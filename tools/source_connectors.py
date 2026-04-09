from __future__ import annotations

import urllib.parse
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from typing import Dict, List


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
    clean = parsed._replace(fragment="")
    return urllib.parse.urlunparse(clean)


def choose_canonical_url(url: str) -> str:
    return normalize_url(url)


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def _iter_local(root: ET.Element, name: str) -> List[ET.Element]:
    return [element for element in root.iter() if _local_name(element.tag) == name]


def _is_http_url(url: str) -> bool:
    scheme = urllib.parse.urlparse(url).scheme.lower()
    return scheme in {"http", "https"}


def _is_same_domain(url: str, source_url: str) -> bool:
    parsed_url = urllib.parse.urlparse(url)
    parsed_source = urllib.parse.urlparse(source_url)
    return parsed_url.hostname == parsed_source.hostname


def _looks_like_non_article_path(path: str) -> bool:
    segments = [segment for segment in path.lower().split("/") if segment]
    if not segments:
        return True
    blocked = {
        "about",
        "author",
        "category",
        "contact",
        "feed",
        "privacy",
        "rss",
        "tag",
        "terms",
        "tags",
    }
    return segments[0] in blocked


def discover_rss_items(feed_bytes: bytes, source_url: str) -> List[Dict[str, str]]:
    root = ET.fromstring(feed_bytes)
    items: List[Dict[str, str]] = []
    for item in _iter_local(root, "item"):
        link = ""
        title = ""
        for child in item:
            local = _local_name(child.tag)
            if local == "link" and child.text:
                link = child.text.strip()
            elif local == "title" and child.text:
                title = child.text.strip()
        if link:
            items.append({"title": title or link, "url": normalize_url(link), "source_url": source_url})
            continue
    for entry in _iter_local(root, "entry"):
        link = ""
        title = ""
        for child in entry:
            local = _local_name(child.tag)
            if local == "title" and child.text:
                title = child.text.strip()
            elif local == "link":
                href = child.attrib.get("href", "").strip()
                rel = child.attrib.get("rel", "").strip().lower()
                if href and (_is_http_url(href) or href.startswith("/")) and (not link or rel in {"alternate", ""}):
                    link = href
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
        parsed_href = urllib.parse.urlparse(href.strip())
        if parsed_href.scheme and parsed_href.scheme.lower() not in {"http", "https"}:
            continue
        absolute = urllib.parse.urljoin(base, href)
        normalized = normalize_url(absolute)
        parsed = urllib.parse.urlparse(normalized)
        if not _is_http_url(normalized):
            continue
        if not _is_same_domain(normalized, source_url):
            continue
        if normalized in seen or normalized == base:
            continue
        if _looks_like_non_article_path(parsed.path):
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
        if canonical:
            seen_urls.add(canonical)
        elif digest and digest in seen_hashes:
            continue
        if not canonical and digest:
            seen_hashes.add(digest)
        kept.append(item)
    return kept
