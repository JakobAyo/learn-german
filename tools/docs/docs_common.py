"""Shared rules and helpers for the docs-architect scripts.

Stdlib only. Everything that defines "what a valid docs tree looks like"
lives here so the scaffold, index builder, validator, migrator and hook
all agree.
"""

from __future__ import annotations

import datetime as _dt
import os
import re
import subprocess
from pathlib import Path

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------

INDEX_FILE = "CLAUDE.md"
INDEX_START = "<!-- docs-index:start -->"
INDEX_END = "<!-- docs-index:end -->"
ROOT_POINTER_MARK = "<!-- docs-architect:pointer -->"

DECISIONS_DIR = "decisions"

STATUS_VALUES = ("draft", "active", "deprecated", "superseded")
REQUIRED_FIELDS = ("title", "summary", "status", "updated")
INDEX_REQUIRED_FIELDS = ("title", "summary")

KEBAB_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
ADR_RE = re.compile(r"^(\d{4})-[a-z0-9]+(-[a-z0-9]+)*\.md$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

IGNORE_DIR_NAMES = {
    ".git", ".hg", ".svn", "node_modules", ".venv", "venv", "__pycache__",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", "dist", "build", "target",
    ".next", ".nuxt", ".cache", ".idea", ".vscode", ".tox", ".terraform",
    "graphify-out",
}

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "assets" / "templates"


# --------------------------------------------------------------------------
# Small utilities
# --------------------------------------------------------------------------

def today() -> str:
    return _dt.date.today().isoformat()


def is_hidden(name: str) -> bool:
    return name.startswith(".")


def is_kebab(name: str) -> bool:
    return bool(KEBAB_RE.match(name))


def to_kebab(text: str) -> str:
    """Best-effort conversion of any string to kebab-case."""
    text = text.strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", text)  # camelCase -> camel-Case
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text or "untitled"


def titleize(stem: str) -> str:
    stem = re.sub(r"^\d{4}-", "", stem)
    return " ".join(w.capitalize() for w in re.split(r"[-_\s]+", stem) if w)


def valid_date(value: str) -> bool:
    if not DATE_RE.match(value or ""):
        return False
    try:
        _dt.date.fromisoformat(value)
    except ValueError:
        return False
    return True


def rel(path: Path, base: Path) -> str:
    return os.path.relpath(path, base).replace(os.sep, "/")


def load_template(name: str) -> str:
    return (TEMPLATES_DIR / name).read_text(encoding="utf-8")


def render(template: str, values: dict[str, str]) -> str:
    out = template
    for key, val in values.items():
        out = out.replace("{{" + key + "}}", val)
    return out


# --------------------------------------------------------------------------
# Frontmatter: a deliberately small YAML subset
#   key: value            scalar (quotes optional)
#   key: [a, b, c]        inline list
#   key:                  block list
#     - a
#     - b
#   # comment lines are ignored
# --------------------------------------------------------------------------

class FrontmatterError(ValueError):
    pass


def split_frontmatter(text: str) -> tuple[str | None, str]:
    """Return (frontmatter_text, body). frontmatter_text is None if absent."""
    if not text.startswith("---"):
        return None, text
    lines = text.split("\n")
    if lines[0].strip() != "---":
        return None, text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[1:i]), "\n".join(lines[i + 1:])
    raise FrontmatterError("frontmatter opened with --- but never closed")


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def _parse_inline_list(value: str) -> list[str]:
    inner = value.strip()[1:-1].strip()
    if not inner:
        return []
    return [_unquote(part) for part in inner.split(",")]


