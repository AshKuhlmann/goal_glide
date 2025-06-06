from __future__ import annotations

import json
import logging
import random
from pathlib import Path
from typing import List, Tuple, cast

import requests

__all__ = ["get_random_quote"]

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "quotes.json"
ZENQUOTES_URL = "https://zenquotes.io/api/random"

_LOCAL_CACHE: list[dict[str, str]] | None = None


def _load_local_quotes() -> list[dict[str, str]]:
    with DATA_PATH.open(encoding="utf-8") as fp:
        data = json.load(fp)
    assert isinstance(data, list)
    return cast(List[dict[str, str]], data)


def get_random_quote(use_online: bool = True) -> Tuple[str, str]:
    """Return (quote, author) using online API then local fallback."""
    if use_online:
        try:
            resp = requests.get(ZENQUOTES_URL, timeout=2)
            if resp.ok:
                data = resp.json()[0]
                return data["q"], data["a"]
        except requests.RequestException as exc:
            logging.debug("ZenQuotes fetch failed: %s", exc)

    global _LOCAL_CACHE
    if _LOCAL_CACHE is None:
        _LOCAL_CACHE = _load_local_quotes()
    item = random.choice(_LOCAL_CACHE)
    return item["quote"], item["author"]
