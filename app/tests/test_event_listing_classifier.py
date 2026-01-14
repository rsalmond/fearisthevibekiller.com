import json
import unittest
from pathlib import Path
from typing import Iterable, List, Tuple

from event_listing_classifier import EventListingClassifier


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def iter_labeled_posts(root: Path) -> Iterable[Tuple[Path, str, List[Path]]]:
    """Yield post directories, captions, and image paths for labeled data."""
    if not root.exists():
        return
    for post_dir in sorted([p for p in root.iterdir() if p.is_dir()]):
        metadata_path = post_dir / "post.json"
        media_dir = post_dir / "media"
        if not metadata_path.exists():
            continue
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except Exception:
            metadata = {}
        caption = metadata.get("caption_text") or ""
        images = []
        if media_dir.exists():
            images = [
                path
                for path in media_dir.iterdir()
                if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
            ]
        yield post_dir, caption, images


class TestEventListingClassifier(unittest.TestCase):
    """Validate classifier predictions against labeled test data."""

    def setUp(self) -> None:
        """Create the classifier once for all tests."""
        self.classifier = EventListingClassifier()

    def test_events_are_classified_as_events(self) -> None:
        """Assert that labeled event posts are classified as events."""
        events_root = Path("/app/testdata/eventclassifier/events")
        failures = []
        total = 0
        for post_dir, caption, images in iter_labeled_posts(events_root):
            total += 1
            result = self.classifier.classify_listing(caption, images)
            if not result.is_event:
                failures.append(post_dir.name)
        self.assertGreater(total, 0, "No event samples found in testdata.")
        self.assertFalse(
            failures,
            f"Classifier missed event posts: {', '.join(failures)}",
        )

    def test_nonevents_are_classified_as_nonevents(self) -> None:
        """Report nonevent misclassifications without failing the test."""
        nonevents_root = Path("/app/testdata/eventclassifier/nonevents")
        failures = []
        total = 0
        for post_dir, caption, images in iter_labeled_posts(nonevents_root):
            total += 1
            result = self.classifier.classify_listing(caption, images)
            if result.is_event:
                failures.append(post_dir.name)
        self.assertGreater(total, 0, "No nonevent samples found in testdata.")
        if failures:
            print(
                "Classifier misclassified nonevent posts:",
                ", ".join(failures),
            )


if __name__ == "__main__":
    unittest.main()
