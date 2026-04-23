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
import subprocess
import sys
import tempfile
from dataclasses import dataclass
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


def mirror_service(source_dir: Path, dest_dir: Path) -> int:
    """Mirror source_dir -> dest_dir (delete files removed upstream).

    Returns the number of files that differ post-sync vs pre-sync,
    determined by counting rsync's itemized changes.
    """
    if not source_dir.is_dir():
        raise FileNotFoundError(f"source directory missing: {source_dir}")
    dest_dir.mkdir(parents=True, exist_ok=True)
    # Trailing slashes matter to rsync: copy contents, not the dir itself.
    result = subprocess.run(
        [
            "rsync",
            "-a",
            "--delete",
            "--itemize-changes",
            f"{source_dir}/",
            f"{dest_dir}/",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    # Each itemized line that starts with '>' (file received) or '*deleting'
    # counts as a change. Directory-only entries start with 'c' and we skip them.
    changes = 0
    for line in result.stdout.splitlines():
        if line.startswith(">") or line.startswith("*deleting"):
            changes += 1
    return changes


def update_build_yml(build_path: Path, name: str, dest: str, sdk: str) -> tuple[bool, str | None]:
    """Update (or append) a service entry in this repo's jammin.build.yml.

    Returns (changed, previous_sdk):
      - changed: True if the file content was modified.
      - previous_sdk: the prior sdk pin if the entry already existed, else None.
    """
    with build_path.open() as f:
        data = yaml.load(f)
    if not isinstance(data, dict) or "services" not in data or not isinstance(data["services"], list):
        raise ValueError(f"{build_path}: missing or malformed 'services' list")

    existing = None
    for entry in data["services"]:
        if isinstance(entry, dict) and entry.get("name") == name:
            existing = entry
            break

    if existing is None:
        data["services"].append({"path": dest, "name": name, "sdk": sdk})
        previous_sdk = None
        changed = True
    else:
        previous_sdk = str(existing.get("sdk")) if existing.get("sdk") is not None else None
        if previous_sdk == sdk:
            changed = False
        else:
            existing["sdk"] = sdk
            changed = True

    if changed:
        with build_path.open("w") as f:
            yaml.dump(data, f)

    return changed, previous_sdk


def sync_source(entry: SourceEntry, repo_root: Path) -> SourceResult:
    """Sync a single source repo into this repo. Never raises; errors go into the result."""
    result = SourceResult(name=entry.name, status="failed")
    try:
        with tempfile.TemporaryDirectory() as tmp:
            src_root = Path(tmp) / "src"
            clone_source(entry.repo, src_root)
            sdk = read_source_sdk(src_root)
            dest_dir = repo_root / entry.dest
            files_changed = mirror_service(src_root / "services" / "example", dest_dir)
            yml_changed, previous_sdk = update_build_yml(
                repo_root / "jammin.build.yml", entry.name, entry.dest, sdk
            )
        result.files_changed = files_changed
        result.sdk_before = previous_sdk
        result.sdk_after = sdk
        if previous_sdk is None:
            # No entry in jammin.build.yml yet -> this is a brand-new service.
            result.status = "added"
        elif files_changed == 0 and not yml_changed:
            result.status = "unchanged"
        else:
            result.status = "updated"
        return result
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or b"").decode("utf-8", errors="replace") if isinstance(e.stderr, bytes) else (e.stderr or "")
        result.error = f"{e.cmd[0]} failed (exit {e.returncode}): {stderr.strip()[:500]}"
        return result
    except Exception as e:
        result.error = f"{type(e).__name__}: {e}"
        return result


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

    results: list[SourceResult] = []
    for entry in entries:
        print(f"syncing {entry.repo} -> {entry.dest}", file=sys.stderr)
        r = sync_source(entry, args.repo_root)
        results.append(r)
        if r.status == "failed":
            print(f"  failed: {r.error}", file=sys.stderr)
        else:
            print(f"  {r.status} (files_changed={r.files_changed}, sdk={r.sdk_before}->{r.sdk_after})", file=sys.stderr)

    summary = {
        "results": [r.__dict__ for r in results],
    }
    json.dump(summary, sys.stdout, indent=2)
    sys.stdout.write("\n")
    if args.summary_out:
        args.summary_out.write_text(json.dumps(summary, indent=2) + "\n")

    if results and all(r.status == "failed" for r in results):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
