from __future__ import annotations

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


def fetch_text(url: str, *, timeout: int = 30) -> str:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.text


def fetch_bytes(url: str, *, timeout: int = 60) -> bytes:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.content


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
