"""parrafo: a Spanish paragraph, with its English translation, every so often."""

import os
import shutil
import subprocess
import time
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from . import config as config_mod
from .config import Config, format_duration, parse_duration
from .db import Store
from .display import TOPIC_STYLE, notification_text, show
from .paths import db_path

app = typer.Typer(add_completion=False, no_args_is_help=False, help=__doc__)
console = Console()

SOURCES = ("gracian", "wikipedia")

TopicOpt = Annotated[Optional[list[str]], typer.Option("--topic", "-t", help="Limit to a topic (repeatable).")]
RevealOpt = Annotated[Optional[str], typer.Option(help="enter | delay | instant")]
OrderOpt = Annotated[Optional[str], typer.Option(help="es-en | en-es")]


def _settings(reveal: str | None = None, order: str | None = None, topics: list[str] | None = None) -> Config:
    try:
        cfg = config_mod.load()
        if reveal:
            cfg.reveal = reveal
        if order:
            cfg.order = order
        if topics:
            cfg.topics = topics
        config_mod.validate(cfg)
    except (ValueError, OSError) as e:
        console.print(f"[red]Config problem:[/] {e}")
        raise typer.Exit(2)
    return cfg


def _store() -> Store:
    store = Store(db_path())
    if not store.topic_counts():
        console.print("[yellow]The library is empty.[/] Run [bold]parrafo build[/] first (downloads ~20 MB).")
        raise typer.Exit(1)
    return store


def _notify(title: str, body: str) -> None:
    if shutil.which("notify-send"):
        subprocess.run(["notify-send", "--app-name=parrafo", title, body[:300]], check=False)


def _show_next(store: Store, cfg: Config) -> bool:
    unknown = [t for t in cfg.topics if t not in store.topic_counts()]
    if unknown:
        console.print(f"[red]Unknown topic(s):[/] {', '.join(unknown)}. See [bold]parrafo topics[/].")
        raise typer.Exit(2)
    passage = store.pick(cfg.topics)
    if passage is None:
        console.print("[yellow]No passages match those topics.[/]")
        return False
    store.mark_shown(passage.id)
    if cfg.notify:
        _notify(*notification_text(passage, cfg))
    show(console, passage, cfg)
    return True


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        ctx.invoke(next_)


@app.command("next")
def next_(topic: TopicOpt = None, reveal: RevealOpt = None, order: OrderOpt = None) -> None:
    """Show a new paragraph now."""
    _show_next(_store(), _settings(reveal, order, topic))


@app.command()
def again(reveal: RevealOpt = None, order: OrderOpt = None) -> None:
    """Show the last paragraph again."""
    store, cfg = _store(), _settings(reveal, order)
    last = store.last_shown()
    if not last:
        console.print("Nothing shown yet. Try [bold]parrafo next[/].")
        raise typer.Exit(1)
    show(console, last[0], cfg)


@app.command()
def due(topic: TopicOpt = None) -> None:
    """Show a paragraph only if one is due (handy in ~/.bashrc)."""
    store, cfg = _store(), _settings(topics=topic)
    last = store.last_shown()
    if last and time.time() - last[1] < cfg.every_seconds:
        return
    _show_next(store, cfg)


@app.command()
def watch(
    every: Annotated[Optional[str], typer.Option(help='Interval, e.g. "1h", "3h", "90m".')] = None,
    topic: TopicOpt = None,
    reveal: RevealOpt = None,
    order: OrderOpt = None,
) -> None:
    """Keep running and show a new paragraph every interval (Ctrl-C to stop)."""
    store, cfg = _store(), _settings(reveal, order, topic)
    if every:
        cfg.every = every
    try:
        interval = parse_duration(cfg.every)
    except ValueError as e:
        console.print(f"[red]{e}[/]")
        raise typer.Exit(2)

    console.print(f"[dim]parrafo: a new paragraph every {format_duration(interval)}. Ctrl-C to stop.[/]")
    try:
        while True:
            last = store.last_shown()
            wait = 0 if not last else last[1] + interval - time.time()
            if wait > 0:
                at = time.strftime("%H:%M", time.localtime(time.time() + wait))
                console.print(f"[dim]Next paragraph at {at} (in {format_duration(wait)}).[/]")
                time.sleep(wait)
            _show_next(store, cfg)
    except KeyboardInterrupt:
        console.print("\n[dim]¡Hasta luego![/]")


@app.command()
def topics() -> None:
    """List topics with how many paragraphs you've read in each."""
    store = _store()
    seen = store.seen_counts()
    table = Table(title="Topics", show_edge=False)
    table.add_column("topic")
    table.add_column("paragraphs", justify="right")
    table.add_column("read", justify="right")
    for name, count in store.topic_counts().items():
        icon, color = TOPIC_STYLE.get(name, TOPIC_STYLE["general"])
        table.add_row(f"[{color}]{icon} {name}[/]", str(count), str(seen.get(name, 0)))
    console.print(table)


@app.command()
def stats() -> None:
    """How much you've read lately."""
    store = _store()
    now = time.time()
    total = sum(store.topic_counts().values())
    console.print(f"Library: [bold]{total:,}[/] paragraphs")
    for label, secs in (("today", 86400), ("this week", 7 * 86400), ("this month", 30 * 86400)):
        console.print(f"Read {label}: [bold]{store.shown_since(now - secs)}[/]")
    last = store.last_shown()
    if last:
        console.print(f"Last one: {last[0].title} ({format_duration(now - last[1])} ago)")


@app.command()
def build(
    source: Annotated[Optional[list[str]], typer.Option("--source", "-s", help="gracian | wikipedia (default: both)")] = None,
    refresh: Annotated[bool, typer.Option(help="Re-download instead of using the cache.")] = False,
) -> None:
    """Download the sources and (re)build the local library."""
    from .sources import gracian, wikipedia

    loaders = {"gracian": gracian.load, "wikipedia": wikipedia.load}
    wanted = source or list(SOURCES)
    bad = [s for s in wanted if s not in loaders]
    if bad:
        console.print(f"[red]Unknown source(s):[/] {', '.join(bad)}. Choose from {', '.join(SOURCES)}.")
        raise typer.Exit(2)
    store = Store(db_path())
    for name in wanted:
        with console.status(f"Importing {name}…"):
            passages = loaders[name](refresh=refresh)
        store.replace_source(name, passages)
        console.print(f"[green]✓[/] {name}: {len(passages):,} paragraphs")
    console.print(f"Library saved to [dim]{db_path()}[/]")


@app.command("config")
def config_cmd(edit: Annotated[bool, typer.Option(help="Open the config in $EDITOR.")] = False) -> None:
    """Show (or edit) the settings file: interval, order, reveal mode, topics."""
    path = config_mod.ensure_config()
    if edit:
        subprocess.run([os.environ.get("EDITOR", "nano"), str(path)], check=False)
    console.print(f"[dim]{path}[/]\n")
    console.print(path.read_text(), highlight=False, markup=False)


if __name__ == "__main__":
    app()