def parse_frontmatter(fm_text: str) -> dict[str, str | list[str]]:
    data: dict[str, str | list[str]] = {}
    current_list_key: str | None = None
    for lineno, raw in enumerate(fm_text.split("\n"), start=2):
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        stripped = line.strip()
        if stripped.startswith("- ") and current_list_key is not None:
            data[current_list_key].append(_unquote(stripped[2:]))  # type: ignore[union-attr]
            continue
        current_list_key = None
        m = re.match(r"^([A-Za-z0-9_-]+)\s*:\s*(.*)$", stripped)
        if not m:
            raise FrontmatterError(f"line {lineno}: expected 'key: value', got {stripped!r}")
        key, value = m.group(1), m.group(2).strip()
        if key in data:
            raise FrontmatterError(f"line {lineno}: duplicate key {key!r}")
        if value == "":
            data[key] = []
            current_list_key = key
        elif value.startswith("[") and value.endswith("]"):
            data[key] = _parse_inline_list(value)
        else:
            data[key] = _unquote(value)
    return data


def _quote_if_needed(value: str) -> str:
    needs = (
        value == ""
        or value != value.strip()
        or ": " in value
        or value[0] in "[]{}#&*!|>'\"%@`-"
        or value.endswith(":")
    )
    if needs:
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return value


def dump_frontmatter(data: dict[str, str | list[str]]) -> str:
    lines = ["---"]
    for key, value in data.items():
        if isinstance(value, list):
            lines.append(f"{key}: [" + ", ".join(_quote_if_needed(v) for v in value) + "]")
        else:
            lines.append(f"{key}: {_quote_if_needed(str(value))}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def read_doc(path: Path) -> tuple[dict | None, str]:
    """Return (meta, body). meta is None when there is no frontmatter.
    Raises FrontmatterError on malformed frontmatter."""
    text = path.read_text(encoding="utf-8")
    fm_text, body = split_frontmatter(text)
    if fm_text is None:
        return None, body
    return parse_frontmatter(fm_text), body


def write_doc(path: Path, meta: dict, body: str) -> None:
    body = body.lstrip("\n")
    path.write_text(dump_frontmatter(meta) + "\n" + body, encoding="utf-8")


# --------------------------------------------------------------------------
# Tree walking
# --------------------------------------------------------------------------

def iter_dirs(docs_root: Path):
    """Yield every directory under docs_root (including root), skipping hidden ones."""
    for dirpath, dirnames, _ in os.walk(docs_root):
        dirnames[:] = sorted(d for d in dirnames if not is_hidden(d) and d not in IGNORE_DIR_NAMES)
        yield Path(dirpath)


def list_entries(directory: Path) -> tuple[list[Path], list[Path], list[Path]]:
    """Return (subdirs, md_docs, other_files) for one directory, sorted, hidden skipped.
    md_docs excludes the index file."""
    subdirs, docs, others = [], [], []
    for entry in sorted(directory.iterdir(), key=lambda p: p.name):
        if is_hidden(entry.name) or entry.name in IGNORE_DIR_NAMES:
            continue
        if entry.is_dir():
            subdirs.append(entry)
        elif entry.suffix.lower() == ".md":
            if entry.name != INDEX_FILE:
                docs.append(entry)
        else:
            others.append(entry)
    return subdirs, docs, others


def is_decisions_dir(directory: Path, docs_root: Path) -> bool:
    try:
        return directory.relative_to(docs_root).parts[:1] == (DECISIONS_DIR,)
    except ValueError:
        return False


# --------------------------------------------------------------------------
# Git helpers (optional, never required)
# --------------------------------------------------------------------------

def git(args: list[str], cwd: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True, timeout=20, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    return out.stdout


def in_git_repo(path: Path) -> bool:
    return (git(["rev-parse", "--is-inside-work-tree"], path) or "").strip() == "true"


def git_tracked(path: Path, cwd: Path) -> bool:
    return git(["ls-files", "--error-unmatch", str(path)], cwd) is not None


def git_last_date(path: Path, cwd: Path) -> str | None:
    out = git(["log", "-1", "--format=%cs", "--", str(path)], cwd)
    out = (out or "").strip()
    return out if valid_date(out) else None
