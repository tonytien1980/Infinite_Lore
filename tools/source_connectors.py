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
    path = parsed.path or "/"
    port = parsed.port
    host = (parsed.hostname or "").lower()
    if port and not ((parsed.scheme.lower() == "http" and port == 80) or (parsed.scheme.lower() == "https" and port == 443)):
        host = f"{host}:{parsed.port}"
    if parsed.username:
        userinfo = parsed.username
        if parsed.password:
            userinfo = f"{userinfo}:{parsed.password}"
        host = f"{userinfo}@{host}"
    clean = parsed._replace(fragment="", path=path, netloc=host)
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
    host_url = (parsed_url.hostname or "").lower().removeprefix("www.")
    host_source = (parsed_source.hostname or "").lower().removeprefix("www.")
    return host_url == host_source


def _looks_like_non_article_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    path = parsed.path
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
        "archive",
        "archives",
        "tag",
        "terms",
        "tags",
    }
    if segments[0] in blocked or segments[0] == "search" or segments[0] == "page":
        return True
    if "archive" in segments or "archives" in segments:
        return True
    if "page" in segments:
        page_index = segments.index("page")
        if page_index + 1 < len(segments) and segments[page_index + 1].isdigit():
            return True
    query_keys = {key.lower() for key in urllib.parse.parse_qs(parsed.query).keys()}
    if "page" in query_keys:
        return True
    return False


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
            absolute = urllib.parse.urljoin(source_url, link)
            items.append({"title": title or absolute, "url": normalize_url(absolute), "source_url": source_url})
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
                parsed_href = urllib.parse.urlparse(href)
                if href and (not parsed_href.scheme or parsed_href.scheme.lower() in {"http", "https"}) and (not link or rel in {"alternate", ""}):
                    link = href
        if link:
            absolute = urllib.parse.urljoin(source_url, link)
            items.append({"title": title or absolute, "url": normalize_url(absolute), "source_url": source_url})
    return items


def discover_article_list_items(html: str, source_url: str) -> List[Dict[str, str]]:
    parser = LinkCollector()
    parser.feed(html)
    base = normalize_url(source_url)
    seen = set()
    items: List[Dict[str, str]] = []
    for href in parser.links:
        try:
            parsed_href = urllib.parse.urlparse(href.strip())
            if parsed_href.scheme and parsed_href.scheme.lower() not in {"http", "https"}:
                continue
            absolute = urllib.parse.urljoin(base, href)
            normalized = normalize_url(absolute)
            if not _is_http_url(normalized):
                continue
            if not _is_same_domain(normalized, source_url):
                continue
            if normalized in seen or normalized == base:
                continue
            if _looks_like_non_article_url(normalized):
                continue
        except (ValueError, TypeError):
            continue
        seen.add(normalized)
        items.append({"title": normalized, "url": normalized, "source_url": source_url})
    return items


def dedup_candidates(items: List[Dict[str, str]]) -> List[Dict[str, str]]:
    kept: List[Dict[str, str]] = []
    seen_canonical_urls = set()
    seen_canonical_hashes = set()
    seen_fallback_hashes = set()
    seen_fallback_urls = set()
    fallback_items: List[Dict[str, str]] = []
    for item in items:
        canonical = item.get("canonical_url", "") or ""
        digest = item.get("content_hash", "") or ""
        fallback = item.get("url", "") or item.get("source_url", "") or ""
        if canonical:
            normalized_canonical = normalize_url(canonical)
            if normalized_canonical in seen_canonical_urls:
                continue
            seen_canonical_urls.add(normalized_canonical)
            if digest:
                seen_canonical_hashes.add(digest)
            kept.append(item)
            continue
        fallback_items.append(item)
    for item in fallback_items:
        digest = item.get("content_hash", "") or ""
        fallback = item.get("url", "") or item.get("source_url", "") or ""
        normalized_fallback = ""
        if fallback:
            normalized_fallback = normalize_url(fallback)
            if normalized_fallback in seen_canonical_urls or normalized_fallback in seen_fallback_urls:
                continue
        if digest and (digest in seen_canonical_hashes or digest in seen_fallback_hashes):
            continue
        if normalized_fallback:
            seen_fallback_urls.add(normalized_fallback)
        if digest:
            seen_fallback_hashes.add(digest)
        kept.append(item)
    return kept
