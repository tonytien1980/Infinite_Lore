import unittest

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
    <link href="https://example.com/atom-b?story=1#frag" />
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
            ["https://example.com/atom-a", "https://example.com/atom-b?story=1"],
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

    def test_choose_canonical_url_preserves_query_but_strips_fragment(self) -> None:
        self.assertEqual(
            choose_canonical_url("https://example.com/posts/alpha?story=1&utm_source=newsletter#frag"),
            "https://example.com/posts/alpha?story=1&utm_source=newsletter",
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
