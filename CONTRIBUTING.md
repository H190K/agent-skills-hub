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

3. Put supporting material in `scripts/`, `references/`, `templates/` or `assets/` inside the skill
   folder, and reference it with a relative path in backticks (`` `scripts/run.py` ``). The validator
   checks that every such reference resolves.
4. Run `./scripts/validate.sh` and make sure it passes.
5. Open a pull request. `main` is not pushed to directly.

## Rules

- **One skill, one job.** If the procedure needs a page of setup before the actual task, split it.
- **Keep the description under 500 characters.** It is injected into context on every turn of every
  session where the skill is installed, so length here is a real cost.
- **No secrets, no personal paths.** Nothing in a skill may reference a credential, an API key, or a
  path specific to one machine.
- **Instructions must be executable as written.** If a skill says to run a command, that command has
  to work on a clean machine, or the skill must say what has to be installed first.

## What is not accepted

- Skills that wrap a single command with no judgment or procedure around it.
- Skills that duplicate an existing one — extend the existing skill instead.
- Anything without a resolvable license.

## Automated changes

A scheduled agent opens pull requests here daily with new skills and improvements to existing ones.
Those PRs follow the same rules as human contributions and are reviewed before merge; treat them as
suggestions, not as authoritative. If an automated PR is wrong, close it — the job records the
outcome and will not re-open the same change blindly.
