#!/usr/bin/env python3
"""Validate a docs tree: naming rules, frontmatter schema, index freshness.

Exit code 0 = clean (warnings allowed), 1 = at least one ERROR.

Usage:
    validate_docs.py --docs-root docs
    validate_docs.py --docs-root docs --strict     # warnings also fail
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

import build_index
from docs_common import (
    ADR_RE, DECISIONS_DIR, INDEX_FILE, INDEX_REQUIRED_FIELDS, REQUIRED_FIELDS,
    STATUS_VALUES, FrontmatterError, is_decisions_dir, is_kebab, list_entries,
    iter_dirs, read_doc, rel, valid_date,
)

SUMMARY_MAX = 200
SUMMARY_WARN = 160


class Report:
    def __init__(self, base: Path):
        self.base = base
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, path: Path, msg: str) -> None:
        self.errors.append(f"ERROR {rel(path, self.base)}: {msg}")

    def warn(self, path: Path, msg: str) -> None:
        self.warnings.append(f"WARN  {rel(path, self.base)}: {msg}")


def check_name(entry: Path, docs_root: Path, report: Report) -> None:
    name = entry.name
    if entry.is_dir():
        if not is_kebab(name):
            report.error(entry, "folder name must be kebab-case (lowercase letters, digits, single hyphens)")
        return
    if name == INDEX_FILE:
        return
    if name.lower() == "readme.md":
        report.error(entry, "README.md is not allowed; the folder index is CLAUDE.md")
        return
    if entry.suffix.lower() == ".md":
        if is_decisions_dir(entry.parent, docs_root):
            if not ADR_RE.match(name):
                report.error(entry, "decision records must be named NNNN-short-title.md (four digits, kebab-case)")
        elif not is_kebab(entry.stem) or entry.suffix != ".md":
            report.error(entry, "file name must be kebab-case with a lowercase .md extension")
        return
    # Non-markdown files (images, diagrams): naming is advisory only.
    stem = entry.name.rsplit(".", 1)[0] if "." in entry.name else entry.name
    if not is_kebab(stem):
        report.warn(entry, "non-markdown file name is not kebab-case")


def check_frontmatter(doc: Path, report: Report, required: tuple[str, ...], check_status: bool) -> None:
    try:
        meta, _ = read_doc(doc)
    except FrontmatterError as exc:
        report.error(doc, f"malformed frontmatter: {exc}")
        return
    except UnicodeDecodeError:
        report.error(doc, "file is not valid UTF-8")
        return
    if meta is None:
        report.error(doc, f"missing frontmatter (required fields: {', '.join(required)})")
        return
    for field in required:
        value = meta.get(field)
        if value is None or (isinstance(value, str) and not value.strip()) or value == []:
            report.error(doc, f"frontmatter field '{field}' is missing or empty")
    for field in ("title", "summary"):
        if isinstance(meta.get(field), list):
            report.error(doc, f"frontmatter field '{field}' must be a single line, not a list")
    summary = meta.get("summary")
    if isinstance(summary, str):
        if len(summary) > SUMMARY_MAX:
            report.error(doc, f"summary longer than {SUMMARY_MAX} characters; it must fit on one index line")
        elif len(summary) > SUMMARY_WARN:
            report.warn(doc, f"summary longer than {SUMMARY_WARN} characters; consider shortening")
        if "\n" in summary:
            report.error(doc, "summary must be a single line")
    if check_status:
        status = meta.get("status")
        if isinstance(status, str) and status and status not in STATUS_VALUES:
            report.error(doc, f"status must be one of {', '.join(STATUS_VALUES)}; got {status!r}")
        updated = meta.get("updated")
        if isinstance(updated, str) and updated:
            if not valid_date(updated):
                report.error(doc, f"updated must be a real date in YYYY-MM-DD form; got {updated!r}")
            elif dt.date.fromisoformat(updated) > dt.date.today():
                report.error(doc, f"updated is in the future: {updated}")
    tags = meta.get("tags")
    if tags is not None and not isinstance(tags, list):
        report.error(doc, "tags must be a list, e.g. tags: [security, api]")


def check_adr_numbering(decisions: Path, report: Report) -> None:
    _, docs, _ = list_entries(decisions)
    numbers: dict[int, Path] = {}
    for doc in docs:
        m = ADR_RE.match(doc.name)
        if not m:
            continue
        n = int(m.group(1))
        if n in numbers:
            report.error(doc, f"decision number {n:04d} is already used by {numbers[n].name}")
        numbers[n] = doc
    if numbers:
        expected = set(range(1, max(numbers) + 1))
        gaps = sorted(expected - set(numbers))
        if gaps:
            report.warn(decisions, "gaps in decision numbering: " + ", ".join(f"{g:04d}" for g in gaps))


def validate(docs_root: Path, base: Path) -> Report:
    report = Report(base)
    for directory in iter_dirs(docs_root):
        if directory != docs_root:
            check_name(directory, docs_root, report)
        index = directory / INDEX_FILE
        if not index.exists():
            report.error(index, "every folder needs a CLAUDE.md index (build_index.py --create-missing)")
        else:
            check_frontmatter(index, report, INDEX_REQUIRED_FIELDS, check_status=False)
        subdirs, docs, others = list_entries(directory)
        for entry in [*docs, *others]:
            check_name(entry, docs_root, report)
        for doc in docs:
            check_frontmatter(doc, report, REQUIRED_FIELDS, check_status=True)
        if directory != docs_root and not (subdirs or docs or others):
            report.warn(directory, "folder is empty; add a document or remove the folder")

    decisions = docs_root / DECISIONS_DIR
    if decisions.is_dir():
        check_adr_numbering(decisions, report)
    else:
        report.warn(docs_root, f"no {DECISIONS_DIR}/ folder; decisions are not being recorded")

    stale, missing = build_index.build(docs_root, check=True)
    for path in stale:
        report.error(path, "index is out of date; run build_index.py")
    for path in missing:
        if not any(line.startswith(f"ERROR {rel(path, base)}:") for line in report.errors):
            report.error(path, "missing CLAUDE.md index")
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--docs-root", default="docs")
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    args = ap.parse_args(argv)

    docs_root = Path(args.docs_root).resolve()
    if not docs_root.is_dir():
        print(f"ERROR docs root not found: {docs_root}", file=sys.stderr)
        return 2
    report = validate(docs_root, Path.cwd())
    for line in [*report.errors, *report.warnings]:
        print(line)
    failed = bool(report.errors) or (args.strict and bool(report.warnings))
    print(f"{len(report.errors)} error(s), {len(report.warnings)} warning(s): {'FAIL' if failed else 'OK'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
