---
name: git-cliff
version: 1.0.0
author: H190K
license: MIT
description: "Use when cutting a release, generating or refreshing CHANGELOG.md, or summarizing git history for review - git-cliff workflows: version bumping from tags, unreleased and range flags, JSON context for scripts, the silent drop of non-conventional commits, config groups and templates, fail-open config fallbacks and real exit codes; measured live on 2.14.2."
---

# git-cliff — changelog generator from conventional commits

`git-cliff` ([orhun/git-cliff](https://github.com/orhun/git-cliff), licence `MIT OR Apache-2.0` — the release tarball ships both LICENSE files; crates.io lists `MIT OR Apache-2.0` while the GitHub repo API labels the project Apache-2.0 only) turns git history into a grouped, versioned CHANGELOG.md. Everything here is original text measured live on **2.14.2** (the official `x86_64-unknown-linux-gnu` release tarball, sha256-verified against the per-asset digest on the GitHub release API) and cross-checked on the conda-forge 2.14.2 build — `--help` byte-identical and identical rendering on the same fixture (that build links a dynamic conda-forge libgit2 1.9.7 plus libssh2 and libz). 2.14.2 was the newest release at the time of writing; no older release line was measured, so treat every exact string as version-specific.

## Install and verify

The recommended install is the official release tarball, checked against the per-asset digest returned by the releases API (the digest is the same string the release API reports for the asset):

```bash
cd "$(mktemp -d)" &&
curl -f -sL -o gc.tar.gz "https://github.com/orhun/git-cliff/releases/download/v2.14.2/git-cliff-2.14.2-x86_64-unknown-linux-gnu.tar.gz" &&
echo "24f397c733add5390fdceee3a2088588ab0d5f944ce00d34cb7029b888cf2db4  gc.tar.gz" | sha256sum -c &&
tar xzf gc.tar.gz &&
mkdir -p "$HOME/.local/bin" &&
install -m 755 git-cliff-2.14.2/git-cliff "$HOME/.local/bin/git-cliff" &&
git-cliff --version
```

Alternative package source: `conda install -c conda-forge git-cliff` (pulls the shared libs above). The release tarball also carries shell completions, a man page, and two helper binaries (`git-cliff-completions`, `git-cliff-mangen`). `cargo install git-cliff` works if a Rust toolchain exists.

## First run

Run `git-cliff` inside any git repository with no preparation: the default render starts with `## [unreleased]` followed by one section per tag, newest first — `## [0.1.0] - 2026-11-02`. Without a config file every run emits `WARN ... "cliff.toml" is not found, using the default configuration` on **stderr** and still exits 0. Default rows are description-only — no hashes, no commit bodies — capitalized, with `*(scope)*` prefixes and a `[**breaking**]` marker. Measured default groups here: 🚀 Features, 🐛 Bug Fixes, 📚 Documentation, ⚙️ Miscellaneous Tasks (more exist in the built-in parsers; `git-cliff -i` writes a fully commented template). The `v` prefix disappears from section titles because the default *template* trims it (`trim_start_matches(pat="v")`), not because of a config key.

## Cut a release

```bash
# preview, then cut: tag at the printed version, regenerate the changelog wholesale
git-cliff --bumped-version
V="$(git-cliff --bumped-version)"
git-cliff --bump -o CHANGELOG.md
git tag "$V"
```

Bump math, measured: a `feat!:` (breaking) commit after a `v0.1.0` tag gives `v1.0.0` — breaking means major; a repository with no tags at all yields `0.1.0` for the first release. Note the prefix of `--bumped-version` output mirrors the previous tag (`v1.0.0` after a `v`-tagged repo, bare `0.1.0` on a tagless one), so script conservatively when your tags and `git tag` arguments must agree.

```bash
# overwrite the whole CHANGELOG.md from history — the safe repeatable pattern
git-cliff -o CHANGELOG.md
```

## Machine-readable context

```bash
# -x prints a JSON ARRAY of release contexts (newest first), not a single object
git-cliff -x > clif.json
python3 - <<'PY'
import json
releases = json.load(open("clif.json"))
rel = releases[-1]  # oldest release (the unreleased section sits first, version null)
print(rel.get("version"), rel.get("statistics"))
for c in rel.get("commits", []):
    print(c["id"][:7], c["group"].split("-->")[-1].strip(), c["message"])
PY
```

Each release object carries `version`, `message`, `commits`, `commit_id`, `commit_range`, `previous`, `repository` (an absolute local path — sanitize before publishing), `statistics` (`commit_count`, `conventional_commit_count`, `commits_timespan`, `days_passed_since_last_release`), `bump_type` (set under `--bump`, e.g. `major`), and remote sections (`github`, `gitlab`, `gitea`, `bitbucket`, `azure_devops`). Each commit carries `id`, `message`, `raw_message`, `body`, `footers` (including the parsed `BREAKING CHANGE` footer with a breaking flag), `breaking`, `breaking_description`, `scope`, `conventional`, `merge_commit`, author/committer with timestamps, and per-commit file `statistics`. The `group` string embeds an invisible ordering prefix — `<!-- 0 -->🚀 Features` — strip it (`split("-->")[-1]`) before display.

## Attach commit hashes with a body override

The default rows have no hash. `GIT_CLIFF_TEMPLATE` (or `-b`) overrides the body template, which renders **per release** — the in-scope variables are `version`, `timestamp`, and `commits` (there is no `releases` loop at this level; a template referencing `releases` renders empty). Measured override:

```bash
GIT_CLIFF_TEMPLATE='{% for group, commits in commits | group_by(attribute="group") %}### {{ group | striptags | trim | upper_first }}
{% for commit in commits %}- {{commit.id | truncate(length=7)}} {{commit.message | upper_first}}
{% endfor %}{% endfor %}' git-cliff
```

This renders rows like `- f0fb39a… Rework the CLI entrypoint`. Tera notes measured: `truncate(length=7)` appends an ellipsis by design; the filter's `end` argument must be a string — `truncate(start=0, end=7)` fails with `Filter call 'truncate' failed ... expected a String` and rc 1, and a template error otherwise leaves stdout empty with the error on stderr only.

## Flag specifics — measured

- **Section scope.** Plain run = everything; `-u`/`--unreleased` = only the untagged tail; `--latest` = only the latest tag's section (inclusive); `--current` on a HEAD without a pointing tag behaves like `--latest`. `--bump` re-titles the unreleased section with the computed next version and today's date.
- **Ranges.** `v0.1.0..HEAD` renders just the unreleased tail; explicit `sha..sha` ranges work. A malformed range fails closed: `Error: SetCommitRangeError("main^2..HEAD", ...)` at rc 1.
- **Tag filters.** `--skip-tags` removes a tag's section and its commits entirely; `--ignore-tags` keeps the commits but folds them into the unreleased section — choose the semantics you mean. `--tag-pattern` narrows matching, `--limit-tags` caps the count, `--tag <X>` names the unreleased section.
- **Commit filters.** `--skip-commit <sha>` drops one commit; `--with-commit 'feat: manual row'` injects an extra entry through the real parser (capitalized, no hash); `--include-path`/`--exclude-path` filter by files touched (path-filtered commits are excluded before parsing, so they do not count as parse-skipped).
- **Ordering.** Sections render newest→oldest; commits inside a group oldest→newest. `--sort newest` reverses within groups; `sort_commits = "newest"` in config does the same; `--topo-order` orders by graph instead of date.
- **Files.** `-o` writes (overwrites) a file; `-p` prepends into an existing file (see the marker gotcha below); `--strip header|footer|all` removes template header/footer regions; `--no-exec` disables command execution from templates (the default config runs none); `--offline` disables all remote metadata access (local rendering unaffected, verified rc 0); remote metadata for GitHub/GitLab/Gitea/Bitbucket/Azure DevOps rides dedicated flag pairs with their own env tokens.
- **Location.** `-w/--workdir` and `-r/--repository` operate on a repo from outside it; env equivalents `GIT_CLIFF_WORKDIR`, `GIT_CLIFF_REPOSITORY`, `GIT_CLIFF_CONFIG`, `GIT_CLIFF_TEMPLATE`, `GIT_CLIFF_OUTPUT`, `GIT_CLIFF_TAG` and more are listed in `--help`.

## Configuration

`git-cliff -i` writes `cliff.toml` into the current directory (the `-w` flag does not redirect it) — a fully commented, documented template covering the body pipeline (`commit_groups`, `striptags`, `upper_first`, `trim_start_matches`). Named templates install via `-i keepachangelog` (still writes `cliff.toml`); `--list-templates` lists the 13 built-ins: `keepachangelog`, `minimal`, `detailed`, `github`, `github-keepachangelog`, `gitlab`, `gitlab-keepachangelog`, `azure-devops-keepachangelog`, `scoped`, `scopesorted`, `statistics`, `cocogitto`, `unconventional`. Over an existing `cliff.toml` the same INFO line prints and rc is 0, but the old file is left untouched — `-i` never overwrites.

Overrides merge at field level, measured: a three-line config containing only `[changelog]` with `header = "# Minimal top-title"` (or `footer = """..."""`) still renders the complete default groups and parsers — absent keys fall back to the built-in defaults, so minimal configs are safe. Header/footer render exactly as set (top title first line, footer last lines). Known sharp edges: `sort_commits = "newest"` is the measured in; a wrong-typed value (`sort_commits = 5`) panics (`Incorrect config value ... invalid variant`) and kills the process at rc 101, while a syntactically broken TOML exits rc 1 with a parse position. Config discovery: `cliff.toml`, `.cliff.toml`, `.config/cliff.toml`, then the user config directory, then the built-in default.

## Gotchas — measured on 2.14.2

- **Non-conventional and merge commits vanish silently.** `random commit message` and `Merge branch 'feat-x'` both dropped from the changelog while rc stayed 0 — the only trace is a stderr warning `N commit(s) were skipped due to parse error(s)`. `-vv` names each: `Commit did not match conventional format: 'Missing type in the commit summary, expected 'type: description''` plus the summary. If your history includes merges or legacy subjects, read stderr or expect holes.
- **Fail-open config fetch.** `-c nope.toml` (missing) and `-c https://host/nope.toml --http-timeout 2` (unreachable) both WARN and fall back to the built-in default at rc 0 — a typo'd config path renders a *default-looking* changelog with nothing failing.
- **The prepend marker.** `-p` inserts fresh content above the target file; if the file contains `<!-- git-cliff: end of header -->` (the marker in the `-i` template's header), the header region plus marker are removed first. The rendered output does *not* re-emit the marker, so repeated `-p` on a marker-less file appends duplicate sections — for pipelines prefer wholesale `-o` regeneration.
- **Dates come from commits, not tags.** Section dates are the tagged commit's date (`## [0.1.0] - 2026-11-02` for a tag created today pointing at a 2026-11-02 commit); unreleased and bumped sections show the current date.
- **rc 0 with holes.** Exit code semantics: 0 = success, including skipped-commit runs, config fallbacks, and `--no-exec` short-circuits; 1 = hard errors (no repository: `Error: GitError(... could not find repository at ...)`, an initialized-but-empty repo: `Error: GitError(... reference 'refs/heads/main' not found ...)`, TOML parse failure, malformed range); 101 = wrong-typed config value panic.
- **Empty template level trap.** A body template scoped as one release that references `releases` renders empty output with rc 0 (see the context recipe for the correct scope), and `GIT_CLIFF_TEMPLATE` errors surface only on stderr.

## Provenance

Measured live against the official v2.14.2 release tarball (`git-cliff-2.14.2-x86_64-unknown-linux-gnu.tar.gz`, sha256 `24f397c733add5390fdceee3a2088588ab0d5f944ce00d34cb7029b888cf2db4` matching the per-asset API digest) plus the conda-forge 2.14.2 build (`--help` byte-identical, identical rendering after supplying conda-forge's libgit2 1.9.7 and libssh2 1.11.1 shared objects). Licence is dual `MIT OR Apache-2.0` per crates.io and the shipped LICENSE-MIT/LICENSE-APACHE pair; NOTICE credits the holders named in LICENSE-MIT (Orhun Parmaksız and git-cliff contributors). This file contains original text only — no upstream docs or README prose was adapted.
