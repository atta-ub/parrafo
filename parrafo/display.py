"""Terminal rendering with rich."""

import time

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .config import Config
from .sources import Passage

TOPIC_STYLE = {
    "philosophy": ("🦉", "magenta"),
    "history": ("🏛 ", "yellow"),
    "travel": ("🧭", "green"),
    "computers": ("💻", "cyan"),
    "sports": ("⚽", "bright_green"),
    "news": ("📰", "bright_blue"),
    "science": ("🔬", "blue"),
    "arts": ("🎭", "red"),
    "general": ("📖", "white"),
}

LANG = {"es": ("Español", "bold bright_yellow"), "en": ("English", "bold bright_cyan")}


def _header(p: Passage) -> Text:
    icon, color = TOPIC_STYLE.get(p.topic, TOPIC_STYLE["general"])
    t = Text()
    t.append(f" {icon} {p.topic.upper()} ", style=f"bold black on {color}")
    t.append("  ")
    t.append(p.title, style="bold")
    if p.location:
        t.append(f"  ·  {p.location}", style="dim")
    t.append(f"\n{p.author}", style="italic dim")
    return t


def _lang_panel(p: Passage, lang: str) -> Panel:
    name, style = LANG[lang]
    body = Text(getattr(p, lang))
    return Panel(body, title=Text(name, style=style), title_align="left", border_style=style.split()[-1], padding=(1, 2))


def _footer(p: Passage) -> Text:
    t = Text(style="dim")
    t.append(f"Translation: {p.translator}  ·  {p.license}")
    if p.url:
        t.append("\n")
        t.append(p.url, style=f"dim link {p.url}")
    return t


def show(console: Console, p: Passage, cfg: Config, *, reveal: str | None = None) -> None:
    first, second = cfg.order.split("-")
    reveal = reveal or cfg.reveal
    if not console.is_terminal and reveal == "enter":
        reveal = "instant"  # nobody to press Enter (cron, pipes)

    console.print()
    console.print(_header(p))
    console.print(_lang_panel(p, first))

    if reveal == "enter":
        console.input(Text("  ↵ Enter to reveal the translation…", style="dim"))
    elif reveal == "delay":
        with console.status(f"Translation in {cfg.reveal_delay}s — try it in your head first…"):
            time.sleep(cfg.reveal_delay)

    console.print(_lang_panel(p, second))
    console.print(_footer(p))
    console.print()


def notification_text(p: Passage, cfg: Config) -> tuple[str, str]:
    first = cfg.order.split("-")[0]
    return f"Párrafo · {p.topic} · {p.title}", getattr(p, first)
