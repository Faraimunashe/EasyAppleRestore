from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from easyrestore.constants import IPSW_API_USER_AGENT


class HttpError(RuntimeError):
    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


def get_json(url: str, *, timeout: float = 30.0, user_agent: str = IPSW_API_USER_AGENT) -> Any:
    request = Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except HTTPError as exc:
        raise HttpError(f"HTTP {exc.code} for {url}", status=exc.code) from exc
    except URLError as exc:
        raise HttpError(f"Network error: {exc.reason}") from exc
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HttpError("API returned invalid JSON") from exc
