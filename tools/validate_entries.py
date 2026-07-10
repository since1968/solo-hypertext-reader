#!/usr/bin/env python3
"""Validate a Solo Hypertext Reader entries JSON file.

Usage:
    python3 tools/validate_entries.py [entries_file] [--json]

Exit codes:
    0  validation passed (no errors; warnings do not fail the build)
    1  validation errors found
    2  could not load or parse the entries file
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field

DEFAULT_ENTRIES_PATH = "examples/demo_adventure.json"

# Kept in sync with LINK_REGEX_SOURCE in app.js.
LINK_PATTERN = re.compile(
    r"\b(?:turn|return)\s+(?:immediately\s+)?to\s+(?:paragraph\s+)?(\d+)\b",
    re.IGNORECASE,
)


@dataclass
class Report:
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    endings: list = field(default_factory=list)

    @property
    def passed(self):
        return not self.errors


def load_entries(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except OSError as err:
        raise SystemExit(f"Could not read '{path}': {err}")
    except json.JSONDecodeError as err:
        raise SystemExit(f"'{path}' is not valid JSON: {err}")
    if not isinstance(data, dict):
        raise SystemExit(f"'{path}' must contain a JSON object of entries")
    return data


def extract_targets(body):
    return {m.group(1) for m in LINK_PATTERN.finditer(body)}


def validate(entries):
    report = Report()

    for key, entry in entries.items():
        if not isinstance(entry, dict):
            report.errors.append(f"entry '{key}': not a JSON object")
            continue

        entry_id = entry.get("id")
        if str(entry_id) != key:
            report.warnings.append(
                f"entry '{key}': id field is {entry_id!r}, expected '{key}'"
            )

        body = entry.get("body")
        if not isinstance(body, str) or not body.strip():
            report.errors.append(f"entry '{key}': missing or empty body")
            continue

        targets = extract_targets(body)
        for target in sorted(targets, key=int):
            if target not in entries:
                report.errors.append(
                    f"entry '{key}': broken link -> '{target}' (no such entry)"
                )

        if not targets:
            report.endings.append(key)

    numeric_keys = [int(k) for k in entries.keys() if k.lstrip("-").isdigit()]
    if numeric_keys:
        expected = set(range(min(numeric_keys), max(numeric_keys) + 1))
        missing = sorted(expected - set(numeric_keys))
        for m in missing:
            report.warnings.append(f"gap in id range: no entry '{m}'")

    return report


def format_text_report(report, source_path, entry_count):
    lines = []
    lines.append(f"Solo Hypertext Reader validation: {source_path}")
    lines.append(f"  {entry_count} entries loaded")
    lines.append("")

    lines.append(f"ERRORS ({len(report.errors)})")
    for e in report.errors:
        lines.append(f"  - {e}")
    lines.append("")

    lines.append(f"WARNINGS ({len(report.warnings)})")
    for w in report.warnings:
        lines.append(f"  - {w}")
    lines.append("")

    lines.append(f"ENDINGS ({len(report.endings)})")
    lines.append("  entries with no detected outgoing links (review these):")
    for key in sorted(report.endings, key=int):
        lines.append(f"  - {key}")
    lines.append("")

    lines.append(f"SUMMARY: {'PASS' if report.passed else 'FAIL'}")
    return "\n".join(lines)


def format_json_report(report, source_path, entry_count):
    return json.dumps(
        {
            "source": source_path,
            "entry_count": entry_count,
            "errors": report.errors,
            "warnings": report.warnings,
            "endings": sorted(report.endings, key=int),
            "passed": report.passed,
        },
        indent=2,
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "entries_file",
        nargs="?",
        default=DEFAULT_ENTRIES_PATH,
        help=f"path to entries JSON (default: {DEFAULT_ENTRIES_PATH})",
    )
    parser.add_argument(
        "--json", action="store_true", help="emit a machine-readable JSON report"
    )
    args = parser.parse_args(argv)

    try:
        entries = load_entries(args.entries_file)
    except SystemExit as err:
        print(err, file=sys.stderr)
        return 2

    report = validate(entries)

    if args.json:
        print(format_json_report(report, args.entries_file, len(entries)))
    else:
        print(format_text_report(report, args.entries_file, len(entries)))

    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
