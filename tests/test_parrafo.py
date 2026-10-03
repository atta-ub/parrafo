import random

import pytest

from parrafo import topics
from parrafo.config import format_duration, parse_duration
from parrafo.db import Store
from parrafo.sources import Passage, gracian, wikipedia
from parrafo.sources.textutil import strip_refs, unwrap_ocr


@pytest.mark.parametrize(
    "text,seconds",
    [("1h", 3600), ("3h", 10800), ("90m", 5400), ("1h30m", 5400), ("45s", 45), ("2", 7200), ("0.5", 1800)],
)
def test_parse_duration(text, seconds):
    assert parse_duration(text) == seconds


@pytest.mark.parametrize("bad", ["", "soon", "3x", "0h", "1h banana"])
def test_parse_duration_rejects(bad):
    with pytest.raises(ValueError):
        parse_duration(bad)


def test_format_duration():
    assert format_duration(5400) == "1h30m"
    assert format_duration(42) == "42s"


def test_roman():
    assert [gracian.roman(n) for n in (1, 4, 9, 14, 40, 68, 129, 184, 299)] == [
        "i", "iv", "ix", "xiv", "xl", "lxviii", "cxxix", "clxxxiv", "ccxcix",
    ]


def test_parse_wikisource():
    wikitext = """{{encabezado
|título=x
}}

1. ''Todo está ya en su punto.'' Más se requiere hoy
para un sabio.

{{c|🙝🙟}}

2. ''Genio e ingenio.'' Los dos ejes.<br>
Segunda línea.
"""
    out = gracian.parse_wikisource(wikitext)
    assert out == {
        1: "Todo está ya en su punto. Más se requiere hoy para un sabio.",
        2: "Genio e ingenio. Los dos ejes. Segunda línea.",
    }


def test_parse_jacobs_handles_ocr_noise():
    # Mimics the scan: TOC entry first, numerals OCR'd as "1"/"V", page headers, hyphenation.
    lines = ["junk"] * 3 + [
        "i  Everything  is  at  its  Acme  (Todo  esta)  1",
        "",
        "1   Everything  is  at  its  Acme  ; ",
        "",
        "especially  the  art  of  making  one's  way  in ",
        "the  world.  Nothing  with- ",
        "out  effort. ",
        "",
        "2  ART    OF    WORLDLY    WISDOM ",
        "",
        "ii   Character  and  Intellect : ",
        "",
        "the  two  poles.",
    ]
    text = "\n".join(lines)
    assert gracian.TOTAL == 300  # parser stops quietly when later numbers are absent
    out = gracian.parse_jacobs(text)
    assert out[1] == "Everything is at its Acme; especially the art of making one's way in the world. Nothing without effort."
    assert out[2] == "Character and Intellect: the two poles."


def test_unwrap_ocr_joins_hyphenated_lines():
    assert unwrap_ocr(["a  pro- ", "verb  here ;"]) == "a proverb here;"


def test_strip_refs():
    assert strip_refs("Nació en Lima.[3] Fue poeta.[12]") == "Nació en Lima. Fue poeta."


ES = (
    "La provincia de Tunja fue una entidad administrativa y territorial de la Nueva Granada, "
    "creada en 1539 como corregimiento del Virreinato del Perú. En 1717 una Real Cédula del rey "
    "Felipe V creó el Virreinato de Nueva Granada, y la provincia fue agregada a este último."
)
EN = (
    "The Province of Tunja was an administrative and territorial entity of New Granada, created "
    "in 1539 as a corregimiento of the Viceroyalty of Peru. In 1717 a royal decree of King Philip V "
    "created the Viceroyalty of New Granada, and the province was added to it."
)


def test_keep_accepts_good_pair():
    assert wikipedia.keep(ES, EN, mt="")


def test_keep_rejects_unedited_machine_translation():
    assert not wikipedia.keep(ES, EN, mt=EN)


def test_keep_rejects_untranslated_and_short():
    assert not wikipedia.keep(ES, ES, mt="")
    assert not wikipedia.keep("Corto. Texto.", "Short. Text.", mt="")


def test_classify_categories():
    assert topics.classify_categories(["Argentine footballers", "1990 births", "Living people"]) == "sports"
    assert topics.classify_categories(["Living people"]) is None
    assert topics.classify_categories([]) is None


def test_classify_text():
    text = "El equipo ganó la liga y el campeonato; el jugador marcó un gol en el torneo."
    assert topics.classify(text) == "sports"
    assert topics.classify("Una palabra.") == "general"


def _passage(i: int, topic: str) -> Passage:
    return Passage(f"t:{i}", "test", "T", "A", "", topic, f"es {i}", f"en {i}", "X", "PD", "")


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "t.db")
    s.replace_source("test", [_passage(i, "big") for i in range(50)] + [_passage(100, "small")])
    yield s
    s.close()


def test_pick_balances_topics(store):
    rng = random.Random(0)
    picks = [store.pick(rng=rng).topic for _ in range(200)]
    # "small" has 1 passage vs 50, but topics are chosen first, so it shows up often.
    assert picks.count("small") > 60


def test_pick_avoids_repeats_until_topic_exhausted(store):
    rng = random.Random(1)
    seen = set()
    for _ in range(50):
        p = store.pick(["big"], rng=rng)
        assert p.id not in seen
        seen.add(p.id)
        store.mark_shown(p.id)
    # All 50 read: the topic starts over instead of running dry.
    assert store.pick(["big"], rng=rng) is not None


def test_last_shown_and_rebuild_keeps_history(store):
    store.mark_shown("t:3", when=10.0)
    store.mark_shown("t:7", when=20.0)
    assert store.last_shown()[0].id == "t:7"
    store.replace_source("test", [_passage(7, "big")])
    assert store.last_shown()[0].id == "t:7"
    assert store.shown_since(15.0) == 1
