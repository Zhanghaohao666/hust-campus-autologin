from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class ParsedPortalUrl:
    base_url: str
    query_string: str


def parse_portal_url(value: str) -> ParsedPortalUrl:
    stripped = value.strip()
    if not stripped:
        raise ValueError("portal URL is empty")

    parsed = urlparse(stripped)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"invalid portal URL: {value}")
    if "/eportal" not in parsed.path:
        raise ValueError(f"not an eportal URL: {value}")

    prefix = parsed.path.split("/eportal", 1)[0]
    base_url = f"{parsed.scheme}://{parsed.netloc}{prefix}/eportal"
    return ParsedPortalUrl(base_url=base_url, query_string=parsed.query)
