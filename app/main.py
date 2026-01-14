import argparse
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from instagrapi import Client
from instagrapi.exceptions import LoginRequired

from datastore import PostKey, PostStore, datastore_root
from event_extractor import extract_event_metadata_from_post
from instagram_fetcher import FetchConfig, InstagramFetcher, fetch_accounts, load_accounts
from event_listing_classifier import EventListingClassifier
from template_renderer import event_filename, load_template, render_template


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
TICKET_DOMAINS = {"eventbrite.com", "luma.com", "lu.ma", "tixr.com", "dice.fm"}
LOGGER = logging.getLogger(__name__)


def collect_media_images(store: PostStore) -> List[Path]:
    """Return a list of image paths for a post."""
    images = []
    for path in store.list_media_files():
        if path.suffix.lower() in IMAGE_EXTENSIONS:
            images.append(path)
    return images


def extract_mentions(text: str) -> List[str]:
    """Extract @mentions from a caption."""
    if not text:
        return []
    matches = re.findall(r"@([A-Za-z0-9._]+)", text)
    return list({match.lower() for match in matches})


def instagram_profile_url(username: str) -> str:
    """Return the Instagram profile URL for a username."""
    return f"https://www.instagram.com/{username}/"


def load_instagram_client(session_file: Path) -> Optional[Client]:
    """Load an Instagram client for profile lookups."""
    username = os.environ.get("INSTAGRAM_USERNAME") or os.environ.get("USERNAME")
    password = os.environ.get("INSTAGRAM_PASSWORD") or os.environ.get("PASSWORD")
    if not username or not password:
        return None

    client = Client()
    session = None
    if session_file.exists():
        try:
            session = client.load_settings(session_file.as_posix())
        except Exception:
            session = None
    if session:
        try:
            client.set_settings(session)
            client.login(username, password)
            return client
        except LoginRequired:
            old_uuids = client.get_settings().get("uuids")
            client.set_settings({})
            if old_uuids:
                client.set_uuids(old_uuids)
        except Exception:
            client.set_settings({})

    if client.login(username, password):
        client.dump_settings(session_file.as_posix())
        return client
    return None


def select_best_dj_link(links: Sequence[str]) -> Optional[str]:
    """Select a DJ link by preference order."""
    if not links:
        return None

    lowered = [(link, link.lower()) for link in links if link]
    for link, value in lowered:
        if "soundcloud.com" in value:
            return link
    for link, value in lowered:
        if "residentadvisor" in value or "ra.co" in value:
            return link
    for link, value in lowered:
        if "instagram.com" not in value:
            return link
    return None


def fetch_profile_links(client: Client, username: str) -> List[str]:
    """Return bio links and external URL for an Instagram user."""
    links: List[str] = []
    try:
        data = client.private_request(f"users/{username}/usernameinfo/")
        user = data.get("user") or {}
        external_url = user.get("external_url")
        if external_url:
            links.append(external_url)
        for link in user.get("bio_links") or []:
            url = link.get("url")
            if url:
                links.append(url)
        return links
    except Exception:
        pass

    user = client.user_info_by_username(username)
    if user.external_url:
        links.append(user.external_url)
    for link in user.bio_links or []:
        if link.url:
            links.append(link.url)
    return links


def find_handle_for_name(
    client: Client, name: str, mentions: Sequence[str]
) -> Optional[str]:
    """Resolve a DJ name to a likely Instagram handle."""
    cleaned = name.strip()
    if cleaned.startswith("@"):  # @handle
        return cleaned[1:]

    normalized = re.sub(r"[^a-z0-9]", "", cleaned.lower())
    for handle in mentions:
        if normalized and normalized in handle.replace(".", ""):
            return handle
        try:
            user = client.user_info_by_username(handle)
        except Exception:
            continue
        full_name = (user.full_name or "").lower()
        if cleaned.lower() in full_name:
            return handle

    try:
        results = client.search_users(cleaned)
    except Exception:
        return None
    if results:
        return results[0].username
    return None


