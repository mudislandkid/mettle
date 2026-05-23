"""Tiny stdlib-only HTTP wrapper used by the registry resolvers.

We deliberately avoid bringing in `httpx` or `requests` — the call volume is
modest (hundreds of requests per analysis, capped by the cache), and the
behaviour we need is narrow: GET, follow redirects, parse JSON, fail fast on
4xx/5xx, treat 404 as "no such package" rather than an error.

Concurrency is the caller's job (it uses a thread pool); `RegistryClient` is
re-entrant.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .. import __version__

_DEFAULT_UA = f"mettle/{__version__} license-resolver (+https://github.com/mudislandkid/mettle)"
_DEFAULT_TIMEOUT = 8.0
_RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


class RegistryError(Exception):
    """Raised when the registry returned a non-retryable failure (e.g. parse error)."""


class RegistryClient:
    def __init__(
        self,
        *,
        user_agent: str = _DEFAULT_UA,
        timeout: float = _DEFAULT_TIMEOUT,
        retries: int = 2,
    ):
        self.user_agent = user_agent
        self.timeout = timeout
        self.retries = retries

    def get_json(self, url: str) -> dict[str, Any] | None:
        """GET a URL and return the parsed JSON body. None on 404 / parse error.

        Retries `_RETRYABLE_STATUSES` up to `self.retries` times with linear
        backoff. Anything else is raised as `RegistryError`.
        """
        last_exc: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": self.user_agent, "Accept": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    raw = resp.read()
                try:
                    return json.loads(raw)
                except json.JSONDecodeError as e:
                    raise RegistryError(f"non-JSON body from {url}") from e
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    return None
                if e.code in _RETRYABLE_STATUSES and attempt < self.retries:
                    time.sleep(0.5 * (attempt + 1))
                    last_exc = e
                    continue
                raise RegistryError(f"HTTP {e.code} from {url}") from e
            except urllib.error.URLError as e:
                if attempt < self.retries:
                    time.sleep(0.5 * (attempt + 1))
                    last_exc = e
                    continue
                raise RegistryError(f"network error fetching {url}: {e}") from e
        if last_exc:
            raise RegistryError(f"exhausted retries for {url}") from last_exc
        return None
