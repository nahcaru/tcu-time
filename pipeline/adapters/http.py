from __future__ import annotations

from datetime import timedelta, timezone
from email.utils import parsedate_to_datetime
import logging
import ssl

import requests
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": "TCU-TIME Syllabus Enricher/1.0 (grad timetable pipeline)",
}

JST = timezone(timedelta(hours=9))


class LegacyTLSAdapter(HTTPAdapter):
    """HTTPS adapter for the legacy TCU syllabus server."""

    def init_poolmanager(self, *args, **kwargs):  # type: ignore[override]
        ctx = create_urllib3_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
        ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT
        kwargs["ssl_context"] = ctx
        return super().init_poolmanager(*args, **kwargs)


def parse_http_date(date_str: str | None) -> str | None:
    """Parse HTTP date header (e.g. RFC 7231 / RFC 2822) to JST ISO 8601 string."""
    if not date_str:
        return None
    try:
        dt = parsedate_to_datetime(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(JST).isoformat()
    except Exception:
        logger.warning("Failed to parse HTTP date: %s", date_str, exc_info=True)
        return None


class DownloadedPdf(bytes):
    """Subclass of bytes that carries optional HTTP metadata such as Last-Modified timestamp."""

    last_modified: str | None = None

    def __new__(cls, content: bytes, last_modified: str | None = None) -> DownloadedPdf:
        instance = super().__new__(cls, content)
        instance.last_modified = last_modified
        return instance


def fetch_text(url: str, *, timeout: int = 30) -> str:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.text


def fetch_bytes(url: str, *, timeout: int = 60) -> DownloadedPdf:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    last_modified = parse_http_date(response.headers.get("Last-Modified"))
    return DownloadedPdf(response.content, last_modified=last_modified)


def fetch_pdf_with_metadata(url: str, *, timeout: int = 60) -> tuple[bytes, str | None]:
    """Download a PDF and return raw bytes alongside its Last-Modified timestamp in JST ISO 8601."""
    pdf = fetch_bytes(url, timeout=timeout)
    return bytes(pdf), pdf.last_modified


def create_legacy_tls_session(
    *,
    mount_prefix: str = "https://websrv.tcu.ac.jp",
    headers: dict[str, str] | None = None,
) -> requests.Session:
    session = requests.Session()
    session.mount(mount_prefix, LegacyTLSAdapter())
    session.headers.update(headers or DEFAULT_HEADERS)
    return session


def fetch_syllabus_html(
    session: requests.Session,
    url: str,
    *,
    timeout: int = 30,
) -> str | None:
    try:
        response = session.get(
            url,
            verify=False,  # noqa: S501 - required for the legacy server
            timeout=timeout,
        )
        response.raise_for_status()
        response.encoding = "utf-8"
        return response.text
    except requests.RequestException:
        logger.warning("Failed to fetch syllabus: %s", url, exc_info=True)
        return None


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
