# Contributing

## Adding a skill

1. Create `skills/<kebab-case-name>/SKILL.md`.
2. Open with YAML front matter. `name` is required and must equal the directory name;
   `description` is required and is the only part an agent sees before deciding to load the skill,
   so write it as a trigger, not a summary.

   ```markdown
   ---
   name: my-skill
   description: Use when <the situation that should trigger this>. <One line on what it does.>
   version: 1.0.0
   author: your-name
   license: MIT
   ---
   ```

3. Write the body as instructions an agent can follow directly. Reference other documentation by name
   or URL. Do not add files to this repository beyond `SKILL.md`, `README.md`, `CONTRIBUTING.md`,
   `NOTICE.md` and `LICENSE`.
4. Commit and push, or open a pull request if you would rather have the change reviewed first.

## Rules

- **Markdown only.** No scripts, binaries, configuration files, or CI. A skill that needs a tool
  should tell the agent how to obtain and run that tool — not vendor it here.
- **One skill, one job.** If the procedure needs a page of setup before the actual task, split it.
- **Keep the description under 500 characters.** It is injected into context on every turn of every
  session where the skill is installed, so length here is a real cost.
- **Nothing private, nothing that looks like a secret.** No tokens, API keys, credentials, personal
  file paths, hostnames, or account identifiers. Every file here is public and gets loaded into other
  people's agents — treat anything committed as disclosed.
- **Stay framework-neutral.** The skill must be usable by someone on Claude Code, Codex, OpenCode, or
  a homegrown agent. Naming one product's internal files, storage locations or configuration keys as
  though they were universal is the most common way a skill becomes useless to everyone else. Where a
  product-specific detail is genuinely necessary, say which product it belongs to.
- **Instructions must be executable as written.** If a skill says to run a command, that command has
  to work on a clean machine, or the skill must say what has to be installed first.

## What is not accepted

- Skills that wrap a single command with no judgment or procedure around it.
- Skills that duplicate an existing one — extend the existing skill instead.
- Skills containing code, or pointing at code whose license cannot be resolved.
- Anything whose original author cannot be identified.

## Reporting a bad skill

Open an issue with the skill name and what went wrong. Skills are expected to work as written on a
clean machine; if one does not, that is a bug in the skill.
