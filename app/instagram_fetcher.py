import datetime
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple
from urllib.parse import urlparse

import requests
import time
from instagrapi import Client
from instagrapi.exceptions import LoginRequired

from datastore import PostKey, PostStore
from video_utils import extract_static_frame

MEDIA_TYPE_PHOTO = 1
MEDIA_TYPE_VIDEO = 2
MEDIA_TYPE_CAROUSEL = 8
LOGGER = logging.getLogger(__name__)


@dataclass
class FetchConfig:
    """Configure session storage and fetch limits."""
    session_file: Path
    post_limit: int


@dataclass
class FetchedPost:
    """Normalized post data for downloads and metadata."""
    code: str
    pk: int
    caption_text: Optional[str]
    taken_at: Optional[str]
    media_type: int
    location: Optional[dict]
    image_urls: List[str]
    video_urls: List[str]
    username: str


class InstagramFetcher:
    """Fetch Instagram posts and save them to the datastore."""
    def __init__(self, config: FetchConfig) -> None:
        """Initialize the fetcher with session and limits."""
        self.config = config
        self.client: Optional[Client] = None

    def _get_env(self, *keys: str) -> Optional[str]:
        """Return the first environment variable that is set."""
        for key in keys:
            value = os.environ.get(key)
            if value:
                return value
        return None

    def _login(self) -> Client:
        """Log into Instagram, preferring a stored session."""
        if self.client is not None:
            return self.client

        username = self._get_env("INSTAGRAM_USERNAME", "USERNAME")
        password = self._get_env("INSTAGRAM_PASSWORD", "PASSWORD")
        if not username or not password:
            raise RuntimeError("Missing Instagram credentials in env vars.")

        client = Client()
        session = None
        if self.config.session_file.exists():
            try:
                session = client.load_settings(self.config.session_file.as_posix())
            except Exception:
                session = None

        if session:
            try:
                client.set_settings(session)
                client.login(username, password)
                client.account_info()
                self.client = client
                LOGGER.debug("Instagram session validated for %s", username)
                return client
            except LoginRequired:
                old_uuids = client.get_settings().get("uuids")
                client.set_settings({})
                if old_uuids:
                    client.set_uuids(old_uuids)
                LOGGER.info("Instagram session expired; reauthenticating %s", username)
            except Exception:
                client.set_settings({})
                LOGGER.info("Instagram session validation failed; reauthenticating %s", username)

        if client.login(username, password):
            client.dump_settings(self.config.session_file.as_posix())
            self.client = client
            LOGGER.debug("Instagram login succeeded for %s", username)
            return client

        raise RuntimeError(
            "Unable to log into Instagram. If you recently logged in elsewhere, "
            "delete the session file and retry to create a new one."
        )

    def _user_id_from_username(self, username: str) -> str:
        """Resolve a username to its numeric user id."""
        client = self._login()
        data = client.private_request(f"users/{username}/usernameinfo/")
        return str(data["user"]["pk"])

    def _best_image_url(self, image_versions: dict) -> Optional[str]:
        """Choose the highest-resolution image URL."""
        candidates = image_versions.get("candidates") or []
        if not candidates:
            return None
        best = max(candidates, key=lambda item: item.get("width", 0) * item.get("height", 0))
        return best.get("url")

    def _best_video_url(self, video_versions: list) -> Optional[str]:
        """Choose the highest-resolution video URL."""
        if not video_versions:
            return None
        best = max(video_versions, key=lambda item: item.get("width", 0) * item.get("height", 0))
        return best.get("url")

    def _extract_media_urls(self, item: dict) -> Tuple[List[str], List[str]]:
        """Collect image and video URLs for a media item."""
        images: List[str] = []
        videos: List[str] = []
        media_type = item.get("media_type")

        if media_type == MEDIA_TYPE_PHOTO:
            url = self._best_image_url(item.get("image_versions2") or {})
            if url:
                images.append(url)
        elif media_type == MEDIA_TYPE_VIDEO:
            url = self._best_video_url(item.get("video_versions") or [])
            if url:
                videos.append(url)
            thumb = self._best_image_url(item.get("image_versions2") or {})
            if thumb:
                images.append(thumb)
        elif media_type == MEDIA_TYPE_CAROUSEL:
            for child in item.get("carousel_media") or []:
                child_images, child_videos = self._extract_media_urls(child)
                images.extend(child_images)
                videos.extend(child_videos)

        return images, videos

    def fetch_recent_posts(self, username: str) -> List[FetchedPost]:
        """Fetch recent posts from the private API and normalize them."""
        LOGGER.debug("Fetching recent posts for %s", username)
        client = self._login()
        user_id = self._user_id_from_username(username)
        data = self._get_recent_media_payload(client, user_id)
        items = data.get("items") or []
        posts: List[FetchedPost] = []
        for item in items:
            code = item.get("code")
            pk = item.get("pk")
            if not code or not pk:
                continue
            taken_at = item.get("taken_at")
            taken_at_iso = None
            if taken_at:
                taken_at_iso = datetime.datetime.fromtimestamp(
                    taken_at, tz=datetime.timezone.utc
                ).isoformat()
            images, videos = self._extract_media_urls(item)
            posts.append(
                FetchedPost(
                    code=code,
                    pk=pk,
                    caption_text=(item.get("caption") or {}).get("text"),
                    taken_at=taken_at_iso,
                    media_type=item.get("media_type") or 0,
                    location=item.get("location"),
                    image_urls=images,
                    video_urls=videos,
                    username=username,
                )
            )
        LOGGER.info("Fetched %d posts for %s", len(posts), username)
        return posts

    def _get_recent_media_payload(self, client: Client, user_id: str) -> dict:
        """Fetch recent media with retries for transient server errors."""
        retries = 3
        last_error: Optional[Exception] = None
        for attempt in range(1, retries + 1):
            try:
                LOGGER.debug("Fetching media payload for %s (attempt %d)", user_id, attempt)
                return client.private_request(
                    f"feed/user/{user_id}/", params={"count": self.config.post_limit}
                )
            except requests.exceptions.RetryError as exc:
                last_error = exc
            except requests.exceptions.RequestException as exc:
                last_error = exc
            time.sleep(2 * attempt)
        raise RuntimeError(f"Failed to fetch feed for user {user_id}") from last_error

    def _download_url(self, url: str, destination: Path) -> bool:
        """Download a URL to a local file, returning success."""
        if destination.exists():
            return True
        destination.parent.mkdir(parents=True, exist_ok=True)
        session = self._login().private
        responses = [
            session.get(url, stream=True, timeout=60),
            requests.get(
                url,
                stream=True,
                timeout=60,
                headers={
                    "User-Agent": self._login().user_agent,
                    "Referer": "https://www.instagram.com/",
                },
            ),
        ]
        for response in responses:
            if response.status_code != 200:
                continue
            with destination.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        handle.write(chunk)
            return True
        print(f"Failed to download media URL: {url} (status {responses[-1].status_code})")
        return False

    def _refresh_media_urls(self, post: FetchedPost) -> Tuple[List[str], List[str]]:
        """Fetch a fresh media payload to refresh URLs."""
        client = self._login()
        data = client.private_request(f"media/{post.pk}/info/")
        items = data.get("items") or []
        if not items:
            return [], []
        return self._extract_media_urls(items[0])

    def _media_filename(self, post: FetchedPost, index: int, url: str, kind: str) -> str:
        """Generate a stable filename for a media URL."""
        suffix = Path(urlparse(url).path).suffix
        if not suffix:
            suffix = ".mp4" if kind == "video" else ".jpg"
        return f"{post.username}_{post.pk}_{kind}_{index}{suffix}"

    def download_post(self, post: FetchedPost, store: PostStore) -> None:
        """Download images and videos for a post into the datastore."""
        LOGGER.debug(
            "Downloading media for %s (%d images, %d videos)",
            post.code,
            len(post.image_urls),
            len(post.video_urls),
        )
        store.ensure_dirs()
        media_dir = store.media_dir
        failed_images: List[Tuple[int, str]] = []
        failed_videos: List[Tuple[int, str]] = []

        for idx, url in enumerate(post.image_urls, start=1):
            filename = self._media_filename(post, idx, url, "image")
            if not self._download_url(url, media_dir / filename):
                failed_images.append((idx, url))

        for idx, url in enumerate(post.video_urls, start=1):
            filename = self._media_filename(post, idx, url, "video")
            video_path = media_dir / filename
            if self._download_url(url, video_path):
                extract_static_frame(video_path, media_dir)
            else:
                failed_videos.append((idx, url))

        if failed_images or failed_videos:
            LOGGER.info(
                "Retrying media refresh for %s (images=%d videos=%d)",
                post.code,
                len(failed_images),
                len(failed_videos),
            )
            refreshed_images, refreshed_videos = self._refresh_media_urls(post)
            for idx, url in enumerate(refreshed_images, start=1):
                filename = self._media_filename(post, idx, url, "image")
                self._download_url(url, media_dir / filename)
            for idx, url in enumerate(refreshed_videos, start=1):
                filename = self._media_filename(post, idx, url, "video")
                video_path = media_dir / filename
                if self._download_url(url, video_path):
                    extract_static_frame(video_path, media_dir)

    def save_post(self, post: FetchedPost, store: PostStore) -> None:
        """Persist post metadata and media assets."""
        LOGGER.debug("Saving post %s to %s", post.code, store.root)
        metadata = {
            "post_url": f"https://www.instagram.com/p/{post.code}/",
            "username": post.username,
            "shortcode": post.code,
            "media_pk": post.pk,
            "caption_text": post.caption_text,
            "taken_at": post.taken_at,
            "media_type": post.media_type,
            "location": post.location,
        }
        store.save_metadata(metadata)
        self.download_post(post, store)


