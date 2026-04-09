import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.source_connectors import (
    choose_canonical_url,
    dedup_candidates,
    discover_article_list_items,
    discover_rss_items,
)


RSS_XML = b"""<?xml version="1.0"?>
<rss><channel>
<item><title>Alpha</title><link>https://example.com/a</link></item>
<item><title>Beta</title><link>https://example.com/b</link></item>
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


class AutomationScanTests(unittest.TestCase):
    def test_discovers_rss_items(self) -> None:
        items = discover_rss_items(RSS_XML, "https://example.com/feed")
        self.assertEqual([item["url"] for item in items], ["https://example.com/a", "https://example.com/b"])

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
