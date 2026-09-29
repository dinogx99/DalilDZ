from dataclasses import dataclass
from hashlib import sha256
from html.parser import HTMLParser
import json
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx

from app.core.config import settings
from app.core.domain import origin
from app.services.documents import extract_claims
from app.services.security import validate_public_url


class SourceFetchError(RuntimeError):
    pass


@dataclass
class FetchResult:
    final_url: str
    status_code: int
    content_type: str
    body: bytes
    snapshot_hash: str


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_title = False
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "title":
            self._in_title = True
        if tag.lower() == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        cleaned = " ".join(data.split())
        if not cleaned:
            return
        self.text_parts.append(cleaned)
        if self._in_title:
            self.title_parts.append(cleaned)

    @property
    def title(self) -> str:
        return " ".join(self.title_parts)[:300]

    @property
    def visible_text(self) -> str:
        return "\n".join(self.text_parts)[:200000]


async def fetch_public_url(url: str, *, respect_robots: bool = True) -> FetchResult:
    current = validate_public_url(url)
    headers = {
        "User-Agent": settings.user_agent,
        "Accept": "text/html,application/json;q=0.9,*/*;q=0.2",
    }

    if respect_robots and not await robots_allowed(current):
        raise SourceFetchError("ROBOTS_DISALLOWED")

    async with httpx.AsyncClient(
        timeout=settings.http_timeout_seconds,
        follow_redirects=False,
        headers=headers,
    ) as client:
        for _ in range(settings.max_redirects + 1):
            validate_public_url(current)
            async with client.stream("GET", current) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    target = response.headers.get("location")
                    if not target:
                        raise SourceFetchError("INVALID_REDIRECT")
                    current = validate_public_url(urljoin(current, target))
                    continue

                if response.status_code >= 400:
                    raise SourceFetchError(f"HTTP_{response.status_code}")

                declared = response.headers.get("content-length")
                if declared and int(declared) > settings.max_http_bytes:
                    raise SourceFetchError("RESPONSE_TOO_LARGE")

                chunks: list[bytes] = []
                size = 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > settings.max_http_bytes:
                        raise SourceFetchError("RESPONSE_TOO_LARGE")
                    chunks.append(chunk)
                body = b"".join(chunks)
                return FetchResult(
                    final_url=str(response.url),
                    status_code=response.status_code,
                    content_type=response.headers.get("content-type", "").split(";")[0],
                    body=body,
                    snapshot_hash=sha256(body).hexdigest(),
                )
    raise SourceFetchError("TOO_MANY_REDIRECTS")


async def robots_allowed(url: str) -> bool:
    robots_url = urljoin(origin(url) + "/", "robots.txt")
    try:
        result = await fetch_public_url(robots_url, respect_robots=False)
    except SourceFetchError:
        return True

    parser = RobotFileParser()
    parser.set_url(robots_url)
    parser.parse(result.body.decode("utf-8", errors="replace").splitlines())
    return parser.can_fetch(settings.user_agent, url)


async def collect_website_metadata(url: str) -> dict:
    result = await fetch_public_url(url)
    if "html" not in result.content_type:
        raise SourceFetchError("UNSUPPORTED_CONTENT_TYPE")

    parser = PageParser()
    parser.feed(result.body.decode("utf-8", errors="replace"))
    claims = extract_claims(parser.visible_text, page=None, method="website_visible_text")
    evidence = [
        {
            "field": claim.field,
            "value": claim.value,
            "confidence": claim.confidence,
            "method": claim.method,
            "source_url": result.final_url,
            "metadata": {"location": claim.location},
        }
        for claim in claims
        if claim.field in {"rc", "nif", "nis", "ai", "email", "phone", "website", "legal_form", "legal_name"}
    ]

    evidence.append(
        {
            "field": "website",
            "value": result.final_url,
            "confidence": 1.0,
            "method": "http_canonical_url",
            "source_url": result.final_url,
            "metadata": {},
        }
    )
    if parser.title:
        evidence.append(
            {
                "field": "website_title",
                "value": parser.title,
                "confidence": 1.0,
                "method": "html_title",
                "source_url": result.final_url,
                "metadata": {},
            }
        )

    same_origin_links = []
    target_origin = origin(result.final_url)
    for href in parser.links:
        absolute = urljoin(result.final_url, href)
        if origin(absolute) == target_origin and absolute not in same_origin_links:
            same_origin_links.append(absolute)

    return {
        "final_url": result.final_url,
        "snapshot_hash": result.snapshot_hash,
        "content_type": result.content_type,
        "title": parser.title,
        "evidence": evidence,
        "discovered_links": same_origin_links[:20],
        "snapshot_metadata": {
            "status_code": result.status_code,
            "body_bytes": len(result.body),
            "sha256": result.snapshot_hash,
        },
    }
