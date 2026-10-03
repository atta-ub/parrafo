"""Wikipedia Content Translation corpus, Spanish → English.

Wikimedia publishes every section translated with its Content Translation
tool: https://dumps.wikimedia.org/other/contenttranslation/
The es2en dump holds Spanish-original sections with the English that a
Wikipedia editor published, plus the raw machine translation they started
from (when one was used). We keep paragraphs whose English was clearly
written or revised by a person. Licence: CC BY-SA 4.0.

The dump has no titles, so those come from the `cxpublishedtranslations` API.
"""

import difflib
import gzip
import json
import re
import time
from collections import defaultdict
from urllib.parse import quote

import requests

from .. import topics
from ..paths import cache_dir
from . import Passage
from .fetch import USER_AGENT, fetch
from .textutil import squash, strip_refs

DUMPS = "https://dumps.wikimedia.org/other/contenttranslation/"
DUMP_FILE = "cx-corpora.es2en.text.json.gz"
TITLES_API = "https://en.wikipedia.org/w/api.php"
TITLES_FILE = "cx-es2en-titles.json"
CATEGORIES_FILE = "cx-es2en-categories.json"

MIN_LEN, MAX_LEN = 250, 900
# Above this similarity to the raw machine translation, we assume nobody edited it.
MAX_MT_SIMILARITY = 0.85

_EN_WORDS = re.compile(r"\b(the|and|of|was|is|in|with|which)\b", re.I)
_ES_WORDS = re.compile(r"\b(el|la|los|las|y|de|que|en|fue|con)\b", re.I)
_LISTY = re.compile(r"ISBN|https?://|\.\s*\d{4}\.|\(\d{4}\)\.")


def _session() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    return s


def dump_path(refresh: bool = False):
    cached = cache_dir() / DUMP_FILE
    if cached.exists() and not refresh:
        return cached
    html = _session().get(DUMPS, timeout=30).text
    latest = sorted(re.findall(r'href="(\d{8})/"', html))[-1]
    return fetch(f"{DUMPS}{latest}/{DUMP_FILE}", name=DUMP_FILE, refresh=True)


def titles(refresh: bool = False) -> dict[str, dict]:
    """{translationId: {"es": source title, "en": target title}}, cached on disk."""
    path = cache_dir() / TITLES_FILE
    if path.exists() and not refresh:
        return json.loads(path.read_text())
    out: dict[str, dict] = {}
    s, offset = _session(), 0
    while True:
        params = {
            "action": "query", "list": "cxpublishedtranslations", "from": "es", "to": "en",
            "limit": 500, "offset": offset, "format": "json",
        }
        batch = _get_json(s, params)["result"]["translations"]
        if not batch:
            break
        for t in batch:
            out[t["translationId"]] = {"es": t["sourceTitle"], "en": t["targetTitle"]}
        offset += len(batch)
        time.sleep(0.5)
    path.write_text(json.dumps(out, ensure_ascii=False))
    return out


def categories(en_titles: list[str], refresh: bool = False) -> dict[str, list[str]]:
    """{English title: [visible category names]}, cached on disk."""
    path = cache_dir() / CATEGORIES_FILE
    out: dict[str, list[str]] = {} if refresh or not path.exists() else json.loads(path.read_text())
    todo = sorted(set(en_titles) - set(out))
    s = _session()
    for i in range(0, len(todo), 50):
        chunk = todo[i : i + 50]
        params = {
            "action": "query", "prop": "categories", "titles": "|".join(chunk),
            "clshow": "!hidden", "cllimit": "max", "redirects": 1, "format": "json",
        }
        found: dict[str, list[str]] = {t: [] for t in chunk}
        while True:
            data = _get_json(s, params)
            # Map redirected/normalised names back to the titles we asked for.
            back = {}
            for key in ("normalized", "redirects"):
                for m in data.get("query", {}).get(key, []):
                    back[m["to"]] = back.get(m["from"], m["from"])
            for page in data.get("query", {}).get("pages", {}).values():
                title = back.get(page["title"], page["title"])
                cats = [c["title"].removeprefix("Category:") for c in page.get("categories", [])]
                found.setdefault(title, []).extend(cats)
            if "continue" not in data:
                break
            params = {**params, **data["continue"]}
        out.update(found)
        time.sleep(0.5)
        if i % 1000 == 0:
            path.write_text(json.dumps(out, ensure_ascii=False))
    path.write_text(json.dumps(out, ensure_ascii=False))
    return out


def _get_json(s: requests.Session, params: dict, tries: int = 5) -> dict:
    for attempt in range(tries):
        r = s.get(TITLES_API, params=params, timeout=60)
        if r.status_code != 429:
            r.raise_for_status()
            return r.json()
        time.sleep(int(r.headers.get("Retry-After", 0)) or 5 * (attempt + 1))
    r.raise_for_status()
    return r.json()


def _human_edited(mt: str, target: str) -> bool:
    if not mt:
        return True  # translated from scratch, or the MT draft was not recorded
    return difflib.SequenceMatcher(None, mt, target, autojunk=False).ratio() < MAX_MT_SIMILARITY


def keep(es: str, en: str, mt: str) -> bool:
    """Is this a clean prose paragraph pair worth showing?"""
    if not (MIN_LEN <= len(es) <= MAX_LEN) or not en:
        return False
    if not 0.7 <= len(en) / len(es) <= 1.4:
        return False
    if _LISTY.search(es) or ". " not in es or es[-1] not in '.!?»")':
        return False
    # The English must actually be English (some sections were left untranslated).
    if len(_EN_WORDS.findall(en)) <= len(_ES_WORDS.findall(en)):
        return False
    return _human_edited(mt, en)


def load(refresh: bool = False) -> list[Passage]:
    with gzip.open(dump_path(refresh), "rt", encoding="utf-8") as f:
        units = json.load(f)
    names = titles(refresh)

    kept: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    article_text: dict[str, list[str]] = defaultdict(list)
    for u in units:
        article = u["id"].split("/")[0]
        es = squash(strip_refs((u.get("source") or {}).get("content") or ""))
        en = squash(strip_refs((u.get("target") or {}).get("content") or ""))
        mt = squash(strip_refs((u.get("mt") or {}).get("content") or ""))
        article_text[article].append(es)
        if keep(es, en, mt):
            kept[article].append((u["id"], es, en))

    cats = categories([names[a]["en"] for a in kept if a in names], refresh)

    passages = []
    for article, rows in kept.items():
        name = names.get(article)
        es_title = name["es"] if name else ""
        topic = topics.classify_categories(cats.get(name["en"], []) if name else []) \
            or topics.classify(es_title + " " + " ".join(article_text[article]))
        for unit_id, es, en in rows:
            passages.append(
                Passage(
                    id=f"wikipedia:{unit_id}",
                    source="wikipedia",
                    title=es_title or f"Wikipedia translation {article}",
                    author="Wikipedia contributors",
                    location=f"English: {name['en']}" if name and ":" not in name["en"] else "",
                    topic=topic,
                    es=es,
                    en=en,
                    translator="Wikipedia editor (Content Translation)",
                    license="CC BY-SA 4.0",
                    url=f"https://es.wikipedia.org/wiki/{quote(es_title.replace(' ', '_'))}" if name else "",
                )
            )
    return passages
