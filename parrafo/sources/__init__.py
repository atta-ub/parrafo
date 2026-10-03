"""Importers that turn bilingual sources into aligned Spanish/English passages."""

from dataclasses import dataclass


@dataclass
class Passage:
    id: str  # stable, unique across sources, e.g. "gracian:42"
    source: str  # short source key, e.g. "gracian" or "wikipedia"
    title: str  # book or article title
    author: str
    location: str  # where in the work, e.g. "Aforismo 42"
    topic: str
    es: str
    en: str
    translator: str  # who made the English, e.g. "Joseph Jacobs (1892)"
    license: str
    url: str
