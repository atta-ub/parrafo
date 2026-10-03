"""Download helper with an on-disk cache, so `parrafo build` can be re-run cheaply."""

import hashlib
import os
from pathlib import Path

import requests

from ..paths import cache_dir

# Wikimedia throttles anonymous-looking clients; their policy asks for a URL or
# contact address. Set PARRAFO_CONTACT (e.g. your email) to identify yourself.
USER_AGENT = "parrafo/0.1 (personal Spanish-reading CLI; {})".format(
    os.environ.get("PARRAFO_CONTACT") or "https://dumps.wikimedia.org/other/contenttranslation/"
)


def fetch(url: str, *, name: str | None = None, refresh: bool = False) -> Path:
    """Return a local path for `url`, downloading it on first use."""
    name = name or hashlib.sha1(url.encode()).hexdigest()[:16]
    path = cache_dir() / name
    if path.exists() and not refresh:
        return path
    tmp = path.with_suffix(path.suffix + ".part")
    with requests.get(url, stream=True, timeout=60, headers={"User-Agent": USER_AGENT}) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 16):
                f.write(chunk)
    tmp.rename(path)
    return path


def fetch_text(url: str, **kw) -> str:
    return fetch(url, **kw).read_text(encoding="utf-8", errors="replace")
