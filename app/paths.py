from pathlib import Path


def _find_repo_root() -> Path:
    """Find the repo root by locating the data directory."""
    start = Path(__file__).resolve().parent
    for candidate in [start, *start.parents]:
        if (candidate / "data").exists():
            return candidate
    return start


REPO_ROOT = _find_repo_root()
APP_ROOT = REPO_ROOT / "app" if (REPO_ROOT / "app").exists() else REPO_ROOT
DATA_ROOT = REPO_ROOT / "data"

DEFAULT_DATASTORE = Path("/datastore")
DEFAULT_EVENTS_DIR = DATA_ROOT / "_events"
DEFAULT_ACCOUNTS = DATA_ROOT / "accounts.txt"
DEFAULT_TEMPLATE = DATA_ROOT / "template.qmd"
DEFAULT_SESSION = Path("/secure/instagram_session.json")
DEFAULT_ENV = Path("/secure/.env")
DEFAULT_TESTDATA = APP_ROOT / "testdata" / "eventclassifier"
DEFAULT_REJECTED = DATA_ROOT / "rejected_events.txt"
