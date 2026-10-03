"""Small text-cleanup helpers shared by the source importers."""

import re

_REF = re.compile(r"\[\d+\]|\[cita requerida\]|\[citation needed\]|\[nota \d+\]", re.I)
_SPACES = re.compile(r"[ \t ]+")


def strip_refs(text: str) -> str:
    """Remove Wikipedia-style footnote markers like [3]."""
    return _REF.sub("", text)


def squash(text: str) -> str:
    """Collapse runs of whitespace and tidy spacing before punctuation."""
    text = _SPACES.sub(" ", text)
    text = re.sub(r" +([,;:.!?)])", r"\1", text)
    text = re.sub(r"([(¿¡]) +", r"\1", text)
    return text.strip()


def unwrap_ocr(lines: list[str]) -> str:
    """Join hard-wrapped OCR lines into one paragraph, healing hyphenation.

    The Internet Archive text puts a space after a line-break hyphen
    ("with- out"), so both "with-\\nout" and "with- out" are merged.
    """
    text = " ".join(line.strip() for line in lines if line.strip())
    text = re.sub(r"(\w)- (\w)", r"\1\2", text)
    # Common OCR slips in the Jacobs scan.
    text = text.replace("„", ",").replace("^", "").replace("  ", " ")
    return squash(text)
