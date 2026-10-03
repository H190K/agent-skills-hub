# agent-skills-hub

Drop-in **agent skills** for Claude Code, OpenAI Codex, and OpenCode. One source of truth, one
folder per skill, in the `SKILL.md` format all three agents already read.

- **Pure markdown.** No scripts, no build step, no dependencies. Clone it and read it.
- **18 skills**, each self-contained and framework-neutral
- **MIT licensed**, upstream authors credited per skill
- **Kept current** — reviewed and revised regularly; see [How this stays current](#how-this-stays-current)

## The skills

| Skill | What it does | Version |
| --- | --- | --- |
| [`blogwatcher`](skills/blogwatcher/SKILL.md) | Monitor blogs and RSS/Atom feeds via the `blogwatcher-cli` tool. | `2.2.0` |
| [`code-review-reception`](skills/code-review-reception/SKILL.md) | Evaluate review feedback on technical merit instead of agreeing or complying on reflex. | `1.1.0` |
| [`coding-development`](skills/coding-development/SKILL.md) | Build, debug, review and improve software across common languages and APIs. | `1.8.0` |
| [`finishing-a-development-branch`](skills/finishing-a-development-branch/SKILL.md) | Merge, publish, keep or discard finished work, and clean up the workspace. | `1.0.0` |
| [`grounded-citations`](skills/grounded-citations/SKILL.md) | Cite what you fetched — an id ledger kept at retrieval time, a generated Sources block, and a verify step for the draft. | `1.0.0` |
| [`humanizer`](skills/humanizer/SKILL.md) | Strip AI writing tells from prose without changing what it says. | `1.0.0` |
| [`node-debugging`](skills/node-debugging/SKILL.md) | Debug Node.js in one-shot probe mode or the interactive REPL — including attaching to an already-running process. | `1.0.0` |
| [`plan`](skills/plan/SKILL.md) | Write a markdown plan to `.plans/`; no execution. | `2.4.0` |
| [`project-planning-documentation`](skills/project-planning-documentation/SKILL.md) | Plan and document software projects — proposals, README, architecture, API docs. | `1.2.0` |
| [`prompt-engineering`](skills/prompt-engineering/SKILL.md) | Write prompts other agents can execute without questions — structure, acceptance tests, safety rules. | `1.0.0` |
| [`python-debugging`](skills/python-debugging/SKILL.md) | Debug Python with pdb and debugpy — breakpoints, post-mortem, attaching to a live process. | `1.1.0` |
| [`research`](skills/research/SKILL.md) | Research tools, services, APIs and pricing with parallel sourcing. | `1.3.0` |
| [`sketch`](skills/sketch/SKILL.md) | Throwaway HTML mockups — build 2–3 design variants and compare them. | `1.0.0` |
| [`sqlite-recovery`](skills/sqlite-recovery/SKILL.md) | Salvage readable data from a corrupted SQLite database and rebuild it with working FTS5 indexes. | `1.0.0` |
| [`systematic-debugging`](skills/systematic-debugging/SKILL.md) | Find the root cause before fixing a bug, test failure or crash. | `1.3.0` |
| [`test-driven-development`](skills/test-driven-development/SKILL.md) | Write the failing test first; RED–GREEN–REFACTOR and the tests that can never fail. | `1.0.0` |
| [`using-git-worktrees`](skills/using-git-worktrees/SKILL.md) | Isolate feature work in its own workspace and verify a clean baseline first. | `1.0.0` |
| [`verification-before-completion`](skills/verification-before-completion/SKILL.md) | Check what counts as evidence before reporting work as done. | `1.1.0` |

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
`description`; the body is instructions the agent reads when the skill becomes relevant.

```markdown
---
name: my-skill
description: What it does, in one line, starting with when to use it.
---

# My Skill

Instructions go here.
```

Keep the `description` tight. It is the only part of a skill that sits in the agent's context before
the skill is ever used, so it is the entire routing signal — write it as a trigger, not a summary.
Everything else is read only once the agent has decided the skill is relevant, which is what makes a
skill cheap to keep installed.

## How this stays current

A maintainer reviews these skills and revises them as the tools they cover change.

Because everything here is markdown, reviewing a change is reading a diff. Nothing executes, so a
bad change cannot break anything at install time — at worst it is instructions you delete. One
logical change per commit, so `git log` stays readable and anything wrong is one `git revert` away.

## Adding your own

1. Create `skills/<kebab-case-name>/SKILL.md`
2. Add the front matter (`name`, `description`), then the instructions
3. Commit and push, or open a pull request if you would rather have the change reviewed first

Keep one skill to one job. If it needs three paragraphs of setup before the actual procedure, it is
probably two skills.

## What does not belong here

- **Executable code.** This repository is markdown only. If a procedure needs a script, the skill
  should describe what to run and where to get it — not ship the script itself.
- **Anything that must stay private.** No credentials, tokens, personal paths, or internal
  infrastructure details. Every file here is public and gets loaded into other people's agents.
- **Framework-specific instructions.** A skill here must be useful to someone running Claude Code,
  Codex, OpenCode, or their own agent. Something that only works inside one particular product
  belongs in that product's own documentation.

## Credits

Maintained by **Hasan Albehadili ([@H190K](https://github.com/H190K))**. Some skills originate from
other authors — the full mapping is in [`NOTICE.md`](NOTICE.md), and each file records its own
`author:` field. Everything here is MIT; the license text is in [`LICENSE`](LICENSE).
