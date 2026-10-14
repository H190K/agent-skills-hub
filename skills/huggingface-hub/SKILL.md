---
name: huggingface-hub
description: Use when a task needs the Hugging Face Hub from the shell — download or upload model/dataset/space artifacts with the `hf` CLI, read model and dataset metadata, list parquet URLs or SQL-query dataset files, manage the local HF cache and tokens, or create repos and pull requests. Covers the auth fail-closed matrix, cache layout, dry-run plans, and upload resume behavior.
version: 1.0.0
author: H190K
license: MIT
platforms: [linux, macos, windows]
---

# Hugging Face Hub CLI (`hf`)

`hf` is the command-line interface that ships with the `huggingface_hub` Python package. It
manages Hub repositories, models, datasets, Spaces, and the local cache from a terminal. It
replaces the retired `huggingface-cli`.

Flags and behaviors below were verified against `huggingface_hub` **2.2.0** (2026-10-14).
The Hub CLI moves fast — between major versions, re-check `hf <command> --help` before
trusting a flag.

## Install and check

```bash
pip install -U huggingface_hub   # provides the `hf` entry point; no extras needed
hf version                       # → version=2.2.0
```

- Alternative install (isolated from system Python): `curl -LsSf https://hf.co/cli/install.sh | bash`.
- Upgrade in place: `hf update`.
- `hf datasets sql` additionally needs DuckDB: `pip install duckdb` (measured error: bare
  installs lack it).

## Who can do what without a token

Fail-closed matrix, all measured:

- **Works anonymously** for public artifacts: `hf download` of public files, `hf models|datasets|papers` info/list/card,
  `hf datasets parquet`, `hf datasets sql` (with duckdb installed).
  Unauthenticated requests print a rate-limit warning:
  `Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.`
- **Everything that mutates requires a token**: `upload`, `cp` into a repo, `repos
  create|move|delete`, `discussions`, `jobs`, `endpoints`, `buckets`. Without a token these
  fail with `Error: Client error '401 Unauthorized'`.
- **Gated models** (e.g. `meta-llama/*`) deny even downloads until you accept the terms on
  the Hub page while logged in: `Error: Access denied. Model '…' requires approval.`

Auth workflow:

```bash
hf auth login        # browser flow, or: hf auth login --token <token> (from huggingface.co/settings/tokens)
hf auth whoami       # identity check; exit 1 with 'Not logged in. Run `hf auth login` first.' when anonymous
hf auth token        # print the active token to stdout
hf auth list         # list stored tokens (multiple named tokens supported)
hf auth switch / logout
```

Prefer `hf auth login` or an exported `HF_TOKEN`; avoid `--token <literal>` where the command
line may be logged by other tooling.

## Downloading

```bash
hf download REPO_ID config.json                  # one file → prints path=<absolute path>
hf download REPO_ID                              # whole repo at the revision
hf download REPO_ID --include 'voices/*.pt'      # glob filters (pattern applies repo-wide)
hf download REPO_ID --exclude '*.onnx' --exclude '*.h5'
hf download REPO_ID --revision 7c2d8f9           # branch, tag, or commit SHA
hf download REPO_ID --repo-type dataset          # model | dataset | space | kernel
```

Measured behaviors that matter:

- A single-file download prints one `path=<absolute path>` line — parse that for the file's
  location; a multi-file download prints the snapshot directory.
- `--dry-run` prints a plan without touching the network:
  `[dry-run] Will download 9 files (out of 10) totalling 28.2M.` plus a file→size table.
  Files already in cache are listed with size `-`.
- Downloads are cache-first: re-running a satisfied download is a no-op. `--force-download`
  re-fetches anyway; `HF_HUB_OFFLINE=1` forbids network access (cache must cover the request).
- `--local-dir DIR` places **real copies** (not symlinks) under `DIR` — but it also creates a
  hidden `DIR/.cache/huggingface/download/` with `*.metadata` and `*.lock` bookkeeping.
  Exclude that directory when packaging or committing a local-dir.

Error shapes, verbatim:

- `Error: File not found in model '<repo>'.` — filename typo or wrong revision; the message
  includes the exact resolve URL.
- The gated-model denial above — it does not mean the file is missing.

## Cache layout (default under `HF_HUB_CACHE`)

```
$HF_HOME/hub/models--<org>--<name>/
  blobs/<sha>                          # actual file content
  snapshots/<commit-sha>/<path>        # symlinks into blobs/
  refs/main                            # revision this cache entry resolves to
  trees/<sha>.json                     # v2 manifest for the revision
```

- Snapshot files are **symlinks**. Copying a snapshot tree out must dereference them
  (`cp -L`, `tar -h`) or every copy is dangling. For portable copies use `--local-dir`
  instead.
- `--cache-dir` relocates the download; `HF_HOME` relocates everything. `hf env` prints the
  resolved `HF_HUB_CACHE`, token and stored-token paths — run it to see where things live.
- Cache hygiene:

```bash
hf cache ls                       # id / size / last_accessed / refs per cached repo
hf cache prune                    # drop detached revisions and incomplete downloads
hf cache rm model/<org>/<name>    # remove one cached repo (files too: hf cache rm -h)
hf cache verify <repo>            # checksum-check local files; partial caches warn
```

