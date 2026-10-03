"""XDG locations for config, data and download cache."""

import os
from pathlib import Path


def _xdg(var: str, default: str) -> Path:
    base = Path(os.environ.get(var) or Path.home() / default)
    path = base / "parrafo"
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_dir() -> Path:
    return _xdg("XDG_CONFIG_HOME", ".config")


def data_dir() -> Path:
    return _xdg("XDG_DATA_HOME", ".local/share")


def cache_dir() -> Path:
    return _xdg("XDG_CACHE_HOME", ".cache")


def db_path() -> Path:
    return Path(os.environ.get("PARRAFO_DB") or data_dir() / "parrafo.db")
