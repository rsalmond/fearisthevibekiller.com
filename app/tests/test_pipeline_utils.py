import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, "/app")

from datastore import PostKey, PostStore, ProfileCache
from main import (
    build_progress_table,
    choose_ticket_link,
    collect_progress_counts,
    format_percentage,
    find_handle_for_name,
)
from template_renderer import event_filename, render_template


class TestTemplateRenderer(unittest.TestCase):
    """Validate template rendering behavior for DJs and ticket links."""

    def test_render_template_dedupes_djs_and_preserves_location(self) -> None:
        """Render a template with deduped DJ names and unchanged location line."""
        template = (
            "### 👉 <EVENT NAME>\n\n"
            "Location: <LOCATION NAME> @ [LOCATION ADDRESS](GOOGLE MAPS LINK)\n\n"
            "#### STARTTIME-ENDTIME\n\n"
            "* [DJ Name](DJ Link)\n\n"
            "[Tickets or Info](URL)\n"
        )
        event = {
            "event_name": "Test Night",
            "start_time": "21:00",
            "end_time": "02:00",
            "djs": [
                {"name": "DJ One", "link": "https://example.com/djone"},
                {"name": "DJ One", "link": "https://example.com/djone"},
                {"name": "DJ Two", "link": ""},
            ],
            "ticket_or_info_link": "https://eventbrite.com/test",
            "ticket_link_type": "tickets",
        }

        rendered = render_template(template, event)
        self.assertIn("### 👉 Test Night", rendered)
        self.assertIn("21:00-02:00", rendered)
        self.assertIn(
            "Location: <LOCATION NAME> @ [LOCATION ADDRESS](GOOGLE MAPS LINK)",
            rendered,
        )
        self.assertIn("* [DJ One](https://example.com/djone)", rendered)
        self.assertIn("* DJ Two", rendered)
        self.assertEqual(rendered.count("DJ One"), 1)
        self.assertIn("[Tickets](https://eventbrite.com/test)", rendered)

    def test_render_template_info_label(self) -> None:
        """Render a template with an info link label."""
        template = "[Tickets|Info](URL)"
        event = {
            "event_name": "Info Test",
            "ticket_or_info_link": "https://instagram.com/p/abc",
            "ticket_link_type": "info",
        }
        rendered = render_template(template, event)
        self.assertIn("[Info](https://instagram.com/p/abc)", rendered)


class TestTicketLinks(unittest.TestCase):
    """Validate ticket link selection logic."""

    def test_choose_ticket_link_prefers_ticket_domains(self) -> None:
        """Return tickets label when a ticket provider URL is present."""
        result = choose_ticket_link(
            "https://instagram.com/p/abc", "https://eventbrite.com/foo"
        )
        self.assertEqual(result["ticket_or_info_link"], "https://eventbrite.com/foo")
        self.assertEqual(result["ticket_link_type"], "tickets")

    def test_choose_ticket_link_defaults_to_info(self) -> None:
        """Fallback to post URL when the extracted link is not a ticket provider."""
        result = choose_ticket_link(
            "https://instagram.com/p/abc", "https://example.com/info"
        )
        self.assertEqual(result["ticket_or_info_link"], "https://instagram.com/p/abc")
        self.assertEqual(result["ticket_link_type"], "info")

    def test_choose_ticket_link_missing_extracted_link(self) -> None:
        """Fallback to post URL when no link is extracted."""
        result = choose_ticket_link("https://instagram.com/p/abc", None)
        self.assertEqual(result["ticket_or_info_link"], "https://instagram.com/p/abc")
        self.assertEqual(result["ticket_link_type"], "info")


class TestPostStore(unittest.TestCase):
    """Verify PostStore read/write behavior."""

    def create_post_store(self, root: Path, username: str, shortcode: str) -> PostStore:
        """Build a PostStore under a temporary datastore root."""
        key = PostKey(username=username, shortcode=shortcode)
        return PostStore(root, key)

    def test_post_store_round_trip(self) -> None:
        """Write metadata and analysis files and read them back."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            store = self.create_post_store(root, "user", "ABC123")
            metadata = {"caption_text": "hello"}
            analysis = {"is_event_listing": False}
            store.save_metadata(metadata)
            store.save_analysis(analysis)

            self.assertTrue(store.exists())
            self.assertEqual(store.load_metadata(), metadata)
            self.assertEqual(store.load_analysis(), analysis)

    def test_event_failure_and_success(self) -> None:
        """Ensure failed extractions are replaced by success data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            store = self.create_post_store(root, "user", "DEF456")
            store.mark_event_failed("bad data")
            self.assertTrue(store.event_error_path.exists())
            store.save_event({"event_name": "Test", "date": "2025-01-01"})
            self.assertTrue(store.event_path.exists())
            self.assertFalse(store.event_error_path.exists())


