# learn-german

A command-line tool that reads German articles, finds the chunks in them, chiefly
Nomen-Verb-Verbindungen such as *eine Entscheidung treffen* or *zur Verfügung stellen*, and
adds production cards for them to Anki.

## Why

Moving from B2 to C1 is less about knowing more words than about using them: finding the
fixed phrase a native speaker would use, and building the sentence around it without
mistakes. Word lists train recognition. This tool trains production instead:

- It mines the texts you actually read, so the chunks are the ones you meet.
- For every chunk it writes two Anki notes on a shortened sentence from the text: a
  **transformation** card (rewrite a plain verbal sentence in nominal style with the chunk)
  and a **translation** card (say a sentence in your hint language in German, using the
  chunk).
- The card text comes from the Claude API. There is no review step: notes go straight into
  Anki, tagged so a bad batch can be found and deleted. `sync --dry-run` previews a run.

It is a single-user tool that runs on your own machine. Nothing is uploaded except the
sentences sent to the Claude API to write the cards.

## Requirements

- [uv](https://docs.astral.sh/uv/) 0.9 or newer. It installs Python 3.12 if you do not
  have it.
- [Anki](https://apps.ankiweb.net/) desktop with the AnkiConnect add-on (see below).
- A Claude API key from the [Claude Console](https://platform.claude.com/). Card generation
  costs a few cents per chunk; `add` and `status` are free.
- About 1 GB of disk space, most of it for the German spaCy model.

## Install

Install a released version from its git tag, with the `model` extra that brings the spaCy
model `de_core_news_lg` (about 500 MB):

```bash
uv tool install 'learn-german[model] @ git+https://github.com/JakobAyo/learn-german@v1.0.0'
learn-german --version
```

Pick the newest tag from the repository's Releases page. To upgrade, run the same command
with the newer tag and `--force`. Without the `model` extra, `add` and `reextract` stop
with an error that says how to install it.

## Set up Anki and AnkiConnect

1. Install Anki desktop and open it.
2. Install AnkiConnect: Tools, Add-ons, Get Add-ons, code `2055492159`. Restart Anki.
3. Leave AnkiConnect's configuration at its defaults. It listens on
   `http://127.0.0.1:8765`, and its `apiKey` must stay `null`.
4. Keep Anki open, with no dialog showing, while `sync` runs.

On the first `sync`, the tool creates the deck `learn-german::chunks` and two note types,
`learn-german-transformation-v1` and `learn-german-translation-v1`. You may restyle the
cards in Anki, but do not rename or reorder the note types' fields: the tool stops if they
differ from what it expects.

## Configure

Two settings are needed before `sync` can run: the hint language and the API key.

**Hint language.** The ISO 639 code of the language your translation cards are written
in, for example `en`. There is no default. Put it in the config file, which on Linux is
`~/.config/learn-german/config.toml` (on macOS
`~/Library/Application Support/learn-german/config.toml`):

```toml
hint_language = "en"
```

**API key.** Set `ANTHROPIC_API_KEY` in your environment, or put it in a `.env` file in the
directory you run `learn-german` from:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
# or, in ./.env:
ANTHROPIC_API_KEY=sk-ant-...
```

Do not put the key in `config.toml`, and never commit a `.env` file.

**Other settings** have defaults and rarely need changing. Each can go in `config.toml`,
in `.env`, or in an environment variable:

| `config.toml` key | Environment variable | Default |
|---|---|---|
| `hint_language` | `LEARN_GERMAN_HINT_LANGUAGE` | none, required for `sync` |
| `cap` | `LEARN_GERMAN_CAP` | `10` chunks per `sync` |
| `model` | `LEARN_GERMAN_MODEL` | `claude-opus-5-5` |
| `deck` | `LEARN_GERMAN_DECK` | `learn-german::chunks` |
| `anki_connect_url` | `LEARN_GERMAN_ANKI_CONNECT_URL` | `http://127.0.0.1:8765` |
| `database_path` | `LEARN_GERMAN_DATABASE_PATH` | `~/.local/share/learn-german/learn-german.db` |
| `provider` | `LEARN_GERMAN_PROVIDER` | `anthropic`, the only one in v1 |
| (none) | `ANTHROPIC_API_KEY` | none, required for `sync` |

When a setting is given in several places, the first of these wins: a command-line flag,
an environment variable, `.env` in the current directory, `config.toml`, the default. An
unknown key in `config.toml` is an error, so a typo does not go unnoticed.

## Use

The workflow has three steps: `add` collects sources, `status` shows what was found, and
`sync` turns the top chunks into Anki notes.

### 1. Add sources

```bash
learn-german add https://example.org/some-german-article
learn-german add article.txt another-article.txt
learn-german add --from reading-list.txt      # one URL or path per line, # for comments
```

`add` fetches each article (or reads each UTF-8 `.txt` file), finds its chunks and stores
both locally. It prints one line per source as it finishes. A source added before is
skipped; `add --force` fetches it again and updates its chunks.

The tool fetches only the page you give it, respects `robots.txt` and does not get around
paywalls. If a page fails (paywall, login, too little text), open it in your browser, save
the article text as a UTF-8 `.txt` file and add that file instead.

### 2. Check what was found

```bash
learn-german status            # sources, and the 10 chunks sync would take first
learn-german status --top 30
```

### 3. Sync to Anki

First preview a run without writing anything to Anki:

```bash
learn-german sync --dry-run --cap 3
```

This calls the Claude API and prints every note it would add. The generated content is
cached, so the real run that follows does not pay for it again. A dry run works with Anki
closed; it then only warns that it cannot check which notes Anki already has.

Then add the notes:

```bash
learn-german sync --cap 3      # 3 chunks, so 6 notes
learn-german sync              # up to the cap setting, 10 chunks by default
```

`sync` takes the pending chunks that occur most often in your sources, skips any chunk
whose notes are already in Anki, generates the card text, and adds two notes per chunk.
Each note is tagged `learn-german`, `provider::anthropic`, `model::<model>` and
`run::run-YYYYMMDD-HHMM`; to remove a bad batch, search for its `run::` tag in Anki's
browser and delete the notes. Running `sync` again adds only what is still missing, so
repeating it is safe.

If one chunk fails (the API is overloaded, the answer fails a check, Anki rejects a note),
the run goes on, lists the failure in its summary, and the next `sync` tries the chunk
again.

### Other commands

```bash
learn-german reextract         # find chunks again in all stored texts, without fetching
learn-german --help            # all commands; learn-german <command> --help for options
learn-german -v sync           # log fetches, LLM calls and Anki actions to stderr
```

`--verbose` (`-v`) goes before the command. It never prints the API key.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Everything worked, or there was nothing to do. |
| `1` | Some sources or chunks failed; the rest were done. The `failed` lines say why. A failed chunk is tried again by the next `sync`. |
| `2` | The command stopped: a usage error, a missing setting, Anki not reachable, the API key rejected, or a database problem. The message says what to do. |

## Where data is stored

| What | Linux | macOS |
|---|---|---|
| Settings | `~/.config/learn-german/config.toml` | `~/Library/Application Support/learn-german/config.toml` |
| Database | `~/.local/share/learn-german/learn-german.db` | `~/Library/Application Support/learn-german/learn-german.db` |
| API key | your environment, or `.env` in the working directory | the same |

The database is one SQLite file. It holds the text of every source you added, every chunk
occurrence found, which notes were pushed in which run, the last error per chunk, and the
cached Claude answers. Your cards live in Anki, not here. Deleting the database starts the
tool from scratch; `sync` then skips every chunk Anki already has.

## Troubleshooting

- **"Cannot reach AnkiConnect"**: start Anki, check that AnkiConnect is installed and
  enabled, and that `anki_connect_url` matches its address.
- **"AnkiConnect … did not answer … in time"**: close any open dialog in Anki and run the
  command again.
- **"No hint language is set"** or **"ANTHROPIC_API_KEY is not set"**: see
  [Configure](#configure).
- **"The spaCy model de_core_news_lg is not installed"**: install again with the `model`
  extra, as shown in [Install](#install).
- Anything else: run the command again with `-v` and read the log lines before the error.

## Development

See [docs/development/setup.md](docs/development/setup.md) for a development checkout,
and [docs/CLAUDE.md](docs/CLAUDE.md) for the documentation index.

## License

MIT, see [LICENSE](LICENSE).
