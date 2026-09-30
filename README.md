# agent-skills-hub

Drop-in **agent skills** for Claude Code, OpenAI Codex, and OpenCode. One source of truth, one
folder per skill, in the `SKILL.md` format all three agents already read.

- **7 skills**, each self-contained with its own scripts, references and templates
- **Zero dependencies to start** — clone and point your agent at it
- **MIT licensed**, upstream authors credited per skill
- **Kept current by a scheduled agent** that hunts for new skills, hardens the existing ones, and
  opens a PR — see [How this stays current](#how-this-stays-current)

## The skills

| Skill | What it does | Version |
| --- | --- | --- |
| [`blogwatcher`](skills/blogwatcher/SKILL.md) | Monitor blogs and RSS/Atom feeds via blogwatcher-cli tool. | `2.0.0` |
| [`docx`](skills/docx/SKILL.md) | Create, read, edit, template, and review Word .docx files. | `1.1.0` |
| [`github`](skills/github/SKILL.md) | GitHub via gh CLI: PRs, issues, reviews, repos, auth. | `2.0.0` |
| [`ocr-and-documents`](skills/ocr-and-documents/SKILL.md) | Extract text from PDFs/scans (pymupdf, marker-pdf). | `2.3.0` |
| [`plan`](skills/plan/SKILL.md) | Write a markdown plan to .hermes/plans/; no execution. | `2.0.0` |
| [`rss-feeds`](skills/rss-feeds/SKILL.md) | Read RSS, Atom, JSON feeds; discover feeds behind a page. | `1.0.0` |
| [`self-improving-cron-scout`](skills/self-improving-cron-scout/SKILL.md) | Recurring cron scouts that improve their own prompt. | `1.0.0` |

## Install

One folder per skill. Copy the ones you want into the place your agent already scans — no config
edits, no build step.

### Claude Code

```bash
git clone https://github.com/H190K/agent-skills-hub.git ~/.claude/agent-skills-hub
cp -r ~/.claude/agent-skills-hub/skills/* ~/.claude/skills/
```

Reads `~/.claude/skills/<name>/SKILL.md`.

### OpenAI Codex

```bash
git clone https://github.com/H190K/agent-skills-hub.git ~/.codex/agent-skills-hub
cp -r ~/.codex/agent-skills-hub/skills/* ~/.codex/skills/
```

Reads `~/.codex/skills/<name>/SKILL.md`.

### OpenCode

OpenCode reads the same format. It scans `.claude/skills/**/SKILL.md` and
`.agents/skills/**/SKILL.md` in your home directory, plus `{skill,skills}/**/SKILL.md` inside a
project. So either of these works:

```bash
# globally, via the path OpenCode already reads
mkdir -p ~/.agents/skills
cp -r /path/to/agent-skills-hub/skills/* ~/.agents/skills/

# or per project
mkdir -p .opencode/skills
cp -r /path/to/agent-skills-hub/skills/* .opencode/skills/
```

You can also list extra directories in `opencode.json` without copying anything:

```jsonc
{
  "skills": {
    "paths": ["~/agent-skills-hub/skills"]
  }
}
```

## What is a skill?

A folder with a `SKILL.md` inside. The file opens with YAML front matter carrying a `name` and a
`description`; the body is instructions the agent reads when the skill becomes relevant. Anything
else in the folder — scripts, references, templates, assets — is loaded on demand, which is what
makes a skill cheap to keep installed: only the name and description sit in the agent's context
until it actually needs the rest.

```markdown
---
name: my-skill
description: What it does, in one line, starting with when to use it.
---

# My Skill

Instructions go here. Reference relative files like `scripts/run.py`.
```

The `description` matters more than it looks — it is the only part the agent sees up front, so it
is the entire routing signal. Write it as a trigger, not a summary.

## How this stays current

A scheduled agent runs daily and does three things:

1. **Searches** for new skills, prompts and techniques worth packaging
2. **Reviews what is already here** — are the instructions still right, is anything missing
3. **Opens a pull request** with new skills or improvements, never a direct push to `main`

So the library grows on its own, and every change is reviewable.

## Adding your own

1. Create `skills/<kebab-case-name>/SKILL.md`
2. Add the front matter (`name`, `description`), then the instructions
3. Run `./scripts/validate.sh` — it checks the front matter, the description length, and that
   every file you reference actually exists
4. Open a PR

Keep one skill to one job. If it needs three paragraphs of setup before the actual procedure, it
is probably two skills.

## Credits

The skills collected here come from the Hermes Agent skill library. Original authors are recorded
in each file's `author:` field and in [`NOTICE.md`](NOTICE.md). Everything is MIT; the license text
is reproduced in [`LICENSE`](LICENSE).