def enrich_dj_links(
    djs: List[Dict[str, str]],
    caption: str,
    session_file: Path,
) -> List[Dict[str, str]]:
    """Populate DJ links using Instagram profiles and mentions."""
    mentions = extract_mentions(caption)
    client = load_instagram_client(session_file)

    if not client:
        for dj in djs:
            name = dj.get("name") or ""
            handle = name.lstrip("@").strip()
            if handle:
                dj["link"] = instagram_profile_url(handle)
        return djs

    for dj in djs:
        name = dj.get("name") or ""
        try:
            handle = find_handle_for_name(client, name, mentions)
        except Exception:
            handle = None
        if handle:
            try:
                links = fetch_profile_links(client, handle)
                best = select_best_dj_link(links)
                dj["link"] = best or instagram_profile_url(handle)
            except Exception:
                dj["link"] = instagram_profile_url(handle)
        else:
            dj["link"] = dj.get("link") or ""

    existing_names = {dj.get("name", "").lower() for dj in djs}
    for handle in mentions:
        if handle.lower() in existing_names:
            continue
        try:
            links = fetch_profile_links(client, handle)
            best = select_best_dj_link(links)
            djs.append({"name": handle, "link": best or instagram_profile_url(handle)})
        except Exception:
            djs.append({"name": handle, "link": instagram_profile_url(handle)})

    return djs


def choose_ticket_link(post_url: str, extracted_link: Optional[str]) -> Dict[str, str]:
    """Return a ticket or info link based on ticket providers."""
    link = extracted_link or ""
    lowered = link.lower()
    is_ticket = any(domain in lowered for domain in TICKET_DOMAINS)
    if not is_ticket:
        link = post_url
    return {
        "ticket_or_info_link": link if link else post_url,
        "ticket_link_type": "tickets" if is_ticket else "info",
    }


def classify_event_listings(datastore_path: Path) -> None:
    """Classify posts in the datastore as event listings."""
    classifier = EventListingClassifier()
    for post_dir in datastore_path.glob("*/*"):
        key = PostKey(username=post_dir.parent.name, shortcode=post_dir.name)
        store = PostStore(datastore_path, key)
        if not store.metadata_path.exists():
            continue
        if store.analysis_path.exists():
            continue

        metadata = store.load_metadata()
        caption = metadata.get("caption_text")
        images = collect_media_images(store)
        result = classifier.classify_listing(caption, images)
        store.save_analysis(
            {
                "is_event": result.is_event,
                "is_event_listing": result.is_event,
                "score": result.score,
                "details": result.details,
                "model": {
                    "name": classifier.model_name,
                    "pretrained": classifier.pretrained,
                },
            }
        )


