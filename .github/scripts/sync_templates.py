#!/usr/bin/env python3
"""Mirror per-SDK template source repos into this repo.

Reads .github/sync-config.yml, shallow-clones each source repo at main,
mirrors services/example/ into the mapped destination, syncs the SDK pin
in the top-level jammin.build.yml, and emits a JSON summary on stdout.

Exit codes:
  0  success (zero or more sources updated, at most partial failures)
  1  every configured source failed (fatal)
  2  local repo state broken (bad jammin.build.yml, bad config, ...)
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from ruamel.yaml import YAML


yaml = YAML()
yaml.preserve_quotes = True
yaml.indent(mapping=2, sequence=4, offset=2)


@dataclass
class SourceEntry:
    repo: str
    name: str
    dest: str


@dataclass
class SourceResult:
    name: str
    status: str  # "updated" | "unchanged" | "added" | "failed"
    sdk_before: str | None = None
    sdk_after: str | None = None
    files_changed: int = 0
    error: str | None = None


def load_config(path: Path) -> list[SourceEntry]:
    with path.open() as f:
        data = yaml.load(f)
    if not isinstance(data, dict) or "sources" not in data:
        raise ValueError(f"{path}: missing top-level 'sources' key")
    entries = []
    for raw in data["sources"]:
        entries.append(SourceEntry(repo=raw["repo"], name=raw["name"], dest=raw["dest"]))
    names = [e.name for e in entries]
    if len(set(names)) != len(names):
        raise ValueError(f"{path}: duplicate 'name' values: {names}")
    return entries


def clone_source(repo: str, dst: Path) -> None:
    """Shallow-clone a public GitHub repo at main into `dst`."""
    url = f"https://github.com/{repo}.git"
    subprocess.run(
        ["git", "clone", "--depth", "1", "--branch", "main", url, str(dst)],
        check=True,
        capture_output=True,
    )


def read_source_sdk(source_root: Path) -> str:
    """Extract the single service's sdk pin from a source repo's jammin.build.yml."""
    build_path = source_root / "jammin.build.yml"
    if not build_path.exists():
        raise FileNotFoundError("source repo missing jammin.build.yml")
    with build_path.open() as f:
        data = yaml.load(f)
    services = data.get("services") or []
    if not services:
        raise ValueError("source jammin.build.yml has no services")
    sdk = services[0].get("sdk")
    if not sdk:
        raise ValueError("source jammin.build.yml services[0] has no sdk")
    return str(sdk)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(".github/sync-config.yml"),
        help="path to sync-config.yml (default: .github/sync-config.yml)",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
        help="path to this repo's root (default: current dir)",
    )
    parser.add_argument(
        "--summary-out",
        type=Path,
        default=None,
        help="if set, also write the JSON summary to this path",
    )
    args = parser.parse_args()

    try:
        entries = load_config(args.config)
    except Exception as e:
        print(f"ERROR loading config: {e}", file=sys.stderr)
        return 2

    # Per-source sync will be added in Task 6.
    results: list[SourceResult] = []

    summary = {
        "results": [r.__dict__ for r in results],
    }
    json.dump(summary, sys.stdout, indent=2)
    sys.stdout.write("\n")
    if args.summary_out:
        args.summary_out.write_text(json.dumps(summary, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
