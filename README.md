# parrafo

Learn Spanish one real paragraph at a time: every hour (or whatever interval
you choose), parrafo shows a Spanish paragraph in your terminal, then its
published English translation.

## Requirements

- Python 3.11 or newer
- Internet access once, for the first build (downloads about 20 MB)

## Install

### NixOS (no install needed)

The `parrafo-run` script gets Python and the libraries from `shell.nix`:

```sh
cd /path/to/spanish
./parrafo-run --help
```

Use `./parrafo-run` wherever this guide says `parrafo`.

### Any other Linux or macOS

```sh
cd /path/to/spanish
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
parrafo --help
```

## First run: build the library

```sh
parrafo build
```

This downloads the sources once and saves the library to
`~/.local/share/parrafo/parrafo.db`. Wikimedia asks API users to identify
themselves, so you can set a contact address first:

```sh
PARRAFO_CONTACT=you@example.com parrafo build
```

## Run it

```sh
parrafo                      # show a paragraph now (same as: parrafo next)
parrafo next -t history      # only from one topic (repeat -t for more)
parrafo again                # show the last paragraph again
parrafo topics               # list the topics and how much you've read
parrafo stats                # how many you've read today, this week, this month
```

While a paragraph is on screen, press **Enter** to reveal the English.
Options for `next`, `again` and `watch`:

- `--reveal enter|delay|instant`: how the translation appears
- `--order es-en|en-es`: `en-es` shows the English first, as a reverse challenge

## Run it every few hours

Pick one:

1. **In a terminal tab:** `parrafo watch --every 3h`
2. **When you open a new shell:** add `parrafo due` to `~/.bashrc`. It shows a
   paragraph only if the interval has passed since the last one.
3. **As a desktop notification:** set `notify = true` in the config and run
   `parrafo next --reveal instant` from cron or a systemd user timer. This
   option hasn't been tested yet; see `README.org` for an example timer.

## Settings

```sh
parrafo config          # show the settings file
parrafo config --edit   # open it in $EDITOR
```

The file is `~/.config/parrafo/config.toml`:

```toml
every = "1h"          # "3h", "90m", "1h30m" ...
order = "es-en"
reveal = "enter"      # enter | delay | instant
reveal_delay = 30     # seconds, for reveal = "delay"
topics = []           # e.g. ["philosophy", "history"]; empty = all
notify = false        # also send a desktop notification
```

## Update or rebuild the library

```sh
parrafo build --refresh          # download the sources again
parrafo build -s gracian         # rebuild one source only (gracian | wikipedia)
```

Rebuilding keeps your reading history.

## Run the tests

```sh
nix-shell --run "PYTHONPATH=. python -m pytest -q"   # NixOS
pip install -e '.[test]' && pytest -q                 # elsewhere
```

For more about where the paragraphs come from and how they're chosen, see
`README.org`.