def extract_event_metadata_for_listings(
    datastore_path: Path, events_dir: Path, model: str, session_file: Path
) -> None:
    """Extract event metadata and render templates for event listings."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for second pass analysis.")

    template = load_template()
    events_dir.mkdir(parents=True, exist_ok=True)

    for post_dir in datastore_path.glob("*/*"):
        key = PostKey(username=post_dir.parent.name, shortcode=post_dir.name)
        store = PostStore(datastore_path, key)
        if not store.metadata_path.exists():
            continue
        if store.event_already_processed():
            continue
        analysis = store.load_analysis() or {}
        if not (analysis.get("is_event_listing") or analysis.get("is_event")):
            continue

        metadata = store.load_metadata()
        caption = metadata.get("caption_text") or ""
        post_url = metadata.get("post_url") or ""
        images = collect_media_images(store)
        post_date = metadata.get("taken_at")
        post_author = metadata.get("username")
        result = extract_event_metadata_from_post(
            api_key, model, caption, post_url, images, post_date, post_author
        )
        if result.raw_response:
            store.save_openai_response(result.raw_response)
        if result.error and result.raw_response:
            error_info = result.raw_response.get("error") or {}
            if error_info.get("code") == "insufficient_quota":
                raise RuntimeError(
                    "OpenAI API quota exceeded; stopping event extraction."
                )
        if result.error:
            store.mark_event_failed(result.error)
            print(f"Event extraction failed for {post_url}: {result.error}")
            continue

        event_data = result.data or {}
        djs = event_data.get("djs") or []
        if isinstance(djs, list):
            event_data["djs"] = enrich_dj_links(djs, caption, session_file)
        ticket_update = choose_ticket_link(post_url, event_data.get("ticket_or_info_link"))
        event_data.update(ticket_update)
        missing = [
            field
            for field in [
                "event_name",
                "date",
                "location_name",
                "location_address",
                "google_maps_link",
            ]
            if not event_data.get(field)
        ]
        if missing:
            reason = f"Missing required fields: {', '.join(missing)}"
            store.mark_event_failed(reason)
            print(f"Event extraction incomplete for {post_url}: {reason}")
            continue

        store.save_event(event_data)
        rendered = render_template(template, event_data)
        filename = event_filename(event_data)
        (events_dir / filename).write_text(rendered)


def run_fetch(args: argparse.Namespace) -> None:
    """Fetch recent posts for the provided accounts list."""
    accounts = load_accounts(args.accounts)
    datastore_path = datastore_root(args.datastore)
    session_file = Path(args.session_file).expanduser().resolve()

    fetcher = InstagramFetcher(
        FetchConfig(
            session_file=session_file,
            post_limit=args.limit,
        )
    )

    fetch_accounts(fetcher, accounts, datastore_path)


def run_classify_event_listings(args: argparse.Namespace) -> None:
    """Run event listing classification over the datastore."""
    datastore_path = datastore_root(args.datastore)
    classify_event_listings(datastore_path)


def run_extract_event_metadata(args: argparse.Namespace) -> None:
    """Extract event metadata for posts flagged as listings."""
    datastore_path = datastore_root(args.datastore)
    events_dir = Path(args.events_dir).expanduser().resolve()
    session_file = Path(args.session_file).expanduser().resolve()
    extract_event_metadata_for_listings(
        datastore_path, events_dir, args.model, session_file
    )


def run_all(args: argparse.Namespace) -> None:
    """Fetch, classify event listings, and extract event metadata."""
    run_fetch(args)
    run_classify_event_listings(args)
    run_extract_event_metadata(args)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""
    parser = argparse.ArgumentParser(description="Instagram event pipeline")
    subparsers = parser.add_subparsers(dest="command")

    def add_common_args(target: argparse.ArgumentParser) -> None:
        target.add_argument(
            "--datastore",
            default="/app/datastore",
            help="Datastore root for downloaded posts and analysis results.",
        )
        target.add_argument(
            "--limit",
            type=int,
            default=20,
            help="Maximum number of recent posts to fetch per account.",
        )
        target.add_argument(
            "--session-file",
            default="/app/instagram_session.json",
            help="Path to the Instagram session file.",
        )
        target.add_argument(
            "--events-dir",
            default="/app/_events",
            help="Output directory for rendered event templates.",
        )
        target.add_argument(
            "--model",
            default="gpt-4o-mini",
            help="OpenAI model for event metadata extraction.",
        )

    fetch_parser = subparsers.add_parser("fetch", help="Fetch new posts")
    add_common_args(fetch_parser)
    fetch_parser.add_argument(
        "--accounts",
        required=True,
        help="Path to a file of account URLs or a comma-separated list.",
    )

    classify_parser = subparsers.add_parser(
        "classify-events", help="Classify posts as event listings"
    )
    add_common_args(classify_parser)

    extract_parser = subparsers.add_parser(
        "extract-events", help="Extract event metadata and render templates"
    )
    add_common_args(extract_parser)

    run_parser = subparsers.add_parser(
        "run", help="Fetch posts, classify event listings, extract event metadata"
    )
    add_common_args(run_parser)
    run_parser.add_argument(
        "--accounts",
        required=True,
        help="Path to a file of account URLs or a comma-separated list.",
    )

    return parser


def main() -> None:
    """Entry point for the CLI."""
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=log_level,
        format="%(levelname)s %(name)s:%(lineno)d %(message)s",
    )
    logging.getLogger("instagrapi").setLevel(logging.INFO)
    logging.getLogger("urllib3").setLevel(logging.INFO)
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "fetch":
        run_fetch(args)
    elif args.command == "classify-events":
        run_classify_event_listings(args)
    elif args.command == "extract-events":
        run_extract_event_metadata(args)
    elif args.command == "run":
        run_all(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
