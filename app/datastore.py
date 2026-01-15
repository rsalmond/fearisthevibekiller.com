import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


@dataclass(frozen=True)
class PostKey:
    """Identify a post by username and shortcode."""
    username: str
    shortcode: str


class PostStore:
    """Read and write post data under a datastore root."""
    def __init__(self, root: Path, key: PostKey) -> None:
        """Initialize paths for a specific post."""
        self.root = root
        self.key = key
        self.post_dir = self.root / key.username / key.shortcode
        self.media_dir = self.post_dir / "media"
        self.metadata_path = self.post_dir / "post.json"
        self.analysis_path = self.post_dir / "analysis.json"
        self.event_path = self.post_dir / "event.json"
        self.event_error_path = self.post_dir / "event_error.json"

    def exists(self) -> bool:
        """Return True when metadata has already been saved."""
        return self.metadata_path.exists()

    def ensure_dirs(self) -> None:
        """Create post and media directories if missing."""
        self.media_dir.mkdir(parents=True, exist_ok=True)

    def save_metadata(self, metadata: Dict[str, Any]) -> None:
        """Write metadata to post.json."""
        self.ensure_dirs()
        with self.metadata_path.open("w", encoding="utf-8") as handle:
            json.dump(metadata, handle, indent=2, sort_keys=True)

    def load_metadata(self) -> Dict[str, Any]:
        """Load metadata from post.json."""
        with self.metadata_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def list_media_files(self) -> List[Path]:
        """Return all media files for the post."""
        if not self.media_dir.exists():
            return []
        return [p for p in self.media_dir.iterdir() if p.is_file()]

    def save_analysis(self, data: Dict[str, Any]) -> None:
        """Write analysis results to analysis.json."""
        self.ensure_dirs()
        with self.analysis_path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, sort_keys=True)

    def load_analysis(self) -> Optional[Dict[str, Any]]:
        """Load analysis.json if it exists."""
        if not self.analysis_path.exists():
            return None
        with self.analysis_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def save_event(self, data: Dict[str, Any]) -> None:
        """Write event extraction results to event.json."""
        self.ensure_dirs()
        with self.event_path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, sort_keys=True)
        if self.event_error_path.exists():
            self.event_error_path.unlink()

    def save_openai_response(self, data: Dict[str, Any]) -> None:
        """Write the raw OpenAI response for inspection."""
        self.ensure_dirs()
        path = self.post_dir / "openai_response.json"
        with path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, sort_keys=True)

    def mark_event_failed(self, reason: str) -> None:
        """Record a failed event extraction and the error reason."""
        self.ensure_dirs()
        payload = {"error": reason}
        with self.event_error_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)

    def event_already_processed(self) -> bool:
        """Return True if event extraction succeeded or failed already."""
        return self.event_path.exists() or self.event_error_path.exists()


class ProfileCache:
    """Cache Instagram profile data on disk with a time-based refresh window."""

    def __init__(
        self,
        root: Path,
        ttl_seconds: int = 60 * 60 * 24,
        time_func: Callable[[], float] = time.time,
    ) -> None:
        """Initialize the cache directory and expiry window."""
        self.cache_dir = root / ".profile_cache"
        self.ttl_seconds = ttl_seconds
        self.time_func = time_func
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, username: str) -> Path:
        """Return the path for a cached username entry."""
        safe = username.lower().strip()
        return self.cache_dir / f"{safe}.json"

    def _is_fresh(self, cached_at: float) -> bool:
        """Return True when the cached entry is within the refresh window."""
        return (self.time_func() - cached_at) < self.ttl_seconds

    def _load_entry(self, username: str) -> Optional[Dict[str, Any]]:
        """Load a cached entry if it exists and is still fresh."""
        path = self._cache_path(username)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        cached_at = payload.get("cached_at")
        if not isinstance(cached_at, (int, float)) or not self._is_fresh(cached_at):
            return None
        return payload if isinstance(payload, dict) else None

    def get(self, username: str) -> Optional[Dict[str, Any]]:
        """Load cached profile data if it is still fresh."""
        payload = self._load_entry(username)
        if not payload or payload.get("missing") is True:
            return None
        user = payload.get("user")
        return user if isinstance(user, dict) else None

    def is_missing(self, username: str) -> bool:
        """Return True when a cached entry marks the profile as missing."""
        payload = self._load_entry(username)
        return bool(payload and payload.get("missing") is True)

    def set(self, username: str, user: Dict[str, Any]) -> None:
        """Persist profile data to disk with a timestamp."""
        path = self._cache_path(username)
        payload = {"cached_at": self.time_func(), "user": user}
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def set_missing(self, username: str) -> None:
        """Persist a missing-profile marker to disk with a timestamp."""
        path = self._cache_path(username)
        payload = {"cached_at": self.time_func(), "missing": True}
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def datastore_root(path: str) -> Path:
    """Ensure the datastore root exists and return its absolute path."""
    root = Path(path).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root
