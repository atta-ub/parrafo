"""Keyword-based topic classifier for Spanish text.

The Wikipedia translation dumps carry no titles or categories, so each
article's topic is guessed from the Spanish words it uses. Scores are counted
over the whole article (all its paragraphs), which is much steadier than
classifying single paragraphs.
"""

import re
from collections import Counter

TOPICS = ["philosophy", "history", "travel", "computers", "sports", "news", "science", "arts"]

# Stems are matched at the start of a word, so "futbol" also hits "futbolista".
KEYWORDS: dict[str, list[str]] = {
    "philosophy": [
        "filosof", "filósof", "ética", "metafísic", "epistemolog", "ontolog", "razón",
        "pensamiento", "conciencia", "moral", "lógica", "kant", "hegel", "aristóteles",
        "platón", "sócrates", "existencial", "fenomenolog", "dialéctic", "virtud", "alma",
    ],
    "history": [
        "siglo", "imperio", "reino", "rey", "reina", "conquista", "batalla", "guerra",
        "dinastía", "colonial", "virreinato", "medieval", "antigu", "revolución", "monarca",
        "ejército", "tratado", "independencia", "romano", "arqueológ", "histori",
    ],
    "travel": [
        "turis", "viaje", "viajer", "playa", "montaña", "isla", "río", "parque nacional",
        "pueblo", "aldea", "municipio", "habitantes", "kilómetros", "altitud", "clima",
        "paisaje", "costa", "ruta", "visitantes", "localidad", "provincia", "valle",
    ],
    "computers": [
        "software", "informátic", "computador", "ordenador", "programa", "programación",
        "algoritm", "internet", "red ", "datos", "digital", "sistema operativo", "código",
        "aplicación", "videojuego", "servidor", "linux", "windows", "web", "usuario",
        "tecnolog", "inteligencia artificial", "procesador", "criptograf", "electrónic",
    ],
    "sports": [
        "fútbol", "futbol", "deport", "jugador", "equipo", "liga", "campeonato", "torneo",
        "gol", "partido", "olímpic", "atleta", "entrenador", "temporada", "copa",
        "selección", "baloncesto", "tenis", "ciclis", "boxeo", "medalla", "estadio",
    ],
    "news": [
        "gobierno", "elecciones", "elección", "presidente", "ministro", "partido político",
        "congreso", "senado", "protesta", "manifestación", "política", "polític", "ley",
        "derechos humanos", "periodis", "corrupción", "economía", "crisis", "sindicat",
        "votos", "candidat", "parlamento", "alcalde", "diputad", "asesinato", "violencia",
    ],
    "science": [
        "especie", "género", "científic", "biolog", "químic", "físic", "células", "proteína",
        "molécul", "planta", "familia", "hábitat", "evolución", "genétic", "astronom",
        "planeta", "estrella", "matemátic", "teorema", "enfermedad", "investigación",
    ],
    "arts": [
        "película", "cine", "actor", "actriz", "música", "músic", "álbum", "canción",
        "novela", "poeta", "poesía", "pintor", "pintura", "teatro", "escultor", "artista",
        "banda", "disco", "obra", "literatura", "escritor", "serie", "televisión",
    ],
}

_PATTERNS = {
    topic: re.compile(r"\b(?:" + "|".join(re.escape(k) for k in words) + r")", re.I)
    for topic, words in KEYWORDS.items()
}


def scores(text: str) -> Counter:
    return Counter({topic: len(p.findall(text)) for topic, p in _PATTERNS.items()})


def classify(text: str, min_hits: int = 4, margin: float = 1.3) -> str:
    """Return the best topic, or "general" when no topic clearly wins."""
    ranked = scores(text).most_common(2)
    (best, top), (_, second) = ranked[0], ranked[1]
    if top < min_hits or top < second * margin:
        return "general"
    return best


# Substrings of English Wikipedia category names, e.g. "Spanish footballers".
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "philosophy": ["philosoph", "ethic", "metaphysic", "epistemolog", "logician", "theolog"],
    "history": [
        "history", "historical", "empire", "kingdom", "wars", "battles", "colonial",
        "ancient", "medieval", "archaeolog", "dynast", "monarchs", "conquistador",
        "-century", "revolution", "military personnel", "nobility",
    ],
    "travel": [
        "tourist attraction", "populated places", "municipalities", "geography", "islands",
        "mountains", "rivers", "beaches", "national parks", "villages", "towns", "cities",
        "protected areas", "landforms", "cuisine", "festivals", "neighbourhoods", "parks",
    ],
    "computers": [
        "software", "computing", "computer", "internet", "video game", "programming",
        "technology compan", "artificial intelligence", "information technology",
        "websites", "cryptocurrenc", "electronics", "engineers", "startups", "streamers",
        "youtubers",
    ],
    "sports": [
        "footballer", "football", "sport", "olympic", "athlete", "basketball", "tennis",
        "cyclist", "boxer", "competitions", "tournament", "championship", "rugby",
        "baseball", "futsal", "racing", "swimmers", "coaches", "chess",
    ],
    "news": [
        "politician", "political part", "elections", "government", "protests", "activists",
        "journalist", "human rights", "terroris", "crime", "murder", "legislat", "ministers",
        "diplomats", "scandals", "disasters", "presidents", "mayors", "deputies", "senators",
        "trade union", "corruption", "economy", "conflicts",
    ],
    "science": [
        "scientist", "biolog", "chemist", "physicist", "species", "genera", "taxa",
        "astronom", "mathematic", "medicine", "diseases", "botan", "zoolog", "ecology",
        "geolog", "physicians", "researchers", "fauna", "flora",
    ],
    "arts": [
        "films", "actors", "actresses", "musicians", "singers", "albums", "songs", "novels",
        "writers", "poets", "painters", "artists", "television", "theatre", "dancers",
        "bands", "comics", "books", "composers", "photographers", "sculptors", "architecture",
    ],
}

_IGNORED_CATEGORY = re.compile(r"births|deaths|living people|articles|pages|wikidata|cs1", re.I)


def classify_categories(categories: list[str]) -> str | None:
    """Topic from English category names, or None when they don't decide it."""
    counts = Counter()
    for cat in categories:
        if _IGNORED_CATEGORY.search(cat):
            continue
        low = cat.lower()
        for topic, words in CATEGORY_KEYWORDS.items():
            if any(w in low for w in words):
                counts[topic] += 1
    ranked = counts.most_common(2) + [("", 0)] * 2
    (best, top), (_, second) = ranked[0], ranked[1]
    return best if top and top > second else None