class TestProfileCache(unittest.TestCase):
    """Validate cached profile read/write behavior."""

    def test_profile_cache_respects_ttl(self) -> None:
        """Return cached data only within the refresh window."""
        now = [1000.0]

        def time_func() -> float:
            return now[0]

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ProfileCache(Path(tmpdir), ttl_seconds=10, time_func=time_func)
            cache.set("DJHandle", {"full_name": "DJ Test"})
            self.assertEqual(cache.get("djhandle"), {"full_name": "DJ Test"})

            now[0] += 11
            self.assertIsNone(cache.get("djhandle"))

    def test_profile_cache_missing_marker(self) -> None:
        """Treat cached missing profiles as empty until the TTL expires."""
        now = [2000.0]

        def time_func() -> float:
            return now[0]

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ProfileCache(Path(tmpdir), ttl_seconds=10, time_func=time_func)
            cache.set_missing("ghostuser")
            self.assertTrue(cache.is_missing("ghostuser"))
            self.assertIsNone(cache.get("ghostuser"))

            now[0] += 11
            self.assertFalse(cache.is_missing("ghostuser"))


class TestHandleResolution(unittest.TestCase):
    """Ensure handle resolution uses cached profile data."""

    def test_find_handle_for_name_uses_cache(self) -> None:
        """Resolve handles from cached full names without searching."""
        class DummyClient:
            """Stub client that errors if search is called."""

            def search_users(self, _query: str) -> None:
                raise AssertionError("search_users should not be called")

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ProfileCache(Path(tmpdir), ttl_seconds=60)
            cache.set("djhandle", {"full_name": "DJ Example"})
            handle = find_handle_for_name(DummyClient(), "DJ Example", [], cache)
            self.assertEqual(handle, "djhandle")


class TestProgressReporting(unittest.TestCase):
    """Validate datastore progress metrics."""

    def create_post_store(self, root: Path, username: str, shortcode: str) -> PostStore:
        """Build a PostStore under a temporary datastore root."""
        key = PostKey(username=username, shortcode=shortcode)
        return PostStore(root, key)

    def write_event(self, store: PostStore, name: str, date: str) -> dict:
        """Persist a minimal event.json for rendering tests."""
        event_data = {"event_name": name, "date": date}
        store.save_event(event_data)
        return event_data

    def test_collect_progress_counts(self) -> None:
        """Count downloaded, analyzed, extracted, and rendered posts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            events_dir = root / "_events"
            events_dir.mkdir()

            store1 = self.create_post_store(root, "user1", "POST1")
            store1.save_metadata({"caption_text": "one"})
            store1.save_analysis({"is_event_listing": True})
            event_data = self.write_event(store1, "Event One", "2099-09-10")
            rendered_path = events_dir / event_filename(event_data)
            rendered_path.write_text("rendered")

            store2 = self.create_post_store(root, "user2", "POST2")
            store2.save_metadata({"caption_text": "two"})
            store2.save_analysis({"is_event_listing": True})
            store2.mark_event_failed("missing data")

            store3 = self.create_post_store(root, "user3", "POST3")
            store3.save_metadata({"caption_text": "three"})

            counts = collect_progress_counts(root, events_dir)
            self.assertEqual(counts["downloaded"], 3)
            self.assertEqual(counts["clip_analyzed"], 2)
            self.assertEqual(counts["clip_event_listings"], 2)
            self.assertEqual(counts["extracted_success"], 1)
            self.assertEqual(counts["extracted_fail"], 1)
            self.assertEqual(counts["extracted_upcoming"], 1)
            self.assertEqual(counts["rendered"], 1)

    def test_progress_table_formatting(self) -> None:
        """Render a table with expected percentage values."""
        counts = {
            "downloaded": 4,
            "clip_analyzed": 2,
            "clip_event_listings": 2,
            "extracted_success": 1,
            "extracted_fail": 1,
            "extracted_upcoming": 1,
            "rendered": 1,
        }
        table = build_progress_table(counts)
        rows = {}
        for line in table.splitlines():
            if not line.startswith("|") or "Stage" in line:
                continue
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) == 4:
                rows[cells[0]] = cells[1:]

        self.assertEqual(rows["Downloaded posts"], ["4", "100.0%", ""])
        self.assertEqual(rows["CLIP analyzed"], ["2", "50.0%", "of downloaded"])
        self.assertEqual(rows["- events"], ["2", "n/a", "classification result"])
        self.assertEqual(rows["- non-events"], ["0", "n/a", "classification result"])
        self.assertEqual(rows["Extracted total"], ["2", "100.0%", "of CLIP events"])
        self.assertEqual(rows["- success"], ["1", "n/a", ""])
        self.assertEqual(rows["- fail"], ["1", "n/a", ""])
        self.assertEqual(rows["Upcoming extracted"], ["1", "n/a", ""])
        self.assertEqual(rows["Rendered"], ["1", "100.0%", "of upcoming extracted"])

    def test_format_percentage_zero_denominator(self) -> None:
        """Return 'n/a' when no denominator is available."""
        self.assertEqual(format_percentage(1, 0), "n/a")


if __name__ == "__main__":
    unittest.main()
