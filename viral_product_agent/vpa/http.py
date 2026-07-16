"""Retry/backoff'lu tek requests oturumu. Tum kaynak adaptorleri bunu kullanir."""
from __future__ import annotations

import time

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

_session: requests.Session | None = None


def session() -> requests.Session:
    global _session
    if _session is None:
        s = requests.Session()
        s.headers["User-Agent"] = UA
        _session = s
    return _session


def get(url: str, *, params: dict | None = None, headers: dict | None = None,
        timeout: int = 20, retries: int = 3) -> requests.Response | None:
    """GET; basarisizsa None doner — kaynaklar bos liste ile devam eder, run durmaz."""
    backoff = 2.0
    for attempt in range(retries):
        try:
            r = session().get(url, params=params, headers=headers, timeout=timeout)
            if r.status_code == 200:
                return r
            if r.status_code in (202, 403, 404, 451):  # kalici/bot-korumasi: retry anlamsiz
                return None
        except requests.RequestException:
            pass
        if attempt < retries - 1:
            time.sleep(backoff)
            backoff *= 2
    return None
