import argparse
import random
import shlex
import shutil
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from datastore import PostKey, PostStore, datastore_root
from event_listing_classifier import EventListingClassifier


def iter_posts(datastore_path: Path) -> Iterable[Tuple[PostStore, Path]]:
    """Yield PostStore instances for all posts in the datastore."""
    for post_dir in sorted(datastore_path.glob("*/*")):
        key = PostKey(username=post_dir.parent.name, shortcode=post_dir.name)
        store = PostStore(datastore_path, key)
        if not store.metadata_path.exists():
            continue
        yield store, post_dir


def load_excluded_keys(testdata_root: Path) -> Tuple[Set[Tuple[str, str]], Set[str]]:
    """Collect post keys or shortcodes already stored in testdata directories."""
    excluded_keys: Set[Tuple[str, str]] = set()
    excluded_shortcodes: Set[str] = set()
    if not testdata_root.exists():
        return excluded_keys, excluded_shortcodes

    for post_dir in testdata_root.glob("*/*/*"):
        if not post_dir.is_dir():
            continue
        username = post_dir.parent.name
        shortcode = post_dir.name
        excluded_keys.add((username, shortcode))

    for post_dir in testdata_root.glob("*/*"):
        if not post_dir.is_dir():
            continue
        excluded_shortcodes.add(post_dir.name)

    return excluded_keys, excluded_shortcodes


def load_post_candidates(
    datastore_path: Path,
    excluded_keys: Set[Tuple[str, str]],
    excluded_shortcodes: Set[str],
) -> List[Tuple[PostStore, Path]]:
    """Return eligible posts that are not in testdata."""
    candidates: List[Tuple[PostStore, Path]] = []
    for store, post_dir in iter_posts(datastore_path):
        key = (store.key.username, store.key.shortcode)
        if key in excluded_keys or store.key.shortcode in excluded_shortcodes:
            continue
        candidates.append((store, post_dir))
    return candidates


def load_qmd_search_terms(events_dir: Path) -> Set[str]:
    """Extract search terms from QMD event files."""
    terms: Set[str] = set()
    if not events_dir.exists():
        return terms

    for qmd_path in events_dir.glob("*.qmd"):
        content = qmd_path.read_text(errors="ignore").splitlines()
        for line in content:
            stripped = line.strip()
            if stripped.startswith("###"):
                title = stripped.lstrip("#").strip().lstrip("👉").strip()
                if len(title) >= 4:
                    terms.add(title)
            if stripped.lower().startswith("location:"):
                location = stripped.split(":", 1)[1].strip()
                location = location.split("@", 1)[0].strip()
                if len(location) >= 4:
                    terms.add(location)

        name_from_file = qmd_path.stem
        if "-" in name_from_file:
            parts = name_from_file.split("-", 3)
            if len(parts) == 4:
                slug = parts[-1].replace("-", " ").strip()
                if len(slug) >= 4:
                    terms.add(slug)

    return terms


def filter_posts_by_terms(
    candidates: List[Tuple[PostStore, Path]], terms: Set[str]
) -> List[Tuple[PostStore, Path]]:
    """Return posts whose captions contain any of the search terms."""
    if not terms:
        return []
    lowered_terms = {term.lower() for term in terms if len(term) >= 4}
    matched: List[Tuple[PostStore, Path]] = []
    for store, post_dir in candidates:
        caption = (store.load_metadata().get("caption_text") or "").lower()
        if not caption:
            continue
        if any(term in caption for term in lowered_terms):
            matched.append((store, post_dir))
    return matched


def pick_random_post(
    candidates: List[Tuple[PostStore, Path]],
) -> Optional[Tuple[PostStore, Path]]:
    """Pick a random post and remove it from the candidate pool."""
    if not candidates:
        return None
    index = random.randrange(len(candidates))
    return candidates.pop(index)


def pick_best_event_guess(
    candidates: List[Tuple[PostStore, Path]],
    classifier: EventListingClassifier,
) -> Optional[Tuple[PostStore, Path, float]]:
    """Pick the highest scoring candidate and remove it from the pool."""
    if not candidates:
        return None
    best_index = None
    best_score = -1.0
    for index, (store, _) in enumerate(candidates):
        metadata = store.load_metadata()
        caption = metadata.get("caption_text")
        images = [
            path
            for path in store.list_media_files()
            if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
        ]
        result = classifier.classify_listing(caption, images)
        if result.score > best_score:
            best_score = result.score
            best_index = index
    if best_index is None:
        return None
    store, post_dir = candidates.pop(best_index)
    return store, post_dir, best_score


def format_media_list(store: PostStore) -> List[str]:
    """Return a list of media file paths as strings."""
    return [path.as_posix() for path in store.list_media_files()]

def format_classification_summary(analysis: Optional[Dict]) -> str:
    """Return a human-readable summary of classification results."""
    if not analysis:
        return "missing"
    is_event = analysis.get("is_event_listing")
    if is_event is None:
        is_event = analysis.get("is_event")
    score = analysis.get("score")
    if score is None:
        return f"is_event={is_event}"
    return f"is_event={is_event} score={score:.3f}"


