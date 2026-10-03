"""User settings, read from ~/.config/parrafo/config.toml."""

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .paths import config_dir

DEFAULT_TOML = """\
# parrafo settings

# How often a new paragraph is due: "1h", "3h", "90m", "1h30m", "45s" ...
every = "1h"

# "es-en" shows Spanish first; "en-es" flips it into a reverse challenge.
order = "es-en"

# How the translation is revealed after the first language:
#   "enter"   wait for you to press Enter (default)
#   "delay"   reveal automatically after reveal_delay seconds
#   "instant" show both at once
reveal = "enter"
reveal_delay = 30

# Topics to draw from; empty means all. Run `parrafo topics` to see them.
# e.g. topics = ["philosophy", "history", "travel", "computers", "sports", "news"]
topics = []

# Send a desktop notification (notify-send) as well, useful with cron/systemd.
notify = false
"""

ORDERS = ("es-en", "en-es")
REVEALS = ("enter", "delay", "instant")


@dataclass
class Config:
    every: str = "1h"
    order: str = "es-en"
    reveal: str = "enter"
    reveal_delay: int = 30
    topics: list[str] = field(default_factory=list)
    notify: bool = False

    @property
    def every_seconds(self) -> int:
        return parse_duration(self.every)


def config_path() -> Path:
    return config_dir() / "config.toml"


def ensure_config() -> Path:
    path = config_path()
    if not path.exists():
        path.write_text(DEFAULT_TOML)
    return path


def load() -> Config:
    path = config_path()
    data = tomllib.loads(path.read_text()) if path.exists() else {}
    known = {k: v for k, v in data.items() if k in Config.__dataclass_fields__}
    cfg = Config(**known)
    validate(cfg)
    return cfg


def validate(cfg: Config) -> None:
    parse_duration(cfg.every)
    if cfg.order not in ORDERS:
        raise ValueError(f"order must be one of {ORDERS}, got {cfg.order!r}")
    if cfg.reveal not in REVEALS:
        raise ValueError(f"reveal must be one of {REVEALS}, got {cfg.reveal!r}")


_DURATION = re.compile(r"(\d+(?:\.\d+)?)\s*([hms])")
_UNITS = {"h": 3600, "m": 60, "s": 1}


def parse_duration(text: str) -> int:
    """'3h' -> 10800, '1h30m' -> 5400, '90m' -> 5400, '2' -> 7200 (bare = hours)."""
    text = str(text).strip().lower()
    if re.fullmatch(r"\d+(\.\d+)?", text):
        return int(float(text) * 3600)
    parts = _DURATION.findall(text)
    if not parts or _DURATION.sub("", text).strip():
        raise ValueError(f"can't understand duration {text!r}; try '1h', '3h' or '90m'")
    seconds = int(sum(float(n) * _UNITS[u] for n, u in parts))
    if seconds <= 0:
        raise ValueError("duration must be positive")
    return seconds


def format_duration(seconds: float) -> str:
    seconds = int(round(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    out = (f"{h}h" if h else "") + (f"{m}m" if m else "")
    return out or f"{s}s"
