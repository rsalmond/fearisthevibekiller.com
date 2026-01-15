import argparse
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from instagrapi import Client
from instagrapi.exceptions import LoginRequired

from datastore import PostKey, PostStore, ProfileCache, datastore_root
from event_extractor import extract_event_metadata_from_post
from event_listing_classifier import EventListingClassifier
from instagram_fetcher import FetchConfig, InstagramFetcher, fetch_accounts, load_accounts
from paths import DEFAULT_ACCOUNTS, DEFAULT_DATASTORE, DEFAULT_EVENTS_DIR, DEFAULT_SESSION
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


def fetch_profile_data(
    client: Client, username: str, cache: Optional[ProfileCache]
) -> Optional[Dict[str, Any]]:
    """Return profile data for a username, using cached data when available."""
    if cache:
        if cache.is_missing(username):
            return None
        cached = cache.get(username)
        if cached:
            return cached
    try:
        data = client.private_request(f"users/{username}/usernameinfo/")
    except Exception as exc:
        if cache:
            message = str(exc).lower()
            if "404" in message or "not found" in message:
                cache.set_missing(username)
        return None
    user = data.get("user") if isinstance(data, dict) else None
    if isinstance(user, dict) and cache:
        cache.set(username, user)
    return user if isinstance(user, dict) else None


def fetch_profile_links(
    client: Client, username: str, cache: Optional[ProfileCache]
) -> List[str]:
    """Return bio links and external URL for an Instagram user."""
    links: List[str] = []
    user = fetch_profile_data(client, username, cache)
    if not user:
        return links
    external_url = user.get("external_url")
    if external_url:
        links.append(external_url)
    for link in user.get("bio_links") or []:
        url = link.get("url")
        if url:
            links.append(url)
    return links


def find_handle_for_name(
    client: Client,
    name: str,
    mentions: Sequence[str],
    cache: Optional[ProfileCache],
) -> Optional[str]:
    """Resolve a DJ name to a likely Instagram handle."""
    cleaned = name.strip()
    if cleaned.startswith("@"):  # @handle
        return cleaned[1:]

    normalized = re.sub(r"[^a-z0-9]", "", cleaned.lower())
    for handle in mentions:
        if normalized and normalized in handle.replace(".", ""):
            return handle
        user = fetch_profile_data(client, handle, cache)
        if not user:
            continue
        full_name = (user.get("full_name") or "").lower()
        if cleaned.lower() in full_name:
            return handle

    if cache:
        cleaned_lower = cleaned.lower()
        for entry in cache.iter_fresh_users():
            user = entry.get("user") or {}
            full_name = (user.get("full_name") or "").lower()
            if cleaned_lower and cleaned_lower in full_name:
                return entry.get("username")

    try:
        results = client.search_users(cleaned)
    except Exception:
        return None
    if results:
        username = results[0].username
        fetch_profile_data(client, username, cache)
        return username
    return None


