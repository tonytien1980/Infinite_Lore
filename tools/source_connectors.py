from __future__ import annotations

import urllib.parse
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from typing import Dict, List

from tools.automation_cache import content_hash_bytes


class LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: List[str] = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        for key, value in attrs:
            if key == "href" and value:
                self.links.append(value)


def normalize_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url.strip())
    clean = parsed._replace(fragment="", query="")
    return urllib.parse.urlunparse(clean)


def choose_canonical_url(url: str) -> str:
    return normalize_url(url)


def discover_rss_items(feed_bytes: bytes, source_url: str) -> List[Dict[str, str]]:
    root = ET.fromstring(feed_bytes)
    items: List[Dict[str, str]] = []
    for item in root.findall(".//item"):
        link = item.findtext("link", default="").strip()
        title = item.findtext("title", default="").strip()
        if link:
            items.append({"title": title or link, "url": normalize_url(link), "source_url": source_url})
    return items


def discover_article_list_items(html: str, source_url: str) -> List[Dict[str, str]]:
    parser = LinkCollector()
    parser.feed(html)
    base = normalize_url(source_url)
    seen = set()
    items: List[Dict[str, str]] = []
    for href in parser.links:
        absolute = urllib.parse.urljoin(base, href)
        normalized = normalize_url(absolute)
        if normalized in seen or normalized == base:
            continue
        seen.add(normalized)
        items.append({"title": normalized, "url": normalized, "source_url": source_url})
    return items


def dedup_candidates(items: List[Dict[str, str]]) -> List[Dict[str, str]]:
    kept: List[Dict[str, str]] = []
    seen_urls = set()
    seen_hashes = set()
    for item in items:
        canonical = item.get("canonical_url", "") or ""
        digest = item.get("content_hash", "") or ""
        if canonical and canonical in seen_urls:
            continue
        if digest and digest in seen_hashes:
            continue
        if canonical:
            seen_urls.add(canonical)
        if digest:
            seen_hashes.add(digest)
        kept.append(item)
    return kept
