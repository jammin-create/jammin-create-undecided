# Auto-sync `jammin-create-undecided` from sibling source repos

## Problem

`jammin-create-undecided` is an aggregator template that bundles one example
service per SDK so users can explore before picking one. Each service lives
in its own source-of-truth repo in the `jammin-create` GitHub organization
(`jammin-create-jade`, `-jambrains`, `-jam-sdk`, `-ajanta`, `-jamc3`, …).

Today these are kept in sync by hand, so the undecided template drifts behind
its sources. We want the template to update itself automatically whenever the
source repos change.

## Scope

**In scope**

- Mirror each source repo's `services/example/` directory into this repo's
  matching `services/example-<name>/` directory.
- Keep each service entry's `sdk:` pin in this repo's top-level
  `jammin.build.yml` in sync with the source repo's pin.
- Surface changes as a PR (not a direct commit). One rolling PR that
  aggregates any diff across all sources.
- Run daily on a schedule and on manual dispatch.
- Include `jammin-create-jamc3` as a new service on first run.
- Keep the source list in a declarative config so adding a future SDK is
  a one-commit change.

**Out of scope**

- Modifying the source repos (no workflows or config added there).
- Auto-merging PRs; review stays manual.
- Tracking release tags — we follow `main` HEAD (see Q4 in conversation).
- Unit tests for the sync script. The PR itself is the visible artifact;
  correctness is verified on the first manual run.
- Updating the top-level `README.md` or adding a README into each service
  (the per-service README is part of the upstream mirror and carries over).

## Source-of-truth relationship

- Per-SDK source repo **is** the source of truth for its service contents.
- The only files in this repo that are *not* derived from a source repo are:
  - Top-level `README.md`
  - Top-level `jammin.build.yml`'s `path:` and `name:` fields (the `sdk:`
    field is derived)

Everything under `services/example-<name>/` is a verbatim mirror of the
corresponding source repo's `services/example/`.

## Source repo structure (confirmed)

All current source repos follow an identical layout:

```
<source-repo>/
├── README.md
├── .gitignore
├── jammin.build.yml          # pins sdk version; single entry with path: services/example, name: example
└── services/
    └── example/              # the actual service files (copied into undecided)
```

The sync reads the single `services[0].sdk` value from the source's
`jammin.build.yml` and mirrors the `services/example/` directory.

## Architecture

Three files in this repo handle everything; source repos are untouched.

### 1. `.github/sync-config.yml`

Declarative list of sources. Adding a new SDK is one PR to this file.

```yaml
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

Field semantics:

- `repo` — `owner/name` of the source repo on GitHub.
- `name` — the value used in this repo's `jammin.build.yml` entry's `name:`
  field. Must be unique across sources.
- `dest` — the path in this repo where the source's `services/example/` is
  mirrored. Also the `path:` field in this repo's `jammin.build.yml`.

### 2. `.github/scripts/sync-templates.py`

A Python script (standard library only — `PyYAML` installed via the workflow)
that performs the sync. Python over bash because parsing and updating YAML
while preserving order and comments is painful in bash.

Responsibilities:

1. Load `.github/sync-config.yml`.
2. For each source entry:
   a. Shallow-clone `https://github.com/<repo>.git` at `main` into a temp dir.
   b. Read the source's `jammin.build.yml`; extract `services[0].sdk`.
   c. `rsync -a --delete` from `<tmp>/services/example/` to
      `<repo-root>/<dest>/`. `--delete` makes the destination a true mirror
      (files removed upstream are removed locally).
   d. Update this repo's top-level `jammin.build.yml`:
      - If an entry with matching `name:` exists → set its `sdk:` field.
      - Else → append a new entry `{ path: <dest>, name: <name>, sdk: <version> }`.
3. Collect a per-source result: `updated` / `unchanged` / `failed (<reason>)`,
   and for `updated` entries, the SDK version delta (`old → new`) if it changed.
4. Write a machine-readable summary (JSON on stdout or a file) for the workflow
   step to consume when building the PR body.

