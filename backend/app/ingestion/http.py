import random

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


USER_AGENTS = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (compatible; DuBaoNongSan/1.0; +https://dubaonongsan.com/bot)",
)

DEFAULT_HEADERS = {
    "User-Agent": USER_AGENTS[-1],
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def request_headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    headers = {**DEFAULT_HEADERS, "User-Agent": random.choice(USER_AGENTS)}
    if extra:
        headers.update(extra)
    return headers


def _build_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=10)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update(DEFAULT_HEADERS)
    return session


_SESSION = _build_session()


def fetch_html(url: str, timeout: int = 20) -> str:
    response = _SESSION.get(url, timeout=timeout, headers=request_headers())
    response.raise_for_status()
    response.encoding = response.apparent_encoding or response.encoding
    return response.text
