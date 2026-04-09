import json
import hashlib
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from tools.automation_scan import run_scan
from tools.source_connectors import (
    choose_canonical_url,
    dedup_candidates,
    discover_article_list_items,
    discover_rss_items,
)
from tools.wiki_compile import read_note
from workbench.source_store import load_source_state


RSS_XML = b"""<?xml version="1.0"?>
<rss><channel>
<item><title>Alpha</title><link>https://example.com/a</link></item>
<item><title>Beta</title><link>https://example.com/b</link></item>
</channel></rss>
"""

RSS_FILE_XML = b"""<?xml version="1.0"?>
<rss><channel>
<item><title>Unsafe</title><link>file:///etc/passwd</link></item>
<item><title>Safe</title><link>https://example.com/safe</link></item>
</channel></rss>
"""

RSS_MALFORMED_XML = b"""<?xml version="1.0"?>
<rss><channel>
<item><title>Bad</title><link>https://example.com:bad/post</link></item>
<item><title>Good</title><link>https://example.com/good</link></item>
</channel></rss>
"""

RSS_RELATIVE_XML = b"""<?xml version="1.0"?>
<rss><channel>
<item><title>Alpha</title><link>post-a?story=1#frag</link></item>
</channel></rss>
"""

ATOM_XML = b"""<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Example Feed</title>
  <entry>
    <title>Atom Alpha</title>
    <link href="https://example.com/atom-a" />
  </entry>
  <entry>
    <title>Atom Beta</title>
    <link href="post-b?story=1#frag" />
  </entry>
</feed>
"""

LIST_HTML = """
<html><body>
  <a href="https://example.com/a">Alpha</a>
  <a href="https://example.com/c">Gamma</a>
</body></html>
"""

FILTERED_LIST_HTML = """
<html><body>
  <a href="https://example.com/posts/alpha">Alpha</a>
  <a href="/posts/beta?story=1#section">Beta</a>
  <a href="?page=2">Next page</a>
  <a href="/search?q=alpha">Search</a>
  <a href="mailto:test@example.com">Email</a>
  <a href="javascript:void(0)">JS</a>
  <a href="https://other.example.com/posts/gamma">Off domain</a>
  <a href="/tag/python">Tag</a>
  <a href="/category/news">Category</a>
  <a href="/about">About</a>
</body></html>
"""


def _dated_bundle_path(root: Path, name: str) -> Path:
    return root / "20_Raw/inbox" / f"{date.today().isoformat()}-{name}"


