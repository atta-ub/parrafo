"""SQLite store for passages and reading history."""

import random
import sqlite3
import time
from dataclasses import astuple, fields
from pathlib import Path

from .sources import Passage

SCHEMA = """
CREATE TABLE IF NOT EXISTS passages (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    location TEXT NOT NULL,
    topic TEXT NOT NULL,
    es TEXT NOT NULL,
    en TEXT NOT NULL,
    translator TEXT NOT NULL,
    license TEXT NOT NULL,
    url TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS passages_topic ON passages(topic);
CREATE TABLE IF NOT EXISTS history (
    passage_id TEXT NOT NULL,
    shown_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS history_passage ON history(passage_id);
"""

_COLUMNS = [f.name for f in fields(Passage)]


class Store:
    def __init__(self, path: Path):
        self.conn = sqlite3.connect(path)
        self.conn.executescript(SCHEMA)

    def close(self) -> None:
        self.conn.close()

    # --- building -------------------------------------------------------

    def replace_source(self, source: str, passages: list[Passage]) -> None:
        """Swap in a fresh import of one source; history is kept."""
        with self.conn:
            self.conn.execute("DELETE FROM passages WHERE source = ?", (source,))
            placeholders = ", ".join("?" * len(_COLUMNS))
            self.conn.executemany(
                f"INSERT OR REPLACE INTO passages ({', '.join(_COLUMNS)}) VALUES ({placeholders})",
                [astuple(p) for p in passages],
            )

    # --- reading --------------------------------------------------------

    def topic_counts(self) -> dict[str, int]:
        rows = self.conn.execute("SELECT topic, COUNT(*) FROM passages GROUP BY topic ORDER BY 2 DESC")
        return dict(rows.fetchall())

    def seen_counts(self) -> dict[str, int]:
        rows = self.conn.execute(
            "SELECT p.topic, COUNT(DISTINCT h.passage_id) FROM history h "
            "JOIN passages p ON p.id = h.passage_id GROUP BY p.topic"
        )
        return dict(rows.fetchall())

    def get(self, passage_id: str) -> Passage | None:
        row = self.conn.execute(
            f"SELECT {', '.join(_COLUMNS)} FROM passages WHERE id = ?", (passage_id,)
        ).fetchone()
        return Passage(*row) if row else None

    def pick(self, topics: list[str] | None = None, rng: random.Random | None = None) -> Passage | None:
        """Pick an unseen passage.

        A topic is chosen first (uniformly), then a passage within it, so a
        small topic like philosophy comes up as often as a huge one like arts.
        Once every passage in a topic has been shown, that topic starts over.
        """
        rng = rng or random.Random()
        available = self.topic_counts()
        candidates = [t for t in (topics or available) if available.get(t)]
        if not candidates:
            return None
        topic = rng.choice(candidates)
        unseen = (
            "SELECT id FROM passages WHERE topic = ? "
            "AND id NOT IN (SELECT passage_id FROM history)"
        )
        ids = [r[0] for r in self.conn.execute(unseen, (topic,))]
        if not ids:
            # Everything in this topic has been read: forget it and start again.
            with self.conn:
                self.conn.execute(
                    "DELETE FROM history WHERE passage_id IN (SELECT id FROM passages WHERE topic = ?)",
                    (topic,),
                )
            ids = [r[0] for r in self.conn.execute("SELECT id FROM passages WHERE topic = ?", (topic,))]
        return self.get(rng.choice(ids))

    def mark_shown(self, passage_id: str, when: float | None = None) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO history (passage_id, shown_at) VALUES (?, ?)",
                (passage_id, when if when is not None else time.time()),
            )

    def last_shown(self) -> tuple[Passage, float] | None:
        row = self.conn.execute(
            "SELECT passage_id, shown_at FROM history ORDER BY shown_at DESC LIMIT 1"
        ).fetchone()
        if not row:
            return None
        passage = self.get(row[0])
        return (passage, row[1]) if passage else None

    def shown_since(self, since: float) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM history WHERE shown_at >= ?", (since,)).fetchone()[0]