def print_post_details(
    store: PostStore, score: Optional[float] = None, analysis: Optional[Dict] = None
) -> None:
    """Print a post's content, media paths, and optional classification data."""
    metadata = store.load_metadata()
    caption = metadata.get("caption_text") or ""

    print("\n---")
    print(f"Post: {metadata.get('post_url')}")
    print("Caption:")
    print(caption if caption else "(no caption)")
    print("Media files:")
    media_files = format_media_list(store)
    if media_files:
        for path in media_files:
            print(f"  {path}")
    else:
        print("  (no media files found)")
    if score is not None:
        print(f"Classifier score: {score:.3f}")
    if analysis is not None:
        print(f"Classification: {format_classification_summary(analysis)}")


def prompt_label(store: PostStore, score: Optional[float] = None) -> Optional[bool]:
    """Prompt for a label and return True/False, or None to skip/quit."""
    print_post_details(store, score=score)

    while True:
        choice = input("Is this advertising an event? [y/n/s/x]: ").strip().lower()
        if choice in {"y", "yes"}:
            return True
        if choice in {"n", "no"}:
            return False
        if choice in {"s", "skip"}:
            return None
        if choice in {"x", "quit", "exit"}:
            raise KeyboardInterrupt
        print("Please enter y, n, s, or x.")


def build_copy_commands(
    selected: List[Tuple[Path, bool]], testdata_root: Path
) -> List[str]:
    """Return shell commands to copy posts into event/nonevent folders."""
    events_dir = testdata_root / "events"
    nonevents_dir = testdata_root / "nonevents"
    commands = [
        f"mkdir -p {shlex.quote(events_dir.as_posix())} {shlex.quote(nonevents_dir.as_posix())}",
    ]

    for post_dir, is_event in selected:
        dest_dir = events_dir if is_event else nonevents_dir
        commands.append(
            "cp -R "
            f"{shlex.quote(post_dir.as_posix())} "
            f"{shlex.quote(dest_dir.as_posix())}"
        )
    return commands


def copy_post_to_label_dir(post_dir: Path, is_event: bool, testdata_root: Path) -> None:
    """Copy a post directory into the labeled testdata folder."""
    destination_root = testdata_root / ("events" if is_event else "nonevents")
    destination_root.mkdir(parents=True, exist_ok=True)
    destination = destination_root / post_dir.name
    shutil.copytree(post_dir, destination, dirs_exist_ok=True)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for labeling posts."""
    parser = argparse.ArgumentParser(
        description="Label posts as event listings and print copy commands."
    )
    parser.add_argument(
        "--datastore",
        default="/app/datastore",
        help="Datastore root containing post metadata and media.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Stop after labeling this many posts (0 means no limit).",
    )
    parser.add_argument(
        "--testdata-root",
        default="/app/testdata/eventclassifier",
        help="Root directory where labeled test data is stored.",
    )
    parser.add_argument(
        "--prioritize-events",
        action="store_true",
        help="Use the classifier to surface likely event listings first.",
    )
    parser.add_argument(
        "--match-qmd-events",
        action="store_true",
        help="Only show posts whose captions match QMD event text.",
    )
    parser.add_argument(
        "--events-dir",
        default="/data/_events",
        help="Directory containing QMD files with known events.",
    )
    parser.add_argument(
        "--list-classifications",
        action="store_true",
        help="List posts with captions, media paths, and classifier results.",
    )
    parser.add_argument(
        "--include-testdata",
        action="store_true",
        help="Include posts already stored in the labeled testdata directories.",
    )
    return parser


def main() -> None:
    """Run an interactive labeling session for event classifier test data."""
    parser = build_parser()
    args = parser.parse_args()

    datastore_path = datastore_root(args.datastore)
    testdata_root = Path(args.testdata_root).expanduser().resolve()
    excluded_keys, excluded_shortcodes = load_excluded_keys(testdata_root)
    if args.include_testdata:
        candidates = list(iter_posts(datastore_path))
    else:
        candidates = load_post_candidates(datastore_path, excluded_keys, excluded_shortcodes)
    if args.match_qmd_events:
        events_dir = Path(args.events_dir).expanduser().resolve()
        terms = load_qmd_search_terms(events_dir)
        candidates = filter_posts_by_terms(candidates, terms)
    if not candidates:
        print("No eligible posts found (all posts already in testdata).")
        return

    if args.list_classifications:
        shown = 0
        for store, _ in candidates:
            analysis = store.load_analysis()
            print_post_details(store, analysis=analysis)
            shown += 1
            if args.limit and shown >= args.limit:
                break
        return

    classifier = (
        EventListingClassifier() if args.prioritize_events and not args.match_qmd_events else None
    )

    selections: List[Tuple[Path, bool]] = []
    labeled = 0

    try:
        while True:
            if args.limit and labeled >= args.limit:
                break
            score = None
            if args.prioritize_events and classifier:
                prioritized = pick_best_event_guess(candidates, classifier)
                if not prioritized:
                    break
                store, post_dir, score = prioritized
            else:
                next_item = pick_random_post(candidates)
                if not next_item:
                    break
                store, post_dir = next_item
            result = prompt_label(store, score)
            if result is None:
                continue
            selections.append((post_dir, result))
            copy_post_to_label_dir(post_dir, result, testdata_root)
            labeled += 1
    except KeyboardInterrupt:
        print("\nLabeling stopped.")

    if not selections:
        print("No labels recorded.")
        return

    print("\nCopy commands:")
    for cmd in build_copy_commands(selections, testdata_root):
        print(cmd)


if __name__ == "__main__":
    main()
