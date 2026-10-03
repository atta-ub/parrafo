"""Baltasar Gracián, *Oráculo manual y arte de prudencia* (1647).

Spanish: es.wikisource (public domain text).
English: Joseph Jacobs, *The Art of Worldly Wisdom* (1892; 1904 reprint),
OCR text from the Internet Archive scan. Public domain.

Both are numbered 1-300, so aphorisms align exactly by number.
"""

import re
from urllib.parse import quote

from . import Passage
from .fetch import fetch_text
from .textutil import squash, unwrap_ocr

WIKISOURCE_PAGE = "Oráculo manual y arte de prudencia/Aforismos ({a}-{b})"
WIKISOURCE_RAW = "https://es.wikisource.org/w/index.php?title={title}&action=raw"
WIKISOURCE_URL = "https://es.wikisource.org/wiki/{title}"
JACOBS_TXT = "https://archive.org/download/artofworldlywisd00gracuoft/artofworldlywisd00gracuoft_djvu.txt"

TOTAL = 300


def roman(n: int) -> str:
    out = []
    for value, sym in ((100, "c"), (90, "xc"), (50, "l"), (40, "xl"), (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")):
        while n >= value:
            out.append(sym)
            n -= value
    return "".join(out)


# OCR in the scan confuses i/l/1/| and occasionally c/e, x/z/i.
_OCR_CLASS = {"i": "[i1l|!]", "l": "[l1i|]", "c": "[ce]", "v": "v", "x": "[xzi]"}


def _numeral_line(n: int, drop_first: bool = False) -> re.Pattern:
    """Heading line for aphorism `n`, e.g. "cxiii  In Prosperity prepare..."

    With `drop_first`, the numeral's first letter may be missing ("xxix" for cxxix).
    """
    chars = roman(n)[1:] if drop_first else roman(n)
    pat = r"\s?".join(_OCR_CLASS[ch] for ch in chars)
    # Italic capitals in titles often OCR as "/", "J" or "^".
    return re.compile(rf"^\s*{pat}\b[\s.,^]+(?P<title>[A-Z/\"'(].*)$", re.I)


_PAGE_HEADER = re.compile(r"^\s*\S{0,4}\s*ART\s+OF\s+WORLDLY\s+W\S+\s*\S{0,4}\s*$", re.I)
_END_OF_TEXT = re.compile(r"^\s*(NOTES|INDEX|THE END)\s*$")


def _is_junk(line: str) -> bool:
    s = line.strip()
    if _PAGE_HEADER.match(s):
        return True
    # Stray OCR debris such as "^ B" or a lone page number.
    return bool(s) and len(re.sub(r"[^A-Za-z]", "", s)) <= 2 and len(s) <= 6


def parse_jacobs(text: str) -> dict[int, str]:
    """Split the OCR text into {number: "Title. Body"}."""
    lines = text.splitlines()
    # Aphorism 1's heading appears twice: in the table of contents, then in the text.
    acme = [i for i, l in enumerate(lines) if re.search(r"Everything\s+is\s+at\s+its\s+Acme", l)]
    start = acme[1]
    starts: dict[int, int] = {}
    titles: dict[int, str] = {}
    cursor = start
    for n in range(1, TOTAL + 1):
        for pat in (_numeral_line(n), _numeral_line(n, drop_first=n >= 100)):
            i = _find_heading(lines, pat, cursor)
            if i is not None:
                starts[n] = i
                cursor = i + 1
                titles[n] = pat.match(lines[i]).group("title")
                break

    end = next(
        (i for i in range(cursor, len(lines)) if _END_OF_TEXT.match(lines[i])),
        len(lines),
    )
    found = sorted(starts)
    out: dict[int, str] = {}
    for idx, n in enumerate(found):
        first = starts[n]
        last = starts[found[idx + 1]] if idx + 1 < len(found) else end
        body = [l for l in lines[first + 1 : last] if not _is_junk(l)]
        out[n] = unwrap_ocr([titles[n].lstrip("/ ")] + body)
    return out


def _find_heading(lines: list[str], pat: re.Pattern, cursor: int) -> int | None:
    for i in range(cursor, min(cursor + 400, len(lines))):
        prev_blank = not lines[i - 1].strip() or _is_junk(lines[i - 1])
        if prev_blank and pat.match(lines[i]):
            return i
    return None


_ES_ITEM = re.compile(r"^(\d+)\.\s*(.*)$")


def parse_wikisource(wikitext: str) -> dict[int, str]:
    """Split one Wikisource page of aphorisms into {number: text}."""
    out: dict[int, str] = {}
    current: int | None = None
    for raw in wikitext.splitlines():
        line = raw.strip()
        if line.startswith(("{{", "}}", "|", "[[Categoría")):
            continue
        m = _ES_ITEM.match(line)
        if m:
            current = int(m.group(1))
            out[current] = m.group(2)
        elif current is not None and line:
            out[current] += " " + line
    for n, text in out.items():
        text = text.replace("<br>", " ").replace("<br />", " ")
        text = re.sub(r"'''?", "", text)
        text = re.sub(r"<[^>]+>", "", text)
        out[n] = squash(text)
    return out


def load_spanish() -> dict[int, str]:
    out: dict[int, str] = {}
    for a in range(1, TOTAL + 1, 25):
        title = WIKISOURCE_PAGE.format(a=a, b=a + 24)
        url = WIKISOURCE_RAW.format(title=quote(title))
        out.update(parse_wikisource(fetch_text(url, name=f"gracian-es-{a}.wiki")))
    return out


def load(refresh: bool = False) -> list[Passage]:
    es = load_spanish()
    en = parse_jacobs(fetch_text(JACOBS_TXT, name="gracian-jacobs.txt", refresh=refresh))
    passages = []
    for n in range(1, TOTAL + 1):
        if n not in es or n not in en:
            continue
        a = (n - 1) // 25 * 25 + 1
        page = WIKISOURCE_PAGE.format(a=a, b=a + 24)
        passages.append(
            Passage(
                id=f"gracian:{n}",
                source="gracian",
                title="Oráculo manual y arte de prudencia",
                author="Baltasar Gracián (1647)",
                location=f"Aforismo {n}",
                topic="philosophy",
                es=es[n],
                en=en[n],
                translator="Joseph Jacobs, The Art of Worldly Wisdom (1892)",
                license="Public domain",
                url=WIKISOURCE_URL.format(title=quote(page.replace(" ", "_"))),
            )
        )
    return passages
