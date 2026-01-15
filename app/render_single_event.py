import argparse
import json
import logging
import os
from pathlib import Path
from typing import Dict, List

from instagrapi import Client
from instagrapi.exceptions import LoginRequired

from datastore import ProfileCache, datastore_root
from event_extractor import extract_event_metadata_from_post
from main import choose_ticket_link, enrich_dj_links
from template_renderer import event_filename, load_template, render_template


def load_instagram_client(session_file: Path) -> Client:
    """Log into Instagram for profile lookups."""
    username = os.environ.get("INSTAGRAM_USERNAME") or os.environ.get("USERNAME")
    password = os.environ.get("INSTAGRAM_PASSWORD") or os.environ.get("PASSWORD")
    if not username or not password:
        raise RuntimeError("Missing Instagram credentials for DJ lookup.")

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

    raise RuntimeError("Unable to log into Instagram for DJ lookup.")


def load_post_metadata(post_dir: Path) -> Dict:
    """Load post metadata from a testdata directory."""
    metadata_path = post_dir / "post.json"
    return json.loads(metadata_path.read_text(encoding="utf-8"))

def load_event_data(post_dir: Path) -> Dict:
    """Load extracted event data if it exists."""
    event_path = post_dir / "event.json"
    if event_path.exists():
        return json.loads(event_path.read_text(encoding="utf-8"))
    return {}


def save_event_data(post_dir: Path, event_data: Dict) -> None:
    """Save extracted event data to disk."""
    event_path = post_dir / "event.json"
    event_path.write_text(json.dumps(event_data, indent=2, sort_keys=True))


def save_openai_response(post_dir: Path, response: Dict) -> None:
    """Save raw OpenAI response to disk."""
    response_path = post_dir / "openai_response.json"
    response_path.write_text(json.dumps(response, indent=2, sort_keys=True))


def collect_post_images(post_dir: Path) -> List[Path]:
    """Collect image files from a testdata post directory."""
    media_dir = post_dir / "media"
    if not media_dir.exists():
        return []
    return [
        path
        for path in media_dir.iterdir()
        if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
    ]


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""
    parser = argparse.ArgumentParser(description="Render a template from testdata.")
    parser.add_argument("post_dir", help="Path to a labeled event post directory.")
    parser.add_argument(
        "--session-file",
        default="/app/instagram_session.json",
        help="Instagram session file for DJ link lookups.",
    )
    parser.add_argument(
        "--output-dir",
        default="/app/_events",
        help="Directory for rendered templates.",
    )
    parser.add_argument(
        "--model",
        default="gpt-4o-mini",
        help="OpenAI model for event extraction when needed.",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Ignore cached event data and re-run OpenAI extraction.",
    )
    return parser


def main() -> None:
    """Render a template for a single labeled event post."""
    parser = build_parser()
    args = parser.parse_args()
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=log_level,
        format="%(levelname)s %(name)s:%(lineno)d %(message)s",
    )

    post_dir = Path(args.post_dir).expanduser().resolve()
    metadata = load_post_metadata(post_dir)
    caption = metadata.get("caption_text") or ""
    post_url = metadata.get("post_url") or ""

    event_data = {} if args.no_cache else load_event_data(post_dir)
    if not event_data:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required for event extraction.")
        images = collect_post_images(post_dir)
        post_date = metadata.get("taken_at")
        post_author = metadata.get("username")
        result = extract_event_metadata_from_post(
            api_key, args.model, caption, post_url, images, post_date, post_author
        )
        if result.raw_response:
            save_openai_response(post_dir, result.raw_response)
        if result.error:
            raise RuntimeError(f"OpenAI extraction failed: {result.error}")
        event_data = result.data or {}
        save_event_data(post_dir, event_data)

    djs = event_data.get("djs") or []
    if isinstance(djs, list):
        cache = ProfileCache(datastore_root("/app/datastore"))
        event_data["djs"] = enrich_dj_links(
            djs, caption, Path(args.session_file), cache
        )
    event_data.update(choose_ticket_link(post_url, event_data.get("ticket_or_info_link")))

    template = load_template()
    rendered = render_template(template, event_data)
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / event_filename(event_data)
    output_path.write_text(rendered)
    print(output_path.as_posix())


if __name__ == "__main__":
    main()