- `hf cache verify` on a partially downloaded repo reports
  `Warning: N remote file(s) are missing locally.` — that means incomplete, not corrupt.
  `--fail-on-missing-files` turns the warning into a failure.

## Reading the Hub without downloading

Piped output is **JSON by default** (`--format auto` picks agent/json when stdout is not a
TTY, human tables when it is). Scripts should not scrape the human format.

```bash
hf models info openai-community/gpt2 | jq .safetensors.total
hf models ls --sort downloads --limit 10 --format quiet   # one repo id per line
hf models card openai-community/gpt2                       # the model README
hf datasets info HuggingFaceFW/fineweb
hf datasets card HuggingFaceFW/fineweb
hf datasets leaderboard SWE-bench/SWE-bench_Verified
hf datasets parquet cfahlgren1/hub-stats                   # subset/split/url/size table
hf papers ls                                               # daily papers (id/title/upvotes/…)
hf papers read 2601.15621                                  # full paper as markdown
hf papers search "vision language"
```

- `hf datasets parquet` outputs resolve URLs with byte sizes — budget before fetching;
  measured listings were in the hundreds of MB per file.
- SQL over those parquet URLs, anonymous on public datasets (needs `pip install duckdb`):

```bash
hf datasets sql "SELECT COUNT(*) AS c FROM read_parquet('<url from hf datasets parquet>')"
```

- Shared formatting flags (`--format json|human|agent|quiet`, `-q`, `--no-truncate`) work on
  the listing/info commands.

## Uploading and committing (token required)

```bash
hf upload REPO_ID . .                                  # upload the current folder to the repo root
hf upload REPO_ID model.safetensors weights/model.safetensors
```

- **Folder uploads split into several commits and are resumable by re-running the same
  command** when interrupted. There is no separate large-folder command on `hf` — older
  write-ups mentioning `hf upload-large-folder` describe a pre-2.x CLI.
- Per-commit filtering with `--include/--exclude 'PAT'` globs; `--delete 'PAT'` removes
  matching paths in the same commit. `--commit-message` / `--commit-description` set the
  commit text; `--create-pr` submits as a pull request instead of pushing to the branch.
- `--private` applies only when the command creates the repo (existing repos keep their
  visibility).
- `hf upload --every N` schedules a background job that commits every N minutes.
- `hf cp` is the point-to-point transfer form with `hf://` URIs — upload, download, and
  remote-to-remote, including stdin/stdout (`hf cp hf://user/m/config.json -` writes the
  file body to stdout). Measured restrictions: local↔local and bucket→repo copies are not
  supported; remote→remote needs both sides in the same storage region; directory-scale
  transfer belongs to `upload`/`download` (repos) or `buckets sync`.

## Repo management (token required)

```bash
hf repos create my-model --type dataset        # types: model | dataset | space | kernel
hf repos create demo --type space --space-sdk gradio
hf repos duplicate openai/gdpval --type dataset my-copy
hf repos move old-ns/my-model new-ns/my-model  # namespace transfer
hf repos settings my-model --private
hf repos branch / tag / delete-files           # reference and file management (see -h)
hf repos ls                                     # your repos with storage info
```

Higher-level surfaces, one command away (`<cmd> --help` for depth):

- `hf jobs` — run tasks on HF infrastructure (`run`, `uv` for Python scripts with inline
  dependencies, `ssh`, `logs`, `wait`, `stats`, `scheduled`).
- `hf endpoints` — inference endpoints (`deploy`, `pause`, `resume`, `scale-to-zero`,
  `hardware`).
- `hf buckets` — S3-like object storage (`create/cp/sync`); `sync` has rsync semantics
  including `--dry-run` and `--plan FILE` to save a JSONL plan and review it before
  `--apply`, `--delete` for mirror deletes.
- `hf spaces`, `hf webhooks`, `hf collections`, `hf discussions` (`create/comment/diff/
  merge/close/reopen/…` for issues and PRs), `hf extensions` (community commands; treat as
  third-party executables — install only from sources you trust).

## Environment variables

- `HF_TOKEN` — token for the session. **It takes precedence over stored logins** (measured:
  a stale exported `HF_TOKEN` makes `hf auth whoami` say
  `Invalid user token. The token from HF_TOKEN environment variable is invalid. Note that HF_TOKEN takes precedence over `hf auth login`.`) — unset it when switching accounts.
- `HF_HOME` / `HF_HUB_CACHE` — cache root; `hf env` prints the resolved paths.
- `HF_HUB_OFFLINE=1` — cache-only mode.
- `HF_ENDPOINT` — override the Hub API base (mirrors / self-hosted); honored on every
  request.
- `HF_DEBUG=1` — full tracebacks on CLI errors (the CLI's own hint on failures).

## HF's own agent skill

HF ships an official skill for coding agents: `hf skills add` installs it into the
directory the agent reads skills from, `hf --skills` prints it, `hf skills update` refreshes
it. Use it for routine flag lookup; this skill's value is the judgment layer — auth matrix,
cache mechanics, resume semantics, and the failure shapes above.