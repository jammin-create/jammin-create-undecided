# Auto-sync Templates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a daily GitHub Actions workflow that mirrors per-SDK source template repos (`jammin-create-jade`, `-jambrains`, `-jam-sdk`, `-ajanta`, `-jamc3`) into `jammin-create-undecided` and opens a PR with any drift.

**Architecture:** A single workflow in this repo runs a Python sync script that reads `.github/sync-config.yml`, shallow-clones each source, mirrors `services/example/` into the matching local directory, syncs the SDK version pin in the top-level `jammin.build.yml`, and uses `peter-evans/create-pull-request` (with a GitHub App token) to surface any diff as a rolling PR on branch `sync/templates`.

**Tech Stack:** GitHub Actions, Python 3.12, `ruamel.yaml` (to preserve YAML formatting), `rsync`, `actions/create-github-app-token@v1`, `peter-evans/create-pull-request@v6`.

**Testing approach:** Per the design spec, no unit tests. Each task ends with a manual local verification step (running the script against the real public source repos, since they're publicly clonable). Final verification is the first `workflow_dispatch` run after merging the workflow.

**Reference:** `docs/superpowers/specs/2026-04-23-auto-sync-templates-design.md`

---

## File Structure

Files created by this plan:

- `.github/sync-config.yml` — declarative list of source repos → destination mapping.
- `.github/scripts/sync_templates.py` — sync script (single file, ~150 LOC).
- `.github/scripts/format_pr_body.py` — formats the sync script's JSON summary into Markdown for the PR body.
- `.github/workflows/sync-templates.yml` — the workflow.

No existing files are modified except on manual first-run execution, where the workflow's opening PR will touch `jammin.build.yml` and `services/**`.

Responsibility split:

- **Config** (`sync-config.yml`) — the list of sources. Pure data. Adding a new SDK = edit this file only.
- **Sync script** (`sync_templates.py`) — all the sync logic. Pure function shape: `(config, repo_root) → (mutations_on_disk, JSON summary)`. Runnable locally with zero GitHub-specific setup because source repos are public.
- **PR body formatter** (`format_pr_body.py`) — small and separate so the sync script stays focused on syncing, and the body formatter can be iterated on without re-running the sync.
- **Workflow** (`sync-templates.yml`) — triggers, auth, step orchestration. No business logic.

---

## Task 1: Create the sync config file

**Files:**
- Create: `.github/sync-config.yml`

- [ ] **Step 1: Create the config file**

```yaml
# Source repos that get mirrored into this template.
# Each entry:
#   repo: owner/name on github.com
#   name: value used in this repo's jammin.build.yml services[].name (must be unique)
#   dest: local directory where the source's services/example/ is mirrored
#         (also used as services[].path in this repo's jammin.build.yml)
sources:
  - repo: jammin-create/jammin-create-jade
    name: jade
    dest: services/example-jade
  - repo: jammin-create/jammin-create-jambrains
    name: jambrains
    dest: services/example-jambrains
  - repo: jammin-create/jammin-create-jam-sdk
    name: jamsdk
    dest: services/example-jamsdk
  - repo: jammin-create/jammin-create-ajanta
    name: ajanta
    dest: services/example-ajanta
  - repo: jammin-create/jammin-create-jamc3
    name: jamc3
    dest: services/example-jamc3
```

- [ ] **Step 2: Sanity-check config by eyeballing**

Run: `cat .github/sync-config.yml`
Expected: file contents as above; five entries; no typos in repo names.

- [ ] **Step 3: Commit**

```bash
git add .github/sync-config.yml
git commit -m "chore: add sync-config.yml listing source template repos"
```

---

## Task 2: Create the sync script skeleton (CLI + config loader)

**Files:**
- Create: `.github/scripts/sync_templates.py`

- [ ] **Step 1: Create the script with argument parsing and config loading**

```python
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
```

- [ ] **Step 2: Make it executable**

Run: `chmod +x .github/scripts/sync_templates.py`
Expected: no output.

- [ ] **Step 3: Install ruamel.yaml locally to run the script**

Run: `python3 -m pip install --user ruamel.yaml`
Expected: ruamel.yaml installed (or already satisfied).

- [ ] **Step 4: Verify script runs and parses config**

Run: `python3 .github/scripts/sync_templates.py`
Expected: prints `{"results": []}` and exits 0.

- [ ] **Step 5: Verify config errors are handled**

Run: `python3 .github/scripts/sync_templates.py --config /nonexistent`
Expected: prints `ERROR loading config: ...` to stderr, exit code 2.
Verify: `echo $?` → `2`.

- [ ] **Step 6: Commit**

```bash
git add .github/scripts/sync_templates.py
git commit -m "feat(sync): add script skeleton with config loader"
```

---

## Task 3: Add source-repo clone + sdk extraction

**Files:**
- Modify: `.github/scripts/sync_templates.py`

- [ ] **Step 1: Add `clone_source` and `read_source_sdk` functions**

Insert these functions after `load_config` (before `main`):

```python
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
```

- [ ] **Step 2: Verify the functions work against a real public source repo**

Run:
```bash
python3 -c "
from pathlib import Path
import sys, tempfile
sys.path.insert(0, '.github/scripts')
from sync_templates import clone_source, read_source_sdk
with tempfile.TemporaryDirectory() as tmp:
    dst = Path(tmp) / 'jade'
    clone_source('jammin-create/jammin-create-jade', dst)
    print('sdk:', read_source_sdk(dst))
    print('has services/example:', (dst / 'services' / 'example').is_dir())
"
```

Expected: prints something like `sdk: jade-0.0.15-pre.1` and `has services/example: True`.

- [ ] **Step 3: Commit**

```bash
git add .github/scripts/sync_templates.py
git commit -m "feat(sync): add source clone and SDK-pin extraction"
```

---

## Task 4: Add service-directory mirror logic

**Files:**
- Modify: `.github/scripts/sync_templates.py`

- [ ] **Step 1: Add `mirror_service` function**

Insert after `read_source_sdk`:

```python
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
```

- [ ] **Step 2: Verify mirroring works against a real source repo**

Run:
```bash
python3 -c "
from pathlib import Path
import sys, tempfile
sys.path.insert(0, '.github/scripts')
from sync_templates import clone_source, mirror_service
with tempfile.TemporaryDirectory() as tmp:
    src = Path(tmp) / 'src'
    dst = Path(tmp) / 'dest'
    clone_source('jammin-create/jammin-create-jade', src)
    n = mirror_service(src / 'services' / 'example', dst)
    print('changes:', n)
    print('dst contents:', sorted(p.name for p in dst.iterdir()))
    # Second run should report 0 changes (idempotent).
    n2 = mirror_service(src / 'services' / 'example', dst)
    print('second-run changes:', n2)
"
```

Expected: first run prints several changes and dst contents including `Cargo.toml`, `src`, etc.; second run prints `second-run changes: 0`.

- [ ] **Step 3: Commit**

```bash
git add .github/scripts/sync_templates.py
git commit -m "feat(sync): add idempotent rsync-based service mirror"
```

---

## Task 5: Add top-level `jammin.build.yml` update logic

**Files:**
- Modify: `.github/scripts/sync_templates.py`

- [ ] **Step 1: Add `update_build_yml` function**

Insert after `mirror_service`:

```python
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
```

- [ ] **Step 2: Verify the function against a copy of the real file**

Run:
```bash
python3 -c "
from pathlib import Path
import shutil, sys, tempfile
sys.path.insert(0, '.github/scripts')
from sync_templates import update_build_yml
with tempfile.TemporaryDirectory() as tmp:
    p = Path(tmp) / 'jammin.build.yml'
    shutil.copy('jammin.build.yml', p)
    # 1) same sdk -> no change
    changed, prev = update_build_yml(p, 'jade', 'services/example-jade', 'jade-0.0.15-pre.1')
    print('same sdk:', changed, prev)
    # 2) bumped sdk -> change
    changed, prev = update_build_yml(p, 'jade', 'services/example-jade', 'jade-9.9.9')
    print('bumped sdk:', changed, prev)
    # 3) new entry -> appended
    changed, prev = update_build_yml(p, 'jamc3', 'services/example-jamc3', 'jamc3-1.1.2')
    print('new entry:', changed, prev)
    print('---')
    print(p.read_text())
"
```

Expected output includes:
- `same sdk: False jade-0.0.15-pre.1`
- `bumped sdk: True jade-0.0.15-pre.1`
- `new entry: True None`
- The printed YAML ends with a `jamc3` entry and shows `jade-9.9.9`.

- [ ] **Step 3: Commit**

```bash
git add .github/scripts/sync_templates.py
git commit -m "feat(sync): add jammin.build.yml entry update/append logic"
```

---

## Task 6: Wire up orchestration + per-source error isolation

**Files:**
- Modify: `.github/scripts/sync_templates.py`

- [ ] **Step 1: Add `sync_source` and update `main`**

Add a new `sync_source` function after `update_build_yml`:

```python
def sync_source(entry: SourceEntry, repo_root: Path) -> SourceResult:
    """Sync a single source repo into this repo. Never raises; errors go into the result."""
    result = SourceResult(name=entry.name, status="failed")
    try:
        with tempfile.TemporaryDirectory() as tmp:
            src_root = Path(tmp) / "src"
            clone_source(entry.repo, src_root)
            sdk = read_source_sdk(src_root)
            dest_dir = repo_root / entry.dest
            dest_existed = dest_dir.is_dir()
            files_changed = mirror_service(src_root / "services" / "example", dest_dir)
            yml_changed, previous_sdk = update_build_yml(
                repo_root / "jammin.build.yml", entry.name, entry.dest, sdk
            )
        result.files_changed = files_changed
        result.sdk_before = previous_sdk
        result.sdk_after = sdk
        if previous_sdk is None and not dest_existed:
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
```

Replace the `# Per-source sync will be added in Task 6.` block in `main` with:

```python
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
```

- [ ] **Step 2: Run a full sync locally against a throwaway copy**

Run:
```bash
cp -r . /tmp/pompeii-sync-test
cd /tmp/pompeii-sync-test
python3 .github/scripts/sync_templates.py --summary-out /tmp/sync-summary.json
cat /tmp/sync-summary.json
git status
```

Expected:
- Stderr shows per-source progress (`syncing ... -> ...` and `updated`/`added`/`unchanged`).
- Summary JSON lists five results. The `jamc3` entry has status `added`. Others are `updated` or `unchanged` depending on drift.
- `git status` in the throwaway copy shows a new `services/example-jamc3/` directory and possibly changes under other services + `jammin.build.yml`.

- [ ] **Step 3: Clean up test copy and return to repo**

Run:
```bash
cd -  # back to original repo
rm -rf /tmp/pompeii-sync-test /tmp/sync-summary.json
```

- [ ] **Step 4: Commit**

```bash
git add .github/scripts/sync_templates.py
git commit -m "feat(sync): add per-source orchestration with failure isolation"
```

---

## Task 7: Add PR body formatter

**Files:**
- Create: `.github/scripts/format_pr_body.py`

- [ ] **Step 1: Create the formatter**

```python
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
```

- [ ] **Step 2: Verify formatter against synthetic inputs**

Run:
```bash
python3 -c "
import json, subprocess, sys
cases = {
    'all three': {'results': [
        {'name':'jade','status':'updated','sdk_before':'jade-0.0.14','sdk_after':'jade-0.0.15-pre.1','files_changed':3,'error':None},
        {'name':'jamc3','status':'added','sdk_before':None,'sdk_after':'jamc3-1.1.2','files_changed':7,'error':None},
        {'name':'ajanta','status':'unchanged','sdk_before':'ajanta-0.1.0','sdk_after':'ajanta-0.1.0','files_changed':0,'error':None},
        {'name':'oops','status':'failed','error':'git failed (exit 128): fatal: repository not found'},
    ]},
    'empty': {'results': [
        {'name':'jade','status':'unchanged','sdk_before':'x','sdk_after':'x','files_changed':0,'error':None},
    ]},
}
import tempfile, pathlib
for label, s in cases.items():
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
        json.dump(s, f); path = f.name
    print(f'--- {label} ---')
    print(subprocess.check_output(['python3','.github/scripts/format_pr_body.py',path]).decode())
"
```

Expected: the first case prints a body with `## Changes`, `## New services`, and `## Failures` sections; the second case prints `_No changes detected in any source._`.

- [ ] **Step 3: Commit**

```bash
git add .github/scripts/format_pr_body.py
git commit -m "feat(sync): add PR body formatter"
```

---

## Task 8: Add the GitHub Actions workflow

**Files:**
- Create: `.github/workflows/sync-templates.yml`

- [ ] **Step 1: Create the workflow file**

```yaml
name: Sync templates from source repos

on:
  schedule:
    - cron: "0 6 * * *"  # daily, 06:00 UTC
  workflow_dispatch:

permissions:
  contents: read

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - name: Mint GitHub App token
        id: app-token
        uses: actions/create-github-app-token@v1
        with:
          app-id: ${{ secrets.APP_ID }}
          private-key: ${{ secrets.APP_PRIVATE_KEY }}

      - name: Checkout this repo
        uses: actions/checkout@v4
        with:
          token: ${{ steps.app-token.outputs.token }}

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: python -m pip install ruamel.yaml

      - name: Run sync
        run: |
          python .github/scripts/sync_templates.py \
            --summary-out /tmp/sync-summary.json

      - name: Render PR body
        id: body
        run: |
          python .github/scripts/format_pr_body.py /tmp/sync-summary.json > /tmp/pr-body.md
          {
            echo 'body<<EOF'
            cat /tmp/pr-body.md
            echo EOF
          } >> "$GITHUB_OUTPUT"
          cat /tmp/pr-body.md >> "$GITHUB_STEP_SUMMARY"

      - name: Create or update PR
        uses: peter-evans/create-pull-request@v6
        with:
          token: ${{ steps.app-token.outputs.token }}
          branch: sync/templates
          base: main
          title: "chore: sync templates from source repos"
          body: ${{ steps.body.outputs.body }}
          commit-message: "chore: sync templates from source repos"
          labels: automated-sync
          delete-branch: true
```

- [ ] **Step 2: Sanity-check YAML syntax**

Run: `python3 -c 'import sys; from ruamel.yaml import YAML; YAML().load(open(".github/workflows/sync-templates.yml"))'`
Expected: no output, exit 0.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/sync-templates.yml
git commit -m "feat(sync): add daily template-sync workflow"
```

---

## Task 9: Document setup steps for secrets

**Files:**
- Modify: `README.md` (append a short section)

- [ ] **Step 1: Append setup note to README**

Append to the end of `README.md`:

```markdown
## Template auto-sync

Service directories under `services/example-*` and their SDK pins in
`jammin.build.yml` are kept in sync with the per-SDK source repos in the
`jammin-create` GitHub organization by the workflow at
`.github/workflows/sync-templates.yml`.

The workflow runs daily and can be triggered manually from the Actions
tab. It opens a PR on the branch `sync/templates` whenever a source repo
has drifted.

To set it up on a fork, configure two repo secrets from a GitHub App
installed on this repo with `contents: write` and `pull-requests: write`:

- `APP_ID` — the App's numeric ID
- `APP_PRIVATE_KEY` — the App's PEM private key

The list of sources is in `.github/sync-config.yml`.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: explain template auto-sync setup"
```

---

## Task 10: First-run manual verification

This task happens after the PR is merged, not before — it's the acceptance test.

**Files:** none modified by this task.

- [ ] **Step 1: Open a PR with all prior commits**

Push the branch and open a PR against `main`. Review the diff. Merge it.

- [ ] **Step 2: Ensure GitHub App is installed and secrets are set**

In the repo's Settings > Secrets and variables > Actions, confirm that
`APP_ID` and `APP_PRIVATE_KEY` exist and are non-empty. Confirm the
GitHub App is installed on the repo with `contents: write` and
`pull-requests: write`.

- [ ] **Step 3: Trigger the workflow manually**

Go to the Actions tab > "Sync templates from source repos" > Run
workflow > on `main`. Watch it run to completion.

- [ ] **Step 4: Review the first automated PR**

Expected: a PR titled `chore: sync templates from source repos` on
branch `sync/templates` that:
- Adds `services/example-jamc3/` with files from
  `jammin-create/jammin-create-jamc3:services/example/`.
- Adds a `jamc3` entry to `jammin.build.yml`.
- Optionally updates other services if they've drifted since manual sync.
- Has a body generated by `format_pr_body.py` listing what changed.

- [ ] **Step 5: Merge the PR**

Merge via the GitHub UI. The `sync/templates` branch will be deleted.

- [ ] **Step 6: Verify next scheduled run produces no PR (if nothing drifted)**

Wait for the next daily cron run (or trigger manually again immediately).
Expected: workflow succeeds, `create-pull-request` reports "No changes
to pull request" in its logs, no PR is opened.

---

## Self-Review Notes

Checked against the spec (`docs/superpowers/specs/2026-04-23-auto-sync-templates-design.md`):

- Config file format: matches Task 1.
- Sync logic (clone -> mirror -> SDK extract -> update build.yml): Tasks 3-5, wired in Task 6.
- PR as fixed rolling branch `sync/templates`: Task 8.
- GitHub App auth with `APP_ID` / `APP_PRIVATE_KEY`: Tasks 8-9.
- Daily cron + `workflow_dispatch`: Task 8.
- Error isolation (per-source failures don't block; exit 1 only if all fail): Task 6.
- Summary JSON -> Markdown body: Task 7.
- Inclusion of `jammin-create-jamc3`: Task 1 config includes it; first-run Task 10 verifies it's added.
- First-run manual verification: Task 10.

No unit tests as specified in the design. Each code task ends with a
manual verification step against real public source repos.
