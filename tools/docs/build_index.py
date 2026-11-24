#!/usr/bin/env python3
"""Generate the index sections of every CLAUDE.md under a docs root.

The generated text sits between the markers
    <!-- docs-index:start -->  and  <!-- docs-index:end -->
Everything outside the markers is hand-written and preserved.

Usage:
    build_index.py --docs-root docs            # rewrite indexes in place
    build_index.py --docs-root docs --check    # exit 1 if any index is stale
    build_index.py --docs-root docs --create-missing   # add a minimal CLAUDE.md where none exists
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from docs_common import (
    INDEX_END, INDEX_FILE, INDEX_START, FrontmatterError, is_decisions_dir,
    list_entries, iter_dirs, load_template, read_doc, rel, render, titleize,
)

MARK_RE = re.compile(re.escape(INDEX_START) + r".*?" + re.escape(INDEX_END), re.DOTALL)


def doc_line(doc: Path, base: Path) -> str:
    """One index line for a document, relative to base."""
    link = rel(doc, base)
    try:
        meta, _ = read_doc(doc)
    except (FrontmatterError, UnicodeDecodeError):
        return f"- [{doc.stem}]({link}) — (invalid frontmatter)"
    if not meta:
        return f"- [{doc.stem}]({link}) — (no frontmatter)"
    title = str(meta.get("title") or doc.stem)
    summary = str(meta.get("summary") or "(no summary)")
    status = str(meta.get("status") or "")
    flag = f" `[{status}]`" if status and status != "active" else ""
    return f"- [{title}]({link}){flag} — {summary}"


def folder_summary(directory: Path) -> str:
    index = directory / INDEX_FILE
    if not index.exists():
        return "(no CLAUDE.md)"
    try:
        meta, _ = read_doc(index)
    except (FrontmatterError, UnicodeDecodeError):
        return "(invalid frontmatter in CLAUDE.md)"
    return str((meta or {}).get("summary") or "(no summary)")


def folder_block(directory: Path, base: Path) -> list[str]:
    """Index lines for one folder: its docs, other files and subfolder pointers."""
    subdirs, docs, others = list_entries(directory)
    lines: list[str] = []
    if docs:
        lines.extend(doc_line(d, base) for d in docs)
    if others:
        lines.append("")
        lines.append("Other files:")
        lines.extend(f"- {rel(o, base)}" for o in others)
    if subdirs:
        lines.append("")
        lines.append("Subfolders:")
        for sub in subdirs:
            lines.append(f"- [{sub.name}/]({rel(sub / INDEX_FILE, base)}) — {folder_summary(sub)}")
    if not (docs or others or subdirs):
        lines.append("- (empty)")
    return lines


def render_folder_index(directory: Path) -> str:
    return "\n".join([INDEX_START, "", "## Contents", "", *folder_block(directory, directory), "", INDEX_END])


def render_root_index(docs_root: Path) -> str:
    lines = [INDEX_START, "", "## Index", ""]
    subdirs, docs, others = list_entries(docs_root)
    if docs or others:
        lines.append("### (root)")
        lines.append("")
        lines.extend(doc_line(d, docs_root) for d in docs)
        lines.extend(f"- {rel(o, docs_root)}" for o in others)
        lines.append("")
    for directory in iter_dirs(docs_root):
        if directory == docs_root:
            continue
        relpath = rel(directory, docs_root)
        lines.append(f"### [{relpath}/]({relpath}/{INDEX_FILE})")
        lines.append("")
        lines.append(folder_summary(directory))
        lines.append("")
        _, d_docs, d_others = list_entries(directory)
        if d_docs:
            lines.extend(doc_line(d, docs_root) for d in d_docs)
        if d_others:
            lines.extend(f"- {rel(o, docs_root)}" for o in d_others)
        if not (d_docs or d_others):
            lines.append("- (empty)")
        lines.append("")
    lines.append(INDEX_END)
    return "\n".join(lines)


def splice(existing: str, generated: str) -> str:
    if MARK_RE.search(existing):
        return MARK_RE.sub(lambda _m: generated, existing, count=1)
    sep = "" if existing.endswith("\n\n") else ("\n" if existing.endswith("\n") else "\n\n")
    return existing + sep + generated + "\n"


PLACEHOLDER_PREFIX = "TODO: describe what "


def is_placeholder_index(index_path: Path) -> bool:
    """True when the CLAUDE.md was auto-created by --create-missing and never edited."""
    try:
        meta, body = read_doc(index_path)
    except (FrontmatterError, UnicodeDecodeError, OSError):
        return False
    return (
        str((meta or {}).get("summary", "")).startswith(PLACEHOLDER_PREFIX)
        or f"{PLACEHOLDER_PREFIX}this project is." in body
    )


def minimal_index_file(directory: Path, docs_root: Path) -> str:
    title = titleize(directory.name)
    if directory == docs_root:
        return render(load_template("root-claude.md"), {
            "project_name": docs_root.parent.name,
            "project_summary": f"{PLACEHOLDER_PREFIX}this project is.",
            "index_start": INDEX_START,
            "index_end": INDEX_END,
        })
    template = "decisions-claude.md" if is_decisions_dir(directory, docs_root) and directory.parent == docs_root else "folder-claude.md"
    return render(load_template(template), {
        "title": title,
        "summary": f"{PLACEHOLDER_PREFIX}{title} covers.",
        "belongs": "- TODO",
        "excludes": "- TODO",
        "docs_root": rel(docs_root, Path.cwd()),
        "index_start": INDEX_START,
        "index_end": INDEX_END,
    })


def build(docs_root: Path, check: bool = False, create_missing: bool = False) -> tuple[list[Path], list[Path]]:
    """Return (changed_or_stale, missing_index_files)."""
    stale: list[Path] = []
    missing: list[Path] = []
    for directory in iter_dirs(docs_root):
        index_path = directory / INDEX_FILE
        if not index_path.exists():
            if create_missing and not check:
                index_path.write_text(minimal_index_file(directory, docs_root), encoding="utf-8")
            else:
                missing.append(index_path)
                continue
        generated = render_root_index(docs_root) if directory == docs_root else render_folder_index(directory)
        existing = index_path.read_text(encoding="utf-8")
        updated = splice(existing, generated)
        if updated != existing:
            stale.append(index_path)
            if not check:
                index_path.write_text(updated, encoding="utf-8")
    return stale, missing


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--docs-root", default="docs", help="path to the docs folder (default: docs)")
    ap.add_argument("--check", action="store_true", help="do not write; exit 1 if any index is stale")
    ap.add_argument("--create-missing", action="store_true", help="create a minimal CLAUDE.md in folders lacking one")
    args = ap.parse_args(argv)

    docs_root = Path(args.docs_root).resolve()
    if not docs_root.is_dir():
        print(f"ERROR docs root not found: {docs_root}", file=sys.stderr)
        return 2

    stale, missing = build(docs_root, check=args.check, create_missing=args.create_missing)
    base = Path.cwd()
    for m in missing:
        print(f"MISSING {rel(m, base)} (run with --create-missing or write it by hand)")
    if args.check:
        for s in stale:
            print(f"STALE {rel(s, base)}")
        if stale or missing:
            return 1
        print("index up to date")
        return 0
    for s in stale:
        print(f"UPDATED {rel(s, base)}")
    if not stale:
        print("index already up to date")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