class AutomationScanTests(unittest.TestCase):
    def test_discovers_rss_items(self) -> None:
        items = discover_rss_items(RSS_XML, "https://example.com/feed")
        self.assertEqual([item["url"] for item in items], ["https://example.com/a", "https://example.com/b"])

    def test_discovers_rss_items_ignores_unsafe_schemes(self) -> None:
        items = discover_rss_items(RSS_FILE_XML, "https://example.com/feed")
        self.assertEqual([item["url"] for item in items], ["https://example.com/safe"])

    def test_discovers_rss_items_skips_malformed_links_and_continues(self) -> None:
        items = discover_rss_items(RSS_MALFORMED_XML, "https://example.com/feed")
        self.assertEqual([item["url"] for item in items], ["https://example.com/good"])

    def test_discovers_relative_rss_links_against_source_url(self) -> None:
        items = discover_rss_items(RSS_RELATIVE_XML, "https://example.com/feed")
        self.assertEqual([item["url"] for item in items], ["https://example.com/post-a?story=1"])

    def test_discovers_atom_items(self) -> None:
        items = discover_rss_items(ATOM_XML, "https://example.com/feed")
        self.assertEqual(
            [item["url"] for item in items],
            ["https://example.com/atom-a", "https://example.com/post-b?story=1"],
        )

    def test_discovers_article_links_from_list_page(self) -> None:
        items = discover_article_list_items(LIST_HTML, "https://example.com/blog")
        self.assertEqual([item["url"] for item in items], ["https://example.com/a", "https://example.com/c"])

    def test_discovers_article_links_filters_non_article_and_off_domain_links(self) -> None:
        items = discover_article_list_items(FILTERED_LIST_HTML, "https://example.com/blog")
        self.assertEqual(
            [item["url"] for item in items],
            ["https://example.com/posts/alpha", "https://example.com/posts/beta?story=1"],
        )

    def test_discovers_article_links_filters_blog_pagination(self) -> None:
        items = discover_article_list_items(
            '<html><body><a href="/blog/page/2/">Next</a><a href="/blog/archive/">Archive</a></body></html>',
            "https://example.com/blog",
        )
        self.assertEqual(items, [])

    def test_discovers_article_links_treats_www_and_apex_as_same_domain(self) -> None:
        items = discover_article_list_items(
            '<html><body><a href="https://example.com/posts/alpha">Alpha</a></body></html>',
            "https://www.example.com/blog",
        )
        self.assertEqual([item["url"] for item in items], ["https://example.com/posts/alpha"])

    def test_choose_canonical_url_preserves_query_but_strips_fragment(self) -> None:
        self.assertEqual(
            choose_canonical_url("https://example.com/posts/alpha?story=1&utm_source=newsletter#frag"),
            "https://example.com/posts/alpha?story=1&utm_source=newsletter",
        )

    def test_choose_canonical_url_normalizes_host_case_and_empty_path(self) -> None:
        self.assertEqual(
            choose_canonical_url("HTTPS://WWW.EXAMPLE.COM"),
            "https://www.example.com/",
        )

    def test_choose_canonical_url_drops_default_port(self) -> None:
        self.assertEqual(
            choose_canonical_url("https://example.com:443/posts/alpha?story=1"),
            "https://example.com/posts/alpha?story=1",
        )

    def test_choose_canonical_url_preserves_ipv6_brackets(self) -> None:
        self.assertEqual(
            choose_canonical_url("https://[2001:db8::1]/posts/alpha"),
            "https://[2001:db8::1]/posts/alpha",
        )

    def test_dedup_prefers_canonical_url_then_hash(self) -> None:
        unique = dedup_candidates(
            [
                {"canonical_url": "https://example.com/a", "content_hash": "h1"},
                {"canonical_url": "https://example.com/a", "content_hash": "h2"},
                {"canonical_url": "", "content_hash": "h3"},
                {"canonical_url": "", "content_hash": "h3"},
            ]
        )
        self.assertEqual(len(unique), 2)

    def test_dedup_keeps_different_canonical_urls_even_when_hash_matches(self) -> None:
        unique = dedup_candidates(
            [
                {"canonical_url": "https://example.com/a", "content_hash": "same"},
                {"canonical_url": "https://example.com/b", "content_hash": "same"},
            ]
        )
        self.assertEqual(len(unique), 2)

    def test_dedup_uses_hash_only_when_canonical_url_is_empty(self) -> None:
        unique = dedup_candidates(
            [
                {"canonical_url": "", "content_hash": "same"},
                {"canonical_url": "", "content_hash": "same"},
            ]
        )
        self.assertEqual(len(unique), 1)

    def test_dedup_drops_hash_only_duplicate_when_canonical_peer_exists(self) -> None:
        unique = dedup_candidates(
            [
                {"canonical_url": "", "content_hash": "same"},
                {"canonical_url": "https://example.com/a", "content_hash": "same"},
            ]
        )
        self.assertEqual(len(unique), 1)

    def test_dedup_drops_mixed_canonical_and_hash_duplicate_regardless_of_order(self) -> None:
        unique = dedup_candidates(
            [
                {"content_hash": "same"},
                {"canonical_url": "https://example.com/a", "content_hash": "same"},
            ]
        )
        self.assertEqual(len(unique), 1)

    def test_dedup_collapses_mixed_canonical_and_fallback_url_duplicate(self) -> None:
        unique = dedup_candidates(
            [
                {"canonical_url": "https://example.com/a", "content_hash": "h1"},
                {"content_hash": "h2", "url": "https://example.com/a"},
            ]
        )
        self.assertEqual(len(unique), 1)

    def test_dedup_collapses_same_hash_when_fallback_urls_differ_and_canonical_missing(self) -> None:
        unique = dedup_candidates(
            [
                {"content_hash": "same", "url": "https://example.com/a"},
                {"content_hash": "same", "url": "https://example.com/b"},
            ]
        )
        self.assertEqual(len(unique), 1)

    def test_dedup_skips_malformed_candidate_urls_and_keeps_good_items(self) -> None:
        unique = dedup_candidates(
            [
                {"canonical_url": "https://example.com:bad/post", "content_hash": "bad"},
                {"canonical_url": "https://example.com/good", "content_hash": "good"},
            ]
        )
        self.assertEqual(len(unique), 1)
        self.assertEqual(unique[0]["canonical_url"], "https://example.com/good")

    def test_run_scan_imports_local_file_and_updates_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "20_Raw/inbox").mkdir(parents=True)
            (root / "10_Domains/ai-application").mkdir(parents=True)
            (root / "10_Domains/ai-application/index.md").write_text("# AI Application\n", encoding="utf-8")
            (root / "30_Wiki/ai-application").mkdir(parents=True)
            (root / "20_Raw/inbox/note.txt").write_text("# Library Systems\n\nKnowledge access matters.\n", encoding="utf-8")

            result = run_scan(root, [], root / "automation-state.json")

            self.assertGreaterEqual(result["imported_count"], 1)
            self.assertGreaterEqual(result["compiled_count"], 1)
            self.assertEqual(result["failed_count"], 0)

    def test_run_scan_records_unreadable_local_file_and_continues(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inbox = root / "20_Raw/inbox"
            inbox.mkdir(parents=True)
            (root / "10_Domains/business-strategy").mkdir(parents=True)
            (root / "10_Domains/business-strategy/index.md").write_text("# Business Strategy\n", encoding="utf-8")
            (root / "30_Wiki/business-strategy").mkdir(parents=True)
            readable = inbox / "readable.txt"
            unreadable = inbox / "unreadable.txt"
            readable.write_text("# Market Positioning\n\nBusiness strategy and positioning.\n", encoding="utf-8")
            unreadable.write_text("blocked", encoding="utf-8")

            original_read_bytes = Path.read_bytes

            def patched_read_bytes(self: Path) -> bytes:
                if self == unreadable:
                    raise PermissionError("nope")
                return original_read_bytes(self)

            with mock.patch.object(Path, "read_bytes", patched_read_bytes):
                result = run_scan(root, [], root / "automation-state.json")

            state = load_source_state(root / "automation-state.json")
            failed_item = next(item for item in state["failed_items"] if item["source"] == str(unreadable))

            self.assertEqual(result["imported_count"], 1)
            self.assertEqual(result["compiled_count"], 1)
            self.assertEqual(result["failed_count"], 1)
            self.assertEqual(failed_item["stage"], "discovery-failed")
            self.assertEqual(failed_item["error_stage"], "discover")
            self.assertIn("PermissionError", failed_item["error"])
            self.assertEqual(state["last_scan"]["failed_count"], 1)
            self.assertEqual(state["last_scan"]["discovered_count"], 2)

    def test_run_scan_retries_and_exhausts_unreadable_local_file_without_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inbox = root / "20_Raw/inbox"
            inbox.mkdir(parents=True)
            unreadable = inbox / "unreadable.txt"
            unreadable.write_text("blocked", encoding="utf-8")
            state_path = root / "automation-state.json"

            original_read_bytes = Path.read_bytes

            def patched_read_bytes(self: Path) -> bytes:
                if self == unreadable:
                    raise PermissionError("nope")
                return original_read_bytes(self)

            with mock.patch.object(Path, "read_bytes", patched_read_bytes):
                first = run_scan(root, [], state_path)
                state_after_first = load_source_state(state_path)
                second = run_scan(root, [], state_path)
                state_after_second = load_source_state(state_path)
                third = run_scan(root, [], state_path)

            final_state = load_source_state(state_path)

            self.assertEqual(first["failed_count"], 1)
            self.assertEqual(state_after_first["failed_items"][0]["retry_count"], 1)
            self.assertEqual(state_after_first["failed_items"][0]["stage"], "discovery-failed")
            self.assertEqual(second["failed_count"], 0)
            self.assertEqual(state_after_second["failed_items"], [])
            self.assertEqual(len(state_after_second["exhausted_failed_items"]), 1)
            self.assertEqual(state_after_second["exhausted_failed_items"][0]["retry_count"], 2)
            self.assertEqual(state_after_second["exhausted_failed_items"][0]["retry_status"], "exhausted")
            self.assertEqual(third["failed_count"], 0)
            self.assertEqual(third["exhausted_failed_count"], 1)
            self.assertEqual(final_state["failed_items"], [])
            self.assertEqual(len(final_state["exhausted_failed_items"]), 1)
            self.assertEqual(final_state["exhausted_failed_items"][0]["retry_count"], 2)

    def test_run_scan_recovered_unreadable_local_file_is_eligible_again_after_becoming_readable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inbox = root / "20_Raw/inbox"
            inbox.mkdir(parents=True)
            unreadable = inbox / "unreadable.txt"
            unreadable.write_text("# Market Positioning\n\nBusiness strategy and positioning.\n", encoding="utf-8")
            state_path = root / "automation-state.json"

            original_read_bytes = Path.read_bytes

            def patched_read_bytes(self: Path) -> bytes:
                if self == unreadable:
                    raise PermissionError("nope")
                return original_read_bytes(self)

            with mock.patch.object(Path, "read_bytes", patched_read_bytes):
                first = run_scan(root, [], state_path)
                second = run_scan(root, [], state_path)

            third = run_scan(root, [], state_path)
            final_state = load_source_state(state_path)

            self.assertEqual(first["failed_count"], 1)
            self.assertEqual(second["exhausted_failed_count"], 1)
            self.assertEqual(third["failed_count"], 0)
            self.assertEqual(third["exhausted_failed_count"], 0)
            self.assertEqual(third["imported_count"], 1)
            self.assertEqual(third["compiled_count"], 1)
            self.assertEqual(final_state["failed_items"], [])
            self.assertEqual(final_state["exhausted_failed_items"], [])

    def test_run_scan_skips_already_processed_local_file_on_rerun(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "20_Raw/inbox").mkdir(parents=True)
            note_path = root / "20_Raw/inbox/market-positioning.txt"
            note_path.write_text(
                "# Market Positioning\n\nBusiness strategy and positioning for the market moat.\n",
                encoding="utf-8",
            )

            first = run_scan(root, [], root / "automation-state.json")
            second = run_scan(root, [], root / "automation-state.json")

            bundle_dirs = [path for path in (root / "20_Raw/inbox").iterdir() if path.is_dir()]
            self.assertEqual(len(bundle_dirs), 1)
            self.assertGreaterEqual(first["imported_count"], 1)
            self.assertGreaterEqual(first["compiled_count"], 1)
            self.assertEqual(second["imported_count"], 0)
            self.assertEqual(second["compiled_count"], 0)
            self.assertGreaterEqual(second["skipped_count"], 1)

    def test_run_scan_recovers_processed_local_file_after_state_corruption_without_reimporting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inbox = root / "20_Raw/inbox"
            inbox.mkdir(parents=True)
            note_path = inbox / "corruption-guard.txt"
            note_path.write_text(
                "# Market Positioning\n\nBusiness strategy and positioning for the market moat.\n",
                encoding="utf-8",
            )
            state_path = root / "automation-state.json"

            first = run_scan(root, [], state_path)
            state_path.write_text("{not json", encoding="utf-8")

            with mock.patch("tools.automation_scan.import_source", side_effect=AssertionError("should not re-import")), mock.patch(
                "tools.automation_scan.compile_bundle",
                side_effect=AssertionError("should not recompile"),
            ):
                second = run_scan(root, [], state_path)

            final_state = load_source_state(state_path)
            source_key = "local-file:20_Raw/inbox/corruption-guard.txt"

            self.assertGreaterEqual(first["imported_count"], 1)
            self.assertGreaterEqual(first["compiled_count"], 1)
            self.assertEqual(second["imported_count"], 0)
            self.assertEqual(second["compiled_count"], 0)
            self.assertGreaterEqual(second["skipped_count"], 1)
            self.assertIn(source_key, final_state["processed_sources"])
            self.assertEqual(final_state["processed_sources"][source_key]["content_hash"], hashlib.sha256(note_path.read_bytes()).hexdigest())

    def test_run_scan_resumes_compile_failure_without_reimporting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "20_Raw/inbox").mkdir(parents=True)
            (root / "20_Raw/inbox/retry-me.txt").write_text(
                "# Market Positioning\n\nBusiness strategy and positioning for the market moat.\n",
                encoding="utf-8",
            )
            state_path = root / "automation-state.json"
            bundle_path = _dated_bundle_path(root, "retry-me")

            with mock.patch("tools.automation_scan.import_source", return_value=bundle_path) as import_mock, mock.patch(
                "tools.automation_scan.compile_bundle",
                side_effect=[RuntimeError("compile boom"), RuntimeError("compile boom again")],
            ) as compile_mock:
                first = run_scan(root, [], state_path)
                state_after_first = load_source_state(state_path)
                second = run_scan(root, [], state_path)
                third = run_scan(root, [], state_path)

            self.assertEqual(import_mock.call_count, 1)
            self.assertEqual(compile_mock.call_count, 2)
            self.assertEqual(first["imported_count"], 1)
            self.assertEqual(first["compiled_count"], 0)
            self.assertEqual(second["imported_count"], 0)
            self.assertEqual(second["compiled_count"], 0)
            self.assertEqual(third["imported_count"], 0)
            self.assertEqual(third["compiled_count"], 0)
            self.assertEqual(state_after_first["failed_items"][0]["stage"], "imported")
            self.assertEqual(state_after_first["failed_items"][0]["error_stage"], "compile")
            self.assertGreaterEqual(state_after_first["failed_items"][0]["retry_count"], 1)
            final_state = load_source_state(state_path)
            self.assertEqual(final_state["failed_items"], [])
            self.assertEqual(len(final_state["exhausted_failed_items"]), 1)
            self.assertEqual(final_state["exhausted_failed_items"][0]["retry_status"], "exhausted")
            self.assertEqual(final_state["last_scan"]["exhausted_failed_count"], 1)
            self.assertEqual(final_state["last_scan"]["retry_limit"], 2)

    def test_run_scan_retries_compile_failure_after_local_source_is_removed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inbox = root / "20_Raw/inbox"
            inbox.mkdir(parents=True)
            note_path = inbox / "retry-after-removal.txt"
            note_path.write_text(
                "# Market Positioning\n\nBusiness strategy and positioning for the market moat.\n",
                encoding="utf-8",
            )
            state_path = root / "automation-state.json"
            source_key = "local-file:20_Raw/inbox/retry-after-removal.txt"

            with mock.patch(
                "tools.automation_scan.compile_bundle",
                side_effect=[RuntimeError("compile boom"), None],
            ) as compile_mock:
                first = run_scan(root, [], state_path)
                note_path.unlink()
                second = run_scan(root, [], state_path)

            final_state = load_source_state(state_path)

            self.assertEqual(first["imported_count"], 1)
            self.assertEqual(first["compiled_count"], 0)
            self.assertEqual(second["imported_count"], 0)
            self.assertEqual(second["compiled_count"], 1)
            self.assertEqual(second["failed_count"], 0)
            self.assertEqual(compile_mock.call_count, 2)
            self.assertEqual(final_state["processed_sources"][source_key]["stage"], "compiled")
            self.assertEqual(final_state["failed_items"], [])
            self.assertEqual(final_state["exhausted_failed_items"], [])

    def test_run_scan_records_compile_failure_even_when_retry_metadata_write_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inbox = root / "20_Raw/inbox"
            inbox.mkdir(parents=True)
            (inbox / "compile-fail.txt").write_text(
                "# Market Positioning\n\nBusiness strategy and positioning for the market moat.\n",
                encoding="utf-8",
            )
            state_path = root / "automation-state.json"

            with mock.patch("tools.automation_scan.compile_bundle", side_effect=RuntimeError("compile boom")), mock.patch(
                "tools.automation_scan.write_note",
                side_effect=RuntimeError("disk full"),
            ):
                result = run_scan(root, [], state_path)

            state = load_source_state(state_path)

            self.assertEqual(result["imported_count"], 1)
            self.assertEqual(result["compiled_count"], 0)
            self.assertEqual(result["failed_count"], 1)
            self.assertEqual(len(state["failed_items"]), 1)
            self.assertEqual(state["last_scan"]["failed_count"], 1)
            self.assertEqual(state["failed_items"][0]["stage"], "imported")
            self.assertEqual(state["failed_items"][0]["error_stage"], "compile")

    def test_run_scan_recovers_imported_bundle_after_corruption_and_resumes_compile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inbox = root / "20_Raw/inbox"
            inbox.mkdir(parents=True)
            note_path = inbox / "resume-after-corruption.txt"
            note_path.write_text(
                "# Market Positioning\n\nBusiness strategy and positioning for the market moat.\n",
                encoding="utf-8",
            )
            state_path = root / "automation-state.json"

            with mock.patch("tools.automation_scan.compile_bundle", side_effect=RuntimeError("compile boom")):
                first = run_scan(root, [], state_path)

            state_path.write_text("{not json", encoding="utf-8")

            with mock.patch("tools.automation_scan.import_source", side_effect=AssertionError("should not re-import")), mock.patch(
                "tools.automation_scan.compile_bundle",
                return_value=None,
            ) as compile_mock:
                second = run_scan(root, [], state_path)

            final_state = load_source_state(state_path)
            source_key = "local-file:20_Raw/inbox/resume-after-corruption.txt"

            self.assertEqual(first["imported_count"], 1)
            self.assertEqual(first["compiled_count"], 0)
            self.assertEqual(second["imported_count"], 0)
            self.assertEqual(second["compiled_count"], 1)
            self.assertEqual(second["skipped_count"], 0)
            self.assertEqual(compile_mock.call_count, 1)
            self.assertEqual(final_state["processed_sources"][source_key]["stage"], "compiled")
            self.assertEqual(final_state["failed_items"], [])
            self.assertEqual(final_state["exhausted_failed_items"], [])

    def test_run_scan_recovers_imported_bundle_after_corruption_and_source_removal_resumes_compile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inbox = root / "20_Raw/inbox"
            inbox.mkdir(parents=True)
            note_path = inbox / "resume-after-removal.txt"
            note_path.write_text(
                "# Market Positioning\n\nBusiness strategy and positioning for the market moat.\n",
                encoding="utf-8",
            )
            state_path = root / "automation-state.json"

            with mock.patch("tools.automation_scan.compile_bundle", side_effect=RuntimeError("compile boom")):
                first = run_scan(root, [], state_path)

            note_path.unlink()
            state_path.write_text("{not json", encoding="utf-8")

            with mock.patch("tools.automation_scan.import_source", side_effect=AssertionError("should not re-import")), mock.patch(
                "tools.automation_scan.compile_bundle",
                return_value=None,
            ) as compile_mock:
                second = run_scan(root, [], state_path)

            final_state = load_source_state(state_path)
            source_key = "local-file:20_Raw/inbox/resume-after-removal.txt"

            self.assertEqual(first["imported_count"], 1)
            self.assertEqual(first["compiled_count"], 0)
            self.assertEqual(second["imported_count"], 0)
            self.assertEqual(second["compiled_count"], 1)
            self.assertEqual(second["skipped_count"], 0)
            self.assertEqual(compile_mock.call_count, 1)
            self.assertEqual(final_state["processed_sources"][source_key]["stage"], "compiled")
            self.assertEqual(final_state["failed_items"], [])
            self.assertEqual(final_state["exhausted_failed_items"], [])

    def test_run_scan_preserves_compile_retry_budget_across_state_corruption(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inbox = root / "20_Raw/inbox"
            inbox.mkdir(parents=True)
            note_path = inbox / "budget-after-corruption.txt"
            note_path.write_text(
                "# Market Positioning\n\nBusiness strategy and positioning for the market moat.\n",
                encoding="utf-8",
            )
            state_path = root / "automation-state.json"
            bundle_path = _dated_bundle_path(root, "budget-after-corruption")

            with mock.patch("tools.automation_scan.compile_bundle", side_effect=RuntimeError("compile boom")):
                first = run_scan(root, [], state_path)

            state = load_source_state(state_path)
            self.assertEqual(state["failed_items"][0]["retry_count"], 1)
            self.assertEqual(read_note(bundle_path / "metadata.md")[0].get("compile_retry_count"), "1")

            state_path.write_text("{not json", encoding="utf-8")

            with mock.patch("tools.automation_scan.import_source", side_effect=AssertionError("should not re-import")), mock.patch(
                "tools.automation_scan.compile_bundle",
                side_effect=RuntimeError("compile boom again"),
            ) as compile_mock:
                second = run_scan(root, [], state_path)

            final_state = load_source_state(state_path)
            source_key = "local-file:20_Raw/inbox/budget-after-corruption.txt"

            self.assertEqual(first["imported_count"], 1)
            self.assertEqual(first["compiled_count"], 0)
            self.assertEqual(second["imported_count"], 0)
            self.assertEqual(second["compiled_count"], 0)
            self.assertEqual(second["failed_count"], 0)
            self.assertEqual(second["exhausted_failed_count"], 1)
            self.assertEqual(compile_mock.call_count, 1)
            self.assertEqual(final_state["failed_items"], [])
            self.assertEqual(len(final_state["exhausted_failed_items"]), 1)
            self.assertEqual(final_state["exhausted_failed_items"][0]["source_key"], source_key)
            self.assertEqual(final_state["exhausted_failed_items"][0]["retry_count"], 2)

    def test_run_scan_retry_success_updates_processed_state_for_next_scan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "20_Raw/inbox").mkdir(parents=True)
            note_path = root / "20_Raw/inbox/retry-success.txt"
            note_path.write_text(
                "# Market Positioning\n\nBusiness strategy and positioning for the market moat.\n",
                encoding="utf-8",
            )
            state_path = root / "automation-state.json"
            bundle_path = _dated_bundle_path(root, "retry-success")

            with mock.patch("tools.automation_scan.import_source", return_value=bundle_path) as import_mock, mock.patch(
                "tools.automation_scan.compile_bundle",
                side_effect=[RuntimeError("compile boom"), None],
            ) as compile_mock:
                first = run_scan(root, [], state_path)
                second = run_scan(root, [], state_path)
                third = run_scan(root, [], state_path)

            expected_hash = hashlib.sha256(note_path.read_bytes()).hexdigest()
            final_state = load_source_state(state_path)
            source_key = "local-file:20_Raw/inbox/retry-success.txt"

            self.assertEqual(import_mock.call_count, 1)
            self.assertEqual(compile_mock.call_count, 2)
            self.assertEqual(first["imported_count"], 1)
            self.assertEqual(first["compiled_count"], 0)
            self.assertEqual(second["imported_count"], 0)
            self.assertEqual(second["compiled_count"], 1)
            self.assertEqual(third["imported_count"], 0)
            self.assertEqual(third["compiled_count"], 0)
            self.assertEqual(final_state["processed_sources"][source_key]["content_hash"], expected_hash)
            self.assertEqual(final_state["failed_items"], [])
            self.assertEqual(final_state["exhausted_failed_items"], [])

    def test_run_scan_exhausted_item_becomes_eligible_again_after_source_content_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "20_Raw/inbox").mkdir(parents=True)
            note_path = root / "20_Raw/inbox/change-me.txt"
            note_path.write_text(
                "# Market Positioning\n\nBusiness strategy and positioning for the market moat.\n",
                encoding="utf-8",
            )
            state_path = root / "automation-state.json"
            bundle_path = _dated_bundle_path(root, "change-me")

            with mock.patch("tools.automation_scan.import_source", return_value=bundle_path) as import_mock, mock.patch(
                "tools.automation_scan.compile_bundle",
                side_effect=[RuntimeError("compile boom"), RuntimeError("compile boom again"), None],
            ) as compile_mock:
                first = run_scan(root, [], state_path)
                second = run_scan(root, [], state_path)
                note_path.write_text(
                    "# Updated Positioning\n\nAI application strategy with automation and knowledge workflows.\n",
                    encoding="utf-8",
                )
                third = run_scan(root, [], state_path)

            final_state = load_source_state(state_path)
            source_key = "local-file:20_Raw/inbox/change-me.txt"
            expected_hash = hashlib.sha256(note_path.read_bytes()).hexdigest()

            self.assertEqual(import_mock.call_count, 2)
            self.assertEqual(compile_mock.call_count, 3)
            self.assertEqual(first["imported_count"], 1)
            self.assertEqual(first["compiled_count"], 0)
            self.assertEqual(second["imported_count"], 0)
            self.assertEqual(second["compiled_count"], 0)
            self.assertEqual(second["exhausted_failed_count"], 1)
            self.assertEqual(third["imported_count"], 1)
            self.assertEqual(third["compiled_count"], 1)
            self.assertEqual(final_state["processed_sources"][source_key]["content_hash"], expected_hash)
            self.assertEqual(final_state["failed_items"], [])
            self.assertEqual(final_state["exhausted_failed_items"], [])

    def test_run_scan_clears_stale_failed_retry_when_local_file_reverts_to_processed_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inbox = root / "20_Raw/inbox"
            inbox.mkdir(parents=True)
            note_path = inbox / "revert-me.txt"
            state_path = root / "automation-state.json"

            note_path.write_text(
                "# Market Positioning\n\nBusiness strategy and positioning for the market moat.\n",
                encoding="utf-8",
            )
            first = run_scan(root, [], state_path)

            note_path.write_text(
                "# Market Positioning\n\nBusiness strategy and positioning for the market moat, updated.\n",
                encoding="utf-8",
            )

            with mock.patch("tools.automation_scan.compile_bundle", side_effect=RuntimeError("compile boom")):
                second = run_scan(root, [], state_path)

            note_path.write_text(
                "# Market Positioning\n\nBusiness strategy and positioning for the market moat.\n",
                encoding="utf-8",
            )
            third = run_scan(root, [], state_path)
            final_state = load_source_state(state_path)
            source_key = "local-file:20_Raw/inbox/revert-me.txt"

            self.assertGreaterEqual(first["imported_count"], 1)
            self.assertGreaterEqual(first["compiled_count"], 1)
            self.assertEqual(second["compiled_count"], 0)
            self.assertEqual(second["failed_count"], 1)
            self.assertEqual(third["failed_count"], 0)
            self.assertEqual(third["skipped_count"], 1)
            self.assertEqual(final_state["failed_items"], [])
            self.assertEqual(final_state["exhausted_failed_items"], [])
            self.assertIn(source_key, final_state["processed_sources"])

    def test_run_scan_recovers_from_malformed_persisted_retry_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "20_Raw/inbox").mkdir(parents=True)
            (root / "20_Raw/inbox/retry-me.txt").write_text(
                "# Market Positioning\n\nBusiness strategy and positioning for the market moat.\n",
                encoding="utf-8",
            )
            state_path = root / "automation-state.json"
            bundle_path = _dated_bundle_path(root, "retry-me")

            with mock.patch("tools.automation_scan.import_source", return_value=bundle_path), mock.patch(
                "tools.automation_scan.compile_bundle",
                side_effect=RuntimeError("compile boom"),
            ):
                run_scan(root, [], state_path)

            state = load_source_state(state_path)
            state["failed_items"][0]["retry_count"] = "broken"
            state_path.write_text(json.dumps(state), encoding="utf-8")

            with mock.patch("tools.automation_scan.import_source", return_value=bundle_path), mock.patch(
                "tools.automation_scan.compile_bundle",
                return_value=None,
            ) as compile_mock:
                result = run_scan(root, [], state_path)

            final_state = load_source_state(state_path)
            self.assertEqual(compile_mock.call_count, 1)
            self.assertEqual(result["compiled_count"], 1)
            self.assertEqual(final_state["last_scan"]["failed_count"], 0)
            self.assertEqual(final_state["last_scan"]["exhausted_failed_count"], 0)
            self.assertEqual(final_state["failed_items"], [])
            self.assertEqual(final_state["exhausted_failed_items"], [])

    def test_run_scan_recovers_from_malformed_processed_source_retry_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inbox = root / "20_Raw/inbox"
            inbox.mkdir(parents=True)
            note_path = inbox / "resume-me.txt"
            note_path.write_text(
                "# Market Positioning\n\nBusiness strategy and positioning for the market moat.\n",
                encoding="utf-8",
            )
            state_path = root / "automation-state.json"
            bundle_path = _dated_bundle_path(root, "resume-me")

            with mock.patch("tools.automation_scan.import_source", return_value=bundle_path), mock.patch(
                "tools.automation_scan.compile_bundle",
                return_value=None,
            ):
                run_scan(root, [], state_path)

            state = load_source_state(state_path)
            state["processed_sources"]["local-file:20_Raw/inbox/resume-me.txt"]["retry_count"] = "broken"
            state_path.write_text(json.dumps(state), encoding="utf-8")

            with mock.patch("tools.automation_scan.import_source", side_effect=AssertionError("should not re-import")), mock.patch(
                "tools.automation_scan.compile_bundle",
                side_effect=AssertionError("should not recompile"),
            ):
                result = run_scan(root, [], state_path)

            final_state = load_source_state(state_path)
            self.assertEqual(result["imported_count"], 0)
            self.assertEqual(result["compiled_count"], 0)
            self.assertGreaterEqual(result["skipped_count"], 1)
            self.assertEqual(final_state["processed_sources"]["local-file:20_Raw/inbox/resume-me.txt"]["retry_count"], 0)

    def test_run_scan_uses_readable_local_retry_content_to_infer_domain(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "20_Raw/inbox").mkdir(parents=True)
            retry_path = root / "20_Raw/inbox/retry-domain.txt"
            retry_path.write_text(
                "# Market Positioning\n\nBusiness strategy and positioning for the market moat.\n",
                encoding="utf-8",
            )
            state_path = root / "automation-state.json"
            state_payload = {
                "sources": [],
                "last_scan": None,
                "failed_items": [
                    {
                        "source_key": "local-file:20_Raw/inbox/retry-domain.txt",
                        "source": str(retry_path),
                        "source_url": str(retry_path),
                        "url": str(retry_path),
                        "content_hash": "",
                        "primary_domain": "",
                        "related_domains": [],
                        "stage": "import-failed",
                        "error_stage": "import",
                        "retry_count": "broken",
                        "bundle_path": "",
                    }
                ],
                "exhausted_failed_items": [],
                "processed_sources": {},
            }
            state_path.write_text(json.dumps(state_payload), encoding="utf-8")
            bundle_path = _dated_bundle_path(root, "retry-domain")

            with mock.patch("tools.automation_scan.import_source", return_value=bundle_path) as import_mock, mock.patch(
                "tools.automation_scan.compile_bundle",
                return_value=None,
            ):
                result = run_scan(root, [], state_path)

            self.assertEqual(result["imported_count"], 1)
            self.assertEqual(result["compiled_count"], 1)
            self.assertEqual(import_mock.call_args.args[2], "business-strategy")
            final_state = load_source_state(state_path)
            self.assertEqual(final_state["processed_sources"]["local-file:20_Raw/inbox/retry-domain.txt"]["primary_domain"], "business-strategy")

    def test_run_scan_infers_non_ai_domain_for_local_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "20_Raw/inbox").mkdir(parents=True)
            (root / "20_Raw/inbox/strategy-brief.txt").write_text(
                "# Market Positioning\n\nBusiness strategy, positioning, and competitive advantage.\n",
                encoding="utf-8",
            )

            result = run_scan(root, [], root / "automation-state.json")

            self.assertGreaterEqual(result["imported_count"], 1)
            self.assertGreaterEqual(result["compiled_count"], 1)
            self.assertTrue((root / "30_Wiki/business-strategy").exists())
            self.assertTrue((root / "10_Domains/business-strategy/index.md").exists())

    def test_run_scan_failed_item_state_includes_retry_context_and_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "20_Raw/inbox").mkdir(parents=True)
            (root / "20_Raw/inbox/fail-me.txt").write_text(
                "# Market Positioning\n\nBusiness strategy and positioning for the market moat.\n",
                encoding="utf-8",
            )
            state_path = root / "automation-state.json"

            with mock.patch("tools.automation_scan.compile_bundle", side_effect=RuntimeError("compile boom")):
                run_scan(root, [], state_path)

            state = load_source_state(state_path)
            self.assertEqual(len(state["failed_items"]), 1)
            failed_item = state["failed_items"][0]
            self.assertEqual(failed_item["stage"], "imported")
            self.assertEqual(failed_item["error_stage"], "compile")
            self.assertIn("error", failed_item)
            self.assertIn("retry_count", failed_item)
            self.assertIn("source_key", failed_item)
            self.assertIn("content_hash", failed_item)
            self.assertIn("bundle_path", failed_item)
            self.assertGreaterEqual(failed_item["retry_count"], 1)

    def test_dedup_falls_back_to_discovered_url_when_canonical_and_hash_are_empty(self) -> None:
        unique = dedup_candidates(
            [
                {"canonical_url": "", "content_hash": "", "url": "https://example.com/discovered"},
                {"canonical_url": "", "content_hash": "", "url": "https://example.com/discovered"},
            ]
        )
        self.assertEqual(len(unique), 1)

    def test_atomic_write_json_uses_unique_temp_files(self) -> None:
        from tools import automation_cache

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "state.json"
            temp_names = []

            real_named_tempfile = automation_cache.tempfile.NamedTemporaryFile

            def tracking_named_tempfile(*args, **kwargs):
                handle = real_named_tempfile(*args, **kwargs)
                temp_names.append(handle.name)
                return handle

            with mock.patch.object(automation_cache.tempfile, "NamedTemporaryFile", side_effect=tracking_named_tempfile), mock.patch.object(
                automation_cache.os, "replace"
            ) as replace_mock:
                automation_cache.atomic_write_json(target, {"one": 1})
                automation_cache.atomic_write_json(target, {"two": 2})

            self.assertEqual(replace_mock.call_count, 2)
            self.assertEqual(len(set(temp_names)), 2)
            self.assertTrue(all(name.endswith(".tmp") for name in temp_names))

    def test_load_json_returns_independent_default_copy_when_missing(self) -> None:
        from tools.automation_cache import load_json

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "missing.json"
            default = {"sources": []}
            loaded = load_json(target, default)
            loaded["sources"].append("x")
            self.assertEqual(default, {"sources": []})

    def test_discovers_article_links_skips_malformed_anchor_and_continues(self) -> None:
        items = discover_article_list_items(
            '<html><body><a href="https://example.com:bad/post">Bad</a><a href="https://example.com/posts/good">Good</a></body></html>',
            "https://example.com/blog",
        )
        self.assertEqual([item["url"] for item in items], ["https://example.com/posts/good"])

    def test_load_json_recovers_from_unicode_error(self) -> None:
        from tools.automation_cache import load_json

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "broken.json"
            target.write_text("not utf8", encoding="utf-8")
            with mock.patch.object(Path, "read_text", side_effect=UnicodeDecodeError("utf-8", b"", 0, 1, "boom")):
                self.assertEqual(load_json(target, {"sources": []}), {"sources": []})

    def test_load_json_permission_error_still_raises(self) -> None:
        from tools.automation_cache import load_json

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "forbidden.json"
            target.write_text("{}", encoding="utf-8")
            with mock.patch.object(Path, "read_text", side_effect=PermissionError("nope")):
                with self.assertRaises(PermissionError):
                    load_json(target, {"sources": []})
