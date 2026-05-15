from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from html import unescape
from urllib.parse import urlparse

import requests

from campus_autologin.portal_url import parse_portal_url


class ProbeStatus(str, Enum):
    ONLINE = "ONLINE"
    NOT_CAMPUS_NETWORK = "NOT_CAMPUS_NETWORK"
    CAPTIVE_PORTAL = "CAPTIVE_PORTAL"
    PORTAL_REACHABLE = "PORTAL_REACHABLE"
    OFFLINE = "OFFLINE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ProbeResult:
    status: ProbeStatus
    portal_url: str | None = None
    query_string: str | None = None
    message: str = ""


_EPORTAL_RE = re.compile(
    r"https?://[^'\"<>\s]+/eportal/index\.jsp\?[^'\"<>\s]+",
    re.IGNORECASE,
)


def extract_eportal_url(response: object) -> str | None:
    url = str(getattr(response, "url", "") or "")
    if _is_eportal_index(url):
        return url

    text = unescape(str(getattr(response, "text", "") or ""))
    match = _EPORTAL_RE.search(text)
    if match:
        return match.group(0)
    return None


def extract_query_string(portal_url: str) -> str:
    return urlparse(portal_url).query


def is_campus_network_hint(values: list[str] | tuple[str, ...]) -> bool:
    joined = " ".join(str(value) for value in values if value).upper()
    if "HUST_WIRELESS" in joined:
        return True
    if "218.197." in joined:
        return True
    if "202.114." in joined:
        return True
    return False


def probe_connectivity(
    *,
    session: requests.Session,
    probe_urls: list[str],
    portal_base_urls: list[str],
    timeout: int,
    campus_hints: list[str] | tuple[str, ...],
    manual_login_url: str = "",
) -> ProbeResult:
    if not is_campus_network_hint(campus_hints):
        return ProbeResult(
            ProbeStatus.NOT_CAMPUS_NETWORK,
            message="current network does not look like campus network",
        )

    last_error: str | None = None
    for url in probe_urls:
        try:
            response = session.get(url, timeout=timeout, allow_redirects=True)
        except requests.RequestException as exc:
            last_error = str(exc)
            continue

        portal_url = extract_eportal_url(response)
        if portal_url:
            return ProbeResult(
                ProbeStatus.CAPTIVE_PORTAL,
                portal_url=portal_url,
                query_string=extract_query_string(portal_url),
                message="probe reached captive portal",
            )

        if _looks_online(response):
            return ProbeResult(ProbeStatus.ONLINE, message="probe returned online")

    for base_url in portal_base_urls:
        portal_url = base_url.rstrip("/") + "/"
        try:
            response = session.get(portal_url, timeout=timeout, allow_redirects=True)
        except requests.RequestException as exc:
            last_error = str(exc)
            continue

        discovered = extract_eportal_url(response)
        if discovered:
            return ProbeResult(
                ProbeStatus.CAPTIVE_PORTAL,
                portal_url=discovered,
                query_string=extract_query_string(discovered),
                message="portal returned captive URL",
            )
        if response.status_code < 500:
            return ProbeResult(
                ProbeStatus.PORTAL_REACHABLE,
                portal_url=portal_url,
                message="portal base is reachable",
            )

    if manual_login_url:
        try:
            parsed = parse_portal_url(manual_login_url)
        except ValueError:
            pass
        else:
            if parsed.query_string:
                return ProbeResult(
                    ProbeStatus.CAPTIVE_PORTAL,
                    portal_url=manual_login_url,
                    query_string=parsed.query_string,
                    message="using configured manual portal URL",
                )

    return ProbeResult(ProbeStatus.OFFLINE, message=last_error or "all probes failed")


def _is_eportal_index(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.path.endswith("/eportal/index.jsp") and bool(parsed.query)


def _looks_online(response: object) -> bool:
    status_code = int(getattr(response, "status_code", 0) or 0)
    if 200 <= status_code < 300:
        return extract_eportal_url(response) is None
    if status_code in {204, 302, 304}:
        return extract_eportal_url(response) is None
    return False