def parse_account_identifier(value: str) -> str:
    """Normalize account inputs to a username string."""
    handle = value.strip()
    if not handle:
        return handle

    if handle.startswith("@"):  # @username
        return handle[1:]

    if handle.startswith("http"):
        parsed = urlparse(handle)
        parts = [part for part in parsed.path.split("/") if part]
        if parts:
            return parts[0]

    return handle


def load_accounts(source: str) -> List[str]:
    """Load account handles from a file or comma-separated string."""
    path = Path(source)
    if path.exists() and path.is_file():
        entries = [row.strip() for row in path.read_text().splitlines() if row.strip()]
    else:
        entries = [part.strip() for part in source.split(",") if part.strip()]
    return [parse_account_identifier(entry) for entry in entries if entry]


def fetch_accounts(
    fetcher: InstagramFetcher,
    accounts: Iterable[str],
    datastore_path: Path,
) -> List[PostStore]:
    """Fetch and save posts for all provided accounts."""
    accounts_list = list(accounts)
    LOGGER.info("Fetching posts for %d accounts", len(accounts_list))

    def should_log_errors() -> bool:
        """Return True if fetch errors should be logged."""
        return os.environ.get("INSTAGRAM_FETCH_VERBOSE", "").lower() in {"1", "true", "yes"}

    saved_posts: List[PostStore] = []
    for account in accounts_list:
        LOGGER.info("Starting fetch for %s", account)
        try:
            posts = fetcher.fetch_recent_posts(account)
        except Exception as exc:
            if should_log_errors():
                print(f"Failed to fetch posts for {account}: {exc}")
            continue
        LOGGER.debug("Processing %d posts for %s", len(posts), account)
        saved_for_account = 0
        for post in posts:
            key = PostKey(username=account, shortcode=post.code)
            store = PostStore(datastore_path, key)
            if store.exists() and store.list_media_files():
                LOGGER.debug("Skipping existing post %s for %s", post.code, account)
                continue
            fetcher.save_post(post, store)
            saved_posts.append(store)
            saved_for_account += 1
        LOGGER.info("Completed fetch for %s (%d saved)", account, saved_for_account)
    return saved_posts