def enrich_dj_links(
    djs: List[Dict[str, str]],
    caption: str,
    session_file: Path,
    cache: Optional[ProfileCache] = None,
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
            handle = find_handle_for_name(client, name, mentions, cache)
        except Exception:
            handle = None
        if handle:
            try:
                links = fetch_profile_links(client, handle, cache)
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
            links = fetch_profile_links(client, handle, cache)
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


def iter_post_stores(datastore_path: Path) -> Sequence[PostStore]:
    """Return PostStore instances for each post directory in the datastore."""
    stores: List[PostStore] = []
    for post_dir in datastore_path.glob("*/*"):
        if not post_dir.is_dir():
            continue
        key = PostKey(username=post_dir.parent.name, shortcode=post_dir.name)
        stores.append(PostStore(datastore_path, key))
    return stores


def load_event_data(event_path: Path) -> Optional[Dict[str, Any]]:
    """Load event.json data if it can be decoded."""
    if not event_path.exists():
        return None
    try:
        with event_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (json.JSONDecodeError, OSError):
        return None


def expected_render_path(event_data: Dict[str, Any], events_dir: Path) -> Optional[Path]:
    """Return the expected rendered path when required fields exist."""
    if not event_data.get("event_name") or not event_data.get("date"):
        return None
    filename = event_filename(event_data)
    return (events_dir / filename) if filename else None


def collect_progress_counts(datastore_path: Path, events_dir: Path) -> Dict[str, int]:
    """Return counts for each pipeline stage in the datastore."""
    counts = {
        "downloaded": 0,
        "clip_analyzed": 0,
        "clip_event_listings": 0,
        "extracted_success": 0,
        "extracted_fail": 0,
        "rendered": 0,
    }

    for store in iter_post_stores(datastore_path):
        if not store.metadata_path.exists():
            continue
        counts["downloaded"] += 1
        if store.analysis_path.exists():
            counts["clip_analyzed"] += 1
            analysis = store.load_analysis() or {}
            if analysis.get("is_event_listing") or analysis.get("is_event"):
                counts["clip_event_listings"] += 1
        if store.event_path.exists():
            counts["extracted_success"] += 1
        if store.event_error_path.exists():
            counts["extracted_fail"] += 1

        if store.event_path.exists():
            event_data = load_event_data(store.event_path)
            if not event_data:
                continue
            render_path = expected_render_path(event_data, events_dir)
            if render_path and render_path.exists():
                counts["rendered"] += 1
    return counts


def format_percentage(numerator: int, denominator: int) -> str:
    """Return a percentage string or 'n/a' when the denominator is zero."""
    if denominator <= 0:
        return "n/a"
    return f"{(numerator / denominator) * 100:.1f}%"


def build_progress_table(counts: Dict[str, int]) -> str:
    """Build a plain-text table of progress metrics."""
    downloaded = counts["downloaded"]
    clip_analyzed = counts["clip_analyzed"]
    clip_event_listings = counts["clip_event_listings"]
    clip_non_events = max(clip_analyzed - clip_event_listings, 0)
    extracted_success = counts["extracted_success"]
    extracted_fail = counts["extracted_fail"]
    extracted_total = extracted_success + extracted_fail
    rendered = counts["rendered"]

    rows: List[Tuple[str, str, str, str]] = [
        (
            "Downloaded posts",
            str(downloaded),
            "100.0%" if downloaded else "n/a",
            "",
        ),
        (
            "CLIP analyzed",
            str(clip_analyzed),
            format_percentage(clip_analyzed, downloaded),
            "of downloaded",
        ),
        ("  - events", str(clip_event_listings), "n/a", "classification result"),
        ("  - non-events", str(clip_non_events), "n/a", "classification result"),
        (
            "Extracted total",
            str(extracted_total),
            format_percentage(extracted_total, clip_event_listings),
            "of CLIP events",
        ),
        ("  - success", str(extracted_success), "n/a", ""),
        ("  - fail", str(extracted_fail), "n/a", ""),
        (
            "Rendered",
            str(rendered),
            format_percentage(rendered, extracted_success),
            "of extracted success",
        ),
    ]

    headers = ("Stage", "Count", "Percent", "Notes")
    widths = [
        max(len(headers[0]), max(len(row[0]) for row in rows)),
        max(len(headers[1]), max(len(row[1]) for row in rows)),
        max(len(headers[2]), max(len(row[2]) for row in rows)),
        max(len(headers[3]), max(len(row[3]) for row in rows)),
    ]

    def format_row(values: Tuple[str, str, str, str]) -> str:
        return (
            f"| {values[0].ljust(widths[0])} "
            f"| {values[1].rjust(widths[1])} "
            f"| {values[2].rjust(widths[2])} "
            f"| {values[3].ljust(widths[3])} |"
        )

    border = (
        f"+-{'-' * widths[0]}-+-{'-' * widths[1]}-+-{'-' * widths[2]}-+-{'-' * widths[3]}-+"
    )
    lines = [border, format_row(headers), border]
    lines.extend(format_row(row) for row in rows)
    lines.append(border)
    return "\n".join(lines)


def classify_event_listings(datastore_path: Path) -> None:
    """Classify posts in the datastore as event listings."""
    classifier = EventListingClassifier()
    for store in iter_post_stores(datastore_path):
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

    profile_cache = ProfileCache(datastore_path)
    for store in iter_post_stores(datastore_path):
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
            LOGGER.info("Event extraction failed for %s: %s", post_url, result.error)
            continue

        event_data = result.data or {}
        djs = event_data.get("djs") or []
        if isinstance(djs, list):
            event_data["djs"] = enrich_dj_links(
                djs, caption, session_file, profile_cache
            )
        ticket_update = choose_ticket_link(post_url, event_data.get("ticket_or_info_link"))
        event_data.update(ticket_update)
        missing = [
            field
            for field in [
                "event_name",
                "date",
            ]
            if not event_data.get(field)
        ]
        if missing:
            reason = f"Missing required fields: {', '.join(missing)}"
            store.mark_event_failed(reason)
            LOGGER.info("Event extraction incomplete for %s: %s", post_url, reason)
            continue

        store.save_event(event_data)
        rendered = render_template(template, event_data)
        filename = event_filename(event_data)
        (events_dir / filename).write_text(rendered)
        LOGGER.info("Event extraction succeeded for %s", post_url)


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


def run_progress_report(args: argparse.Namespace) -> None:
    """Print pipeline progress metrics for the datastore."""
    datastore_path = datastore_root(args.datastore)
    events_dir = Path(args.events_dir).expanduser().resolve()
    counts = collect_progress_counts(datastore_path, events_dir)
    print(build_progress_table(counts))


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
        """Add datastore and workflow flags shared by core commands."""
        target.add_argument(
            "--datastore",
            default=DEFAULT_DATASTORE.as_posix(),
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
            default=DEFAULT_SESSION.as_posix(),
            help="Path to the Instagram session file.",
        )
        target.add_argument(
            "--events-dir",
            default=DEFAULT_EVENTS_DIR.as_posix(),
            help="Output directory for rendered event templates.",
        )
        target.add_argument(
            "--model",
            default="gpt-4o-mini",
            help="OpenAI model for event metadata extraction.",
        )

    def add_progress_args(target: argparse.ArgumentParser) -> None:
        """Add arguments needed for the progress report."""
        target.add_argument(
            "--datastore",
            default=DEFAULT_DATASTORE.as_posix(),
            help="Datastore root for downloaded posts and analysis results.",
        )
        target.add_argument(
            "--events-dir",
            default=DEFAULT_EVENTS_DIR.as_posix(),
            help="Output directory for rendered event templates.",
        )

    fetch_parser = subparsers.add_parser("fetch", help="Fetch new posts")
    add_common_args(fetch_parser)
    fetch_parser.add_argument(
        "--accounts",
        required=True,
        default=DEFAULT_ACCOUNTS.as_posix(),
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

    progress_parser = subparsers.add_parser(
        "progress", help="Report datastore processing progress"
    )
    add_progress_args(progress_parser)

    run_parser = subparsers.add_parser(
        "run", help="Fetch posts, classify event listings, extract event metadata"
    )
    add_common_args(run_parser)
    run_parser.add_argument(
        "--accounts",
        required=True,
        default=DEFAULT_ACCOUNTS.as_posix(),
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
    elif args.command == "progress":
        run_progress_report(args)
    elif args.command == "run":
        run_all(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