Failure isolation: per-source errors are caught and recorded; the script
continues. It exits non-zero **only** if every configured source failed
(catches total breakage like bad config or auth rot).

### 3. `.github/workflows/sync-templates.yml`

Workflow with two triggers:

```yaml
on:
  schedule:
    - cron: "0 6 * * *"   # daily, 06:00 UTC
  workflow_dispatch:
```

Job steps (high level):

1. `actions/checkout` this repo.
2. `actions/create-github-app-token` — mint an installation token using
   secrets `APP_ID` and `APP_PRIVATE_KEY`. The token is used both for the
   subsequent `checkout`/`push` credentials and for PR creation so the PR
   is attributed to the GitHub App.
3. Install Python + PyYAML.
4. Run `.github/scripts/sync-templates.py`, capturing its summary output.
5. `peter-evans/create-pull-request@v6`:
   - branch: `sync/templates` (fixed — existing open PR is updated, not duplicated)
   - title: `chore: sync templates from source repos`
   - body: generated from the script summary (see below)
   - labels: `automated-sync`
   - token: the GitHub App installation token

If the script produced no diff, `create-pull-request` is a no-op (no PR
opened, no existing PR updated beyond closing if previously merged).

### PR body format

Generated from the script summary. Example:

```
Automated sync from source repos.

## Changes

- `jade`: sdk pin `jade-0.0.14` → `jade-0.0.15-pre.1`, 3 files changed
- `jambrains`: files changed only

## New services

- `jamc3`: added from `jammin-create/jammin-create-jamc3` (sdk `jamc3-1.1.2`)

## Failures

- (none)
```

Sources with no changes are omitted from the body. If the `Failures`
section is empty, it's omitted too. If nothing changed across any source,
no PR is opened at all.

## Auth

- **GitHub App** owned by the user, installed on this repo
  (`jammin-create-undecided`) with `contents: write` and
  `pull-requests: write`.
- Source repos are public, so the clone step uses no credentials — the App
  does not need access to the source repos.
- Secrets stored in this repo:
  - `APP_ID` — numeric App ID.
  - `APP_PRIVATE_KEY` — the App's PEM private key.
- Token minted per-run via `actions/create-github-app-token`. No long-lived
  PAT.

## Error handling

| Situation | Behavior |
|---|---|
| One source clone fails (404, auth, network) | Record failure, continue with other sources. |
| Source repo missing `services/example/` | Record failure for that source, continue. |
| Source repo missing `jammin.build.yml` or no `services[0].sdk` | Record failure, continue. |
| YAML parse error in local `jammin.build.yml` | Fail the whole run — the repo is in a broken state that a sync shouldn't paper over. |
| All sources fail | Script exits non-zero → workflow fails → maintainer gets notified. |
| No diff | Script exits 0; PR step is a no-op. |

Per-source failures are visible in the PR body's "Failures" section, so a
partial success is both useful (it lands the parts that worked) and loud
(the failure is surfaced on the PR).

## Testing approach

- **First run:** manual `workflow_dispatch` after merging the workflow.
  The first PR should add `services/example-jamc3/` and update any SDK
  pins that have drifted. A human reviews and merges.
- **Subsequent runs:** cron takes over. Each morning there may or may not
  be a PR. If something breaks, the workflow run page and the PR body
  show what happened.
- **No unit tests.** The sync script is ~100 lines of straightforward
  file ops and YAML munging. A faulty sync produces a visible wrong PR,
  not silent corruption, and the reviewer catches it.

## Open questions

None remaining. Questions Q1–Q6 from the brainstorming conversation are
resolved:

- Q1: per-SDK repo is source of truth; only top-level README and the
  `path:`/`name:` fields in `jammin.build.yml` are locally owned.
- Q2: scheduled daily + manual `workflow_dispatch`.
- Q3: PR (not direct commit), created by GitHub App.
- Q4: pull `main` HEAD.
- Q5: sync the `sdk:` version pin.
- Q6: include `jamc3`, and keep the source list in a config file so future
  additions are one-commit.
