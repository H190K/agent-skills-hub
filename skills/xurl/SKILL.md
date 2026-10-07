---
name: xurl
description: Use when the task touches X/Twitter through the API — post, reply, quote, delete, search for raw posts, read timelines, like/repost/bookmark, follow/block/mute, DMs, encrypted XChat, media uploads, or any raw v2 endpoint — using the official xurl CLI, kept credential-safe in an agent session.
version: 1.0.0
author: adapted from the xurl project's own agent skill (xdevplatform/xurl, MIT, © 2024 Santiago Medina Rolong)
license: MIT
platforms: [linux, macos]
prerequisites:
  commands: [xurl]
---

# xurl — the X API from an agent session

`xurl` is the official CLI for the X API ([xdevplatform/xurl](https://github.com/xdevplatform/xurl)).
It has **shortcut commands** for common actions and a **raw curl-style mode** for any v2 endpoint;
every command returns JSON to stdout. Two things make it work well from an agent session: the
secret rules below keep credentials out of your context, and the output is already the API's
response — there is no parsing layer between you and the data.

## Secret safety (never break these)

- **Never** read, print, parse, summarize, upload, or send anything under `~/.xurl/` — not to the
  conversation, not into a log. Credentials live there (`~/.xurl/auth.yml` since v1.3.0; the
  directory replaces an older single file and migrates automatically).
- The 7 sensitive flags accept inline secrets and must never appear in a command you run:
  `--bearer-token`, `--consumer-key`, `--consumer-secret`, `--access-token`, `--token-secret`,
  `--client-id`, `--client-secret`.
- **Never** use `-v` / `--verbose` in an agent session — it can print auth headers and tokens into
  the tool output, which you cannot take back.
- **Never** run `xurl token`: it prints a live OAuth2 access token to stdout. That is a credential
  entering your context. (It is fine for the *user's own* scripts.)
- Never run `xurl mcp` directly — it is a configuration bridge for an MCP client and injects the
  bearer token into requests.
- `xurl chat keys restore` and `keys import` prompt without echo. Never pass `--pin` or a key blob
  as inline arguments; if the user must run them, they type the secret themselves.
- Never ask the user to paste credentials or tokens into chat. App registration, credential
  rotation, and the OAuth2 flow are done **by the user, outside the agent session**.
- The only safe credential check is `xurl auth status`.

## Installation

```bash
# macOS
brew install --cask xdevplatform/tap/xurl

# Any platform (npm)
npm install -g @xdevplatform/xurl

# Linux/macOS shell script (installs to ~/.local/bin, no sudo)
curl -fsSL https://raw.githubusercontent.com/xdevplatform/xurl/main/install.sh | bash

# Go
go install github.com/xdevplatform/xurl@latest
```

Verify: `xurl --help` then `xurl auth status`.

## One-time setup — the user runs these, not you

1. Create or open an app at https://developer.x.com/en/portal/dashboard, enable User Authentication
   settings, and set the redirect URI to `http://localhost:8080/callback`.
2. **User, in their own terminal** (the command contains inline secrets, so it must not run through
   an agent): `xurl auth apps add my-app --client-id <ID> --client-secret <SECRET>`
3. **User:** `xurl auth oauth2 --app my-app` — opens a browser for the OAuth2 PKCE flow. Pass a
   username to bind the token when the post-OAuth lookup misbehaves:
   `xurl auth oauth2 --app my-app USERNAME`.
4. On a headless machine (no reachable localhost callback): add `--headless` — xurl prints the
   authorization URL, the user opens it on any device, then pastes the redirect URL back.
5. **User:** `xurl auth default my-app` so every command uses that app.
6. Verify: `xurl auth status` shows the app and tokens; `xurl whoami` returns the profile.

> **The classic trap:** the OAuth flow *succeeds* but the token was saved to the built-in `default`
> app profile, which has no client credentials — every later command fails with auth errors despite
> the browser dance having worked. Fix: re-run `xurl auth oauth2 --app my-app`, then `xurl auth
> default my-app`. If auth keeps failing after a flow that looked successful, this is the first
> thing to suspect.

> **Containerized machines:** credentials land under the HOME of whoever runs the command. If
> `auth status` works interactively but a later tool call reports no apps, the tool's subprocesses
> resolve `~` differently — check where HOME points for that runner and re-register with that HOME.

## Quick reference

| Action | Command |
| --- | --- |
| Post | `xurl post "Hello world!"` |
| Post with media | `xurl post "text" --media-id MEDIA_ID` (repeatable) |
| Reply | `xurl reply POST_ID "Nice point!"` |
| Quote | `xurl quote POST_ID "My take"` |
| Delete | `xurl delete POST_ID` |
| Read a post | `xurl read POST_ID` |
| Search posts | `xurl search "QUERY" -n 10` |
| Who am I | `xurl whoami` |
| Look up a user | `xurl user @handle` |
| List a user's posts | `xurl posts @handle -n 10` |
| Home timeline | `xurl timeline -n 20` |
| Mentions | `xurl mentions -n 10` |
| Like / unlike | `xurl like POST_ID` / `xurl unlike POST_ID` |
| Repost / undo | `xurl repost POST_ID` / `xurl unrepost POST_ID` |
| Bookmark / remove | `xurl bookmark POST_ID` / `xurl unbookmark POST_ID` |
| List bookmarks / likes | `xurl bookmarks -n 10` / `xurl likes -n 10` |
| Follow / unfollow | `xurl follow @handle` / `xurl unfollow @handle` |
| Following / followers | `xurl following -n 20` / `xurl followers -n 20` |
| Another user's graph | `xurl following --of handle -n 20` |
| Block / mute | `xurl block @handle` / `xurl mute @handle` (and un-/un-) |
| Send DM | `xurl dm @handle "message"` |
| List DMs | `xurl dms -n 10` |
| Upload media | `xurl media upload path/to/file.jpg` |
| Media status | `xurl media status MEDIA_ID` |
| XChat inbox | `xurl chat conversations` (add `--json` for structured) |
| Read chat history | `xurl chat read @handle -n 50` |
| Send (encrypted) | `xurl chat send @handle "message"` |
| App management | `xurl auth apps list` / `auth apps add` / `apps remove` |
| Set default app (and user) | `xurl auth default APP_NAME [USERNAME]` |
| Per-request app override | `xurl --app NAME /2/users/me` |
| Auth status | `xurl auth status` |

Anywhere `POST_ID` appears, a full post URL also works
(`https://x.com/user/status/1234567890`) — xurl extracts the id. Usernames work with or without
the leading `@`. Conversations are addressed by `@username`, bare user id, or conversation id
(`123-456` for 1:1, `g123` for groups).

## Gotchas measured against the binary (v1.3.4)

- **`-n` ranges differ per command.** `search` min was measured at 10 and max 100; `posts` spans
  5–100; `timeline`/`dms`/`bookmarks`/`likes` are 1–100; `following`/`followers` go up to 1000.
  A value below a command's minimum is an error — read that command's own `--help` line rather
  than assuming one global range.
- **`media upload` waits for processing by default** (`--wait` defaults to true as of v1.3.4);
  the separate `media status` subcommand exists and takes `-w/--wait` to block until done. Don't
  hand-write a poll loop for images.
- **Chat reads and sends are visible writes.** `chat read` and `chat listen` send a read receipt
  automatically; `chat send` sends a typing indicator first and marks read after. Pass
  `--no-mark-read` / `--no-typing` to suppress, or use them deliberately when reading shouldn't
  signal the other side. `chat rotate` and `chat add-members` change group state every participant
  sees — never run without explicit user intent, and let the user answer the interactive prompt
  rather than passing `--yes`.
- **Chat keys come from another client.** xurl never generates or registers encryption keys; the
  account must already have XChat keys (from the X app), brought over via `keys restore`
  (Juicebox PIN recovery) or `keys import`. Keys live in `~/.xurl/keys.yml` (mode 600) — private
  keys, the strictest no-read rule applies. The `chat` command group ships on macOS/Linux amd64
  elsewhere it prints a stub.
- **Every command has its own `--help`** with the real flags. If a flag from an older blog post or
  skill copy fails, check the installed binary's help before doubting your install.

## Reading and searching

`search` queries the live index as the authenticated account and returns **raw post objects** —
ids, authors, full text — so results feed directly into engagement (reply, like, repost, quote).
Reach for it when the deliverable needs the actual posts; when it only needs a topic summary,
ordinary web search is cheaper.

```bash
xurl search "golang"
xurl search "from:handle" -n 20
xurl read 1234567890
xurl read https://x.com/user/status/1234567890
```

## Raw API mode

For anything the shortcuts don't cover — any v2 endpoint:

```bash
xurl /2/users/me                                   # GET
xurl -X POST /2/tweets -d '{"text":"Hello"}'       # POST with a JSON body
xurl -X DELETE /2/tweets/1234567890                # PUT/PATCH same shape
xurl -H "Content-Type: application/json" /2/...    # custom headers
xurl -s /2/tweets/search/stream                    # force streaming mode
xurl https://api.x.com/2/users/me                  # full URLs also work
```

Streaming endpoints (`/2/tweets/search/stream`, `/2/tweets/sample/stream`,
`/2/tweets/sample10/stream`) are auto-detected; `-s` forces streaming elsewhere.

## Global flags

| Flag | Short | Notes |
| --- | --- | --- |
| `--app` | | Use a specific registered app (overrides `auth default`) |
| `--auth` | | Force auth type: `oauth1`, `oauth2`, or `app` (app-only bearer) |
| `--username` | `-u` | Which OAuth2 account when several exist per app |
| `--trace` | `-t` | Adds the `X-B3-Flags` trace header |
| `--verbose` | `-v` | **Never in an agent session** — leaks headers |

Raw mode additionally takes curl-style `-X`, `-d`, `-H`, and `-F` (multipart file upload).

## Output and errors

Successful output is the X API v2 response pretty-printed as JSON
(`{"data": {...}}`); errors arrive the same way (`{"errors": [{"message": ..., "code": ...}]}`) and
any failure exits non-zero. Parse stdout directly — no extra tooling needed. Practical triage:

| Symptom | Likely cause | First move |
| --- | --- | --- |
| 401 on everything | Expired token, or default app without credentials | `xurl auth status`; re-auth per the setup trap above |
| 403 on one action | Token lacks the scope | Re-run `xurl auth oauth2` for a fresh, broader token |
| `client-forbidden` / `client-not-enrolled` | App's X package/environment | Move the app to a Pay-per-use package and Production in the dashboard (upstream-confirmed fix) |
| 429 | Rate limit | Back off; write endpoints have tighter limits than reads |
| Auth fails only in tool calls | Different HOME/container user | See the containerized-machines note above |
| Other persistent failures | X plan/permission issues are common | Check developer-portal billing and environment before debugging the command |

## Agent workflow

1. Verify prerequisites: `xurl --help` and `xurl auth status`.
2. If auth is missing, stop and direct the user to "One-time setup" — do not register apps, run
   OAuth, or pass secrets yourself.
3. Start with a cheap read (`xurl whoami`, `xurl user @handle`) to confirm reachability.
4. Confirm the target post/user and the user's intent **before any write** (post, reply, like,
   repost, DM, follow, block, delete, anything under `chat`). Group-key writes demand it.
5. Only xurl's own output proves a state change happened. Never report a write as done based on a
   plan, a summary, or another tool's output.
6. Use the JSON directly — it is already structured.

## Attribution

Adapted from the xurl project's own agent skill — `SKILL.md` shipped at the root of
[xdevplatform/xurl](https://github.com/xdevplatform/xurl) (MIT © 2024 Santiago Medina Rolong),
with the tool's README and CHANGELOG consulted. This rewrite is framework-neutral, trims
product-specific setup detail, and every command and flag was verified against the v1.3.4 binary's
`--help` output before shipping; the range differences in the gotchas section were measured there.