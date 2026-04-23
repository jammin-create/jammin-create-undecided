#!/usr/bin/env python3
"""Render the sync script's JSON summary into a Markdown PR body.

Reads JSON (list of results) from a file path (argv[1]) and writes Markdown to stdout.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def render(summary: dict) -> str:
    results = summary.get("results", [])
    lines: list[str] = ["Automated sync from source repos.", ""]

    changes = [r for r in results if r["status"] == "updated"]
    added = [r for r in results if r["status"] == "added"]
    failures = [r for r in results if r["status"] == "failed"]

    if changes:
        lines.append("## Changes")
        lines.append("")
        for r in changes:
            prefix = f"- `{r['name']}`:"
            parts = []
            if r.get("sdk_before") and r.get("sdk_after") and r["sdk_before"] != r["sdk_after"]:
                parts.append(f"sdk pin `{r['sdk_before']}` -> `{r['sdk_after']}`")
            if r.get("files_changed"):
                parts.append(f"{r['files_changed']} file(s) changed")
            if not parts:
                parts.append("updated")
            lines.append(f"{prefix} " + ", ".join(parts))
        lines.append("")

    if added:
        lines.append("## New services")
        lines.append("")
        for r in added:
            lines.append(f"- `{r['name']}`: added (sdk `{r.get('sdk_after')}`)")
        lines.append("")

    if failures:
        lines.append("## Failures")
        lines.append("")
        for r in failures:
            lines.append(f"- `{r['name']}`: {r.get('error')}")
        lines.append("")

    if not (changes or added or failures):
        lines.append("_No changes detected in any source._")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: format_pr_body.py <summary.json>", file=sys.stderr)
        return 2
    summary = json.loads(Path(sys.argv[1]).read_text())
    sys.stdout.write(render(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
