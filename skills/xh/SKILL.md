---
name: xh
version: 1.0.0
author: H190K
license: MIT
platforms: [linux, macos, windows]
description: "Use when a script, scheduler, or agent shell needs to make HTTP calls - JSON or form requests, auth, cookies, sessions, redirects, timeouts, or downloads. xh speaks HTTPie syntax from one static Rust binary; measured traps on 0.26.3: a non-TTY stdin silently becomes the request body (pass -I in scripts), every host defaults to http:// not https://, status classes exit 3/4/5, timeout exits 2, redirect exhaustion 6, piped -m prints the body, netrc matches the typed host string."
---

# xh — HTTPie-compatible HTTP requests from one static binary

`xh` ([ducaale/xh](https://github.com/ducaale/xh)) is a fast, single-binary HTTP
client that reimplements HTTPie's ergonomic CLI: positional `[METHOD] URL
[ITEMS…]` arguments, JSON bodies built from `key=value` fragments, automatic
response formatting, curl translation, sessions, and cookies. No configuration
files, no plugins, nothing in Python. Everything below was measured live on the
**xh 0.26.3 release binary** (2026-10-21, statically linked, `-native-tls
+rustls`) and cross-checked on the **conda-forge `xh 0.26.3` build** plus
release binaries 0.25.3 / 0.23.1 / 0.21.0 / 0.17.0 / 0.8.1 — the surface below
is stable since 0.25; version deltas are marked inline. Upstream is MIT
(copyright (c) 2021 Mohamed Daahir, from the source tarball LICENSE); the skill
text here is original.

## The script-safety rules — read first

- **A non-TTY stdin is a request body, even when empty.** In a script, a cron
  job, an agent harness, or any pipeline, stdin is usually a pipe, so a bare
  `xh :8000/echo` (no -I) reads stdin and sends it as the body: the request
  becomes `POST` with `Content-Type: application/json` and `Content-Length: 0`
  even though you typed nothing. Mixing that "stdin body" with any body
  item fails at rc 1: `Request body (from stdin) and request data
  (key=value) cannot be mixed. Pass --ignore-stdin to ignore standard input.`
  (variants: `...from stdin and --raw cannot be mixed...`, and `Cannot build a
  multipart request body from stdin` for --multipart).
- **Therefore: `-I` / `--ignore-stdin` on every scripted xh call that does not
  explicitly mean to pipe a body in.** With `-I` the request reverts to `GET`
  and the default `Accept: */*`. The piped-body feature itself is real and
  good: `echo '{"a":1}' | xh :8000/echo` sends that JSON with
  `Content-Type: application/json`. The trap is only the *empty* pipe and the
 *surprise* POST.
- **The default scheme is `http://` for every host, not just localhost.**
  `xh --curl example.org/get` prints `curl http://example.org/get`. Force TLS
  with `--https`, or by renaming/invoking the binary as `xhs` / `https` /
 `xhttps` (argv0 forces the scheme). HTTPie-compat mode (below) does not
  change the scheme. Pasting a URL whose scheme got lost works only in the
  argument form that starts with `://`: `xh '://example.org/get'` targets
  `http://example.org/get`; the documented `https ://example.org` one-arg
  form (space before `://`) errors out with `Invalid <URL>: invalid
 international domain name` at rc 2.
- Leading-colon shorthand: `:8000` = `localhost:8000`, `:/path` =
  `localhost/path`, and a bare `:8000` target alone = `GET /` — but see the
  stdin rule: from a script that bare call is a `POST /`.

## Requests: method, items, bodies

- Method position: `[METHOD] URL …`. Omitted method defaults to **GET, or POST
  when a body exists** (any `=`/`:=`/`@` item, `--raw`, a piped body, or a form
  file; `==` query items and header items do not create a body). Lowercase
  methods are accepted (`xh post :8000/echo`, `xh delete …`), and arbitrary
  custom tokens pass through (`xh FETCH :8000/echo` prints a `FETCH /echo`
  request). A method after the URL is not supported: `xh :8000/echo post`
  fails with `error: Invalid value for '[REQUEST_ITEM]...': "post"` (rc 2).
- Item separators (one item per argument, quoting whole args):
  - `key=value` — string field in JSON mode (`s=1` → `"1"`; an empty value
    `emptystr=` → `""`); in `--form` mode a urlencoded field.
  - `key:=value` — literal JSON (`n:=2` → `2`, `f:=3.5`, `b:=true`,
    `arr:=[1,2]`, `obj:={"k":"v"}`, `nil:=null`); invalid JSON → item-level
    error, rc 2.
  - `key==value` — URL query parameter, URL-encoded: `q==r1 r2==v2` on
    `/get` request line becomes `/get?q=r1&r2=v2`, method stays GET.
  - `Header: value` — request header. Header names keep their case; the
    request print pads with an extra space (`X-Flag:  yes`) but the wire value
    is exactly what you wrote (server-side echo shows `H: v` for `H: v`, and
    `K: no-space` without a space is fine).
  - `Header:` (empty value) — **unsets** a header: `User-Agent:` removes xh's
    own default `User-Agent` line entirely.
  - `key=@file` — uses the file's contents as the raw/decoded string value;
    `key:=@file` — parses the file contents as JSON. Both work in plain JSON
    mode too (`u=@data.txt` → `"file text here"`, `k:=@data.json` → embedded
    object) even though the help text says files require form mode; that help
    claim is stale for the 0.26 CLI.
- Body-type flags: default JSON; `--raw '{"x":1}'` sends that exact body with
  `Content-Type: application/json`; `-f/--form` makes
  `application/x-www-form-urlencoded` (`a=1` → body `a=1`) but **any file
  item upgrades the request to multipart/form-data** with a generated
  boundary and `filename="data.txt"` preserved; `--multipart` forces multipart
  even with no files. One command happily mixes form fields, query items and
  headers.
- Default request headers on a JSON-body request: `Accept-Encoding: gzip,
  deflate, br, zstd` (`gzip, deflate, br` on xh ≤ 0.23.x), `User-Agent:
  xh/<version>`, `Connection: keep-alive`, and `Accept: application/json,
  */*;q=0.5` — the JSON-flavored Accept appears only when the request has a
  JSON body type; `-I`, form, and multipart requests send plain `Accept:
  */*`.

## Output: the print matrix

What xh prints depends jointly on flags and whether stdout is a terminal (in
source order — this exact ordering is why `-m` misbehaves when piped):

- `-v/--verbose` → whole request + response (+ `--all` semantics); `xh -v` on a
  404 shows the plain request, a blank gap, then the plain response — **no
  `-->` arrow decoration**; request and response headers/body print raw.
- `-vv` → also appends `Elapsed time: 0.001s` and `Remote address:
  127.0.0.1:8009` lines at the end.
- `-q` once → stdout silenced, stderr untouched (a 404 still prints its
  warning and still exits 4); `-q -q` → everything silenced; on xh ≤ 0.21 the
  second `-q` still leaves the status warning on stderr (fixed by 0.23.1).
- `-h` → response headers only (`HTTP/1.1 200 OK` down, then a blank line).
- `-b` → body only. `-o FILE` → writes the body to the file (compact), stdout
  silent. `-o -` is NOT stdout: it creates a file literally named `-` and
  stdout stays empty.
- `-m` → response metadata only — `Elapsed time:` + `Remote address:` lines.
  **But piped output silently overrides `-m` to "body":** the non-terminal
  branch wins, so `xh -m … | cat` prints the response body, not metadata. It
  is honest on a real TTY. (Use piped `-vv` when you need the timing lines in
  a script.)
- `p, --print <STRING>` composes any of the letters `H` (request headers),
  `B` (request body), `h` (response headers), `b` (response body), `m`
  (metadata): `xh -p Hb :8000/get` prints the request followed by the response
  body. Any other letter → clap error `'z' is not a valid value` (rc 2).
- Default: on a terminal, response headers + a pretty JSON body indented 4
  spaces; when stdout is piped (or `-o`), only the body, compact single-line.
  The formatting can be forced through a pipe: `--pretty colors` prints ANSI
  colors into pipes; `--format-options=json.format:true` forces pretty
  (4-space) indentation into pipes; `--format-options=json.indent:2` sets a
  different indent. On a TTY, `--pretty none|format|colors|all` downgrades
  output, and `-s/--style {auto,solarized,monokai,fruity}` picks the theme.
- `--format-options` accepts exactly (colon-separated, comma-compressed):
  `json.indent:<NUM>`, `json.format:<true|false>`, `xml.indent:<NUM>`,
  `xml.format:<true|false>`, `headers.sort:<true|false>` — e.g.
  `--format-options=json.indent:2,headers.sort:false`. There is no key sort
  option. A wrong shape fails with `Format options consist of a key and a
  value, separated by a ":".` (rc 2).
- Responses are decoded transparently: a gzipped JSON body comes back
  decompressed while the printed headers still show `Content-Encoding: gzip`.
  `-d` (download) instead sends `Accept-Encoding: identity` — downloads are
  raw.
- Every option can be negated at the command line with `--no-OPTION`
  (`--no-check-status`, `--no-stream`, …); an unknown `--no-nonexistent` fails
  with a clap tip pointing at a similar real flag.

## Exit codes and status checking

Default behavior (xh mode):

- `0` — success, including 2xx.
- `3` — a 3xx response when `--follow` is off, `4` — any 4xx, `5` — any 5xx:
  `check-status` is ON by default in xh mode. The response is still printed to
  stdout, and stderr shows `xh_0: warning: HTTP 404 Not Found` (note: the
  warning prefix is the invoked argv0 — a binary named `xhs_1` reports
  `xhs_1:`). With `--no-check-status` (or HTTPie-compat mode, below) these
  exit 0.
- `1` — network failure: connection refused (`...tcp connect error...Connection
  refused (os error 111)`), TLS handshake/type errors (`received corrupt
  message of type InvalidContentType`), send failures.
- `2` — the timeout code (`--timeout` exceeded → `error sending request for
  url (...)` / `Caused by: operation timed out`) — the same rc 2 that clap
  returns for usage errors; tell them apart by the message.
- `6` — redirect exhaustion with `--follow --max-redirects N`:
  `error: Too many redirects (--max-redirects=1)`.
- Usage/config errors (missing URL, unknown flags, invalid values) → rc 2.

`--check-status` / `--no-check-status`; `-q`/`-qq` interact as described above.

## Redirects, timeouts, downloads

- Redirects are not followed by default. `--follow` (or `-F`) follows;
  `--all` shows every intermediate response; `-P h` (`--history-print h`)
  limits the intermediaries to headers. `--max-redirects N` bounds it and
  exits 6 when exhausted.
- `d, --download`: on a real terminal the body is saved honoring
  `Content-Disposition` (`Downloading 26 B to "report-data.txt"`, then `Done.
  26 B in 0.0001s (…)` — both lines on stderr). **Piped, the same command
  downloads to `<stdout>`** (`Downloading 23 B to "<stdout>"`) — piping a
  `-d` call silently changes the destination. Naming the file with `-o
  name.bin` beats the Disposition header and avoids the piped-to-stdout flip.
- `c, --continue` resumes an interrupted download but requires BOTH `-d` and
  `-o` (missing ones are listed by clap at rc 2). Resuming over an existing
  (even complete or partial) file succeeds silently.
- `--timeout SEC` accepts floats (`0.5`). There is no default timeout shown in
  help; rely on it for scripts that must not hang.

## Auth: basic, bearer, digest, netrc

- `-a user:pass` → `Authorization: Basic …`; `-A bearer -a TOKEN` (or
  `--auth-type bearer`) → `Authorization: Bearer TOKEN`; `-A digest` performs
  the challenge dance — the first request carries **no** `Authorization`
  header until the server answers 401 with a `WWW-Authenticate: Digest …`.
- `.netrc` is read by default (`--ignore-netrc` opts out; the file path
  override is the `NETRC` environment variable). The lookup matches the
  **host string as typed in the URL**: a `machine 127.0.0.1` entry does not
  fire for `xh localhost:8000/…` (silently — no auth, no warning), and
  vice versa. Explicit `-a` overrides a netrc entry for that request.
- Session files (below) also persist auth — in **plaintext**.

## Sessions

- `--session NAME` (or an explicit `PATH.json`) creates/reuses a session:
  state lands at the OS config dir — `~/.config/xh/sessions/<host[_port]>/<name>.json`
  on Linux (`$XDG_CONFIG_HOME/xh/sessions/…` when overridden), the macOS
  equivalent uses `~/Library/Application Support/xh/…` with legacy
  migration, and the whole base can be redirected with `XH_CONFIG_DIR`
  (then `sessions/<host>_<port>/…` sits directly inside it — no `xh` segment).
  Cookies sent back by the server are stored and replayed on the next call:
  a `Set-Cookie: sid=abc123` from one call appears as `Cookie: sid=abc123`
  on the next.
- The file shape: `{"__meta__": {"about": "xh session file", "xh":
  "0.26.3"}, "auth": {"type": "basic", "raw_auth": "u:p"}, "cookies":
  [...], "headers": []}` — **`raw_auth` stores the credential plaintext**;
  treat session files as secrets. Old HTTPie session files are read and
  migrated transparently.
- `--session-read-only` loads without persisting the exchange, but a
  previously-missing name still materializes a default (empty) session file.

## TLS, HTTP versions, and hidden feature flags

- `verify <no|CA-path>` disables or re-targets verification; CA bundle paths
  can also come from `REQUESTS_CA_BUNDLE` / `CURL_CA_BUNDLE` env vars.
- `cert FILE` + `cert-key FILE` supply a client certificate (the non-rustls
  build warns that certificates do not work there); `ssl <auto|tls1|tls1.1|
  tls1.2|tls1.3>` (written `--ssl tls1.2`) pins the TLS version.
- `http-version <1.0|1.1|2|2-prior-knowledge|3-prior-knowledge>`: `2`
  over a plain-text HTTP/1.1 server warns `Connection is HTTP/1, but request
  requires HTTP/2` and fails rc 1 with `client error (UserUnsupportedVersion)`;
  `2-prior-knowledge` against an HTTP/1.1 server fails rc 1 (`http2 error
  ...connection error`). `3-prior-knowledge` parses but fails rc 1: `This
  binary was built without support for HTTP/3. Enable the http3 feature.`
- Hidden flags present but feature-disabled in the released binary:
  `--unstable-m-sig-id KEY_ID` + `--unstable-m-sig-key @file` (RFC 9421
  message signatures) → `This binary was built without message signature
  support. Enable the http-message-signatures feature.` (rc 1). Feature-gated
  surfaces fail closed with a message naming the cargo feature — do not
  report "not implemented" until you have read that specific error.
- Compression: `-x/--compress` is a count flag. Once, the body is deflated
  only when compression actually shrinks it (small JSON bodies are sent
  plain — the measured negative-ratio skip); `-xx` forces
  `Content-Encoding: deflate` even when it grows the body. Combining with an
  explicit `Content-Encoding` header disables compression with the warning
  `--compress can't be used with a 'Content-Encoding:' header. --compress
  will be disabled.`
- Other transport surface: `--proxy <PROTOCOL:URL>`, `--resolve
  HOST:ADDRESS` (custom DNS), `--interface NAME/IP`, `--unix-socket FILE` (0.24+),
  `-4`/`-6`, `--response-charset`, `--response-mime` (re-color/display a body
  as another type, e.g. `--response-mime text/yaml` on an XML body prints it
  raw), `-S/--stream` streams bodies without buffering, `--debug` (and
  `RUST_LOG`) for stack traces.

## The curl translator

- `xh --curl [args…]` prints the equivalent curl command instead of sending:
  `xh --curl -I example.org/get` → `curl http://example.org/get`;
  with items, headers are lowercased and query items merged into the URL:
  `curl 'http://localhost:8009/get?q=1' -H 't:  tok' -d '{"a":"1"}'`.
  `--curl-long` emits long forms (`--header`, `--data`). The translation
  includes only what you asked for — xh's own default headers
  (Accept-Encoding, Connection, User-Agent), session cookies, and netrc
  auth are not carried over, so the emitted curl is an essential, not
  byte-identical, translation.
- `--curl` silently ignores `--offline`: stderr prints `Warning: Ignored
  --offline`.

## HTTPie compat mode

Set `XH_HTTPIE_COMPAT_MODE` to any value (or invoke the binary as `http` /
`https`) and xh switches to HTTPie-compat behavior — measured effect: the
default `check-status` flips OFF (3xx/4xx/5xx respond rc 0), matching HTTPie's
opt-in status checking. The scheme, item grammar, and output are unchanged.
The `xhs`/`xhttps` argv0 forms force HTTPS *without* compat mode — so a binary
copied to `https` still exits 4/5 on error statuses while a binary copied to
`http` exits 0.

## Install and version notes

- GitHub release assets: `xh-v0.26.3-x86_64-unknown-linux-musl.tar.gz` (+
  aarch64-musl, darwin x86_64/aarch64, windows-msvc.zip) unpacking one `xh`
  binary; no .deb/.rpm for 0.26.x. `cargo install xh` works where a Rust
  toolchain exists. Conda: `conda install -c conda-forge xh` (0.26.3 measured;
  identical surface and feature line). Ubuntu 24.04 has NO xh package (apt
  cannot locate it); the upstream `install.sh` from the repo root installs a
  release binary onto PATH.
- `xh --version` prints two lines on modern builds: `xh 0.26.3` and
  `-native-tls +rustls` (the feature line; absent ≤ 0.8.x).
- Flag surface: stable from 0.25 through 0.26.x; 0.24 added
  `--unix-socket`, `--generate`, and `--compress`; 0.22/0.23 added `--debug`
  and the zstd Accept-Encoding; ≥0.23 uses clap-4 error phrasing vs clap-3
  wording at ≤0.21; HTTPie session migration and `-I` exist since early
  versions. Re-probe hidden/feature-gated flags on any version change.
- `xh help` prints the long documentation including the full item grammar.

## Related

- `jq`, `gron` — reshape/filter the response bodies xh prints when piped.
- `hyperfine` — benchmark the endpoint xh just exercised.
- `miller` — turn repeated API responses into typed tabular records.
- `typos` — check generated docs before shipping them.

## Recipe-check (run after installing: `XH=<path-to-xh> python3 this-block`)

Extract this block to a file and run it to verify the measured claims on your
installed binary — the fixture server is local, no network needed:

```python
#!/usr/bin/env python3
"""xh recipe-check: verifies the skill's measured claims against a local fixture."""
import base64, json, os, subprocess, sys, tempfile, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

XH = os.environ.get("XH", "xh")
failed = []

def check(name, cond, hint=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else " :: " + hint))
    if not cond:
        failed.append(name)

class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json", extra=None):
        raw = body.encode() if isinstance(body, str) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(raw)
    def _echo(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(n) if n else b""
        try:
            parsed = json.loads(raw.decode()) if raw else None
        except Exception:
            parsed = None
        self._send(200, {"method": self.command, "path": self.path,
                         "headers": dict(self.headers), "body_raw": raw.decode("utf-8", "replace"),
                         "body_json": parsed})
    def _route(self):
        p = urlparse(self.path).path
        if p == "/echo":
            self._echo()
        elif p == "/get":
            self._send(200, {"path": p, "args": urlparse(self.path).query})
        elif p == "/cookie":
            self._send(200, {"set": True}, extra={"Set-Cookie": "sid=abc123; Path=/"})
        elif p == "/whoami":
            self._send(200, {"cookie": self.headers.get("Cookie", ""),
                             "auth": self.headers.get("Authorization", "")})
        elif p.startswith("/status/"):
            self._send(int(p.split("/")[-1]), "status " + p, ctype="text/plain")
        elif p.startswith("/redirect/"):
            n = int(p.split("/")[-1])
            nxt = f"/redirect/{n-1}" if n > 0 else "/cookie"
            self._send(302, "hop", ctype="text/plain", extra={"Location": nxt})
        elif p.startswith("/sleep"):
            q = urlparse(self.path).query
            try:
                ms = float(q.split("ms=")[-1].split("&")[0])
            except ValueError:
                ms = 0
            time.sleep(ms / 1000.0)
            self._send(200, {"slept": ms})
        elif p == "/download.txt":
            self._send(200, "fixture body", ctype="text/plain",
                       extra={"Content-Disposition": 'attachment; filename="report-data.txt"'})
        else:
            self._send(404, "no such route", ctype="text/plain")
    do_GET = do_POST = do_PUT = do_DELETE = _route
    def log_message(self, *a):
        pass

srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
P = srv.server_address[1]

def xh(*args, env=None, stdin=None, timeout=10):
    e = dict(os.environ)
    for k in ("XH_CONFIG_DIR", "XH_HTTPIE_COMPAT_MODE", "NETRC", "XDG_CONFIG_HOME"):
        e.pop(k, None)
    if env:
        e.update(env)
    kw = dict(capture_output=True, text=True, timeout=timeout, env=e, input=stdin)
    if stdin is None:
        kw["stdin"] = subprocess.DEVNULL
    r = subprocess.run([XH, *args], **kw)
    return r.returncode, r.stdout, r.stderr

# 1. version shape
rc, o, _ = xh("--version")
check("version", rc == 0 and o.strip().splitlines()[0].startswith("xh "), o.strip())
# 2. piped stdin-body trap: empty pipe -> POST with json content-type
rc, o, _ = xh(f":{P}/echo", stdin="")
try:
    echo = json.loads(o)
    check("stdin-trap", echo["method"] == "POST" and echo["headers"].get("Content-Type") == "application/json", o[:200])
except Exception as ex:
    check("stdin-trap", False, f"{ex} :: {o[:200]}")
# 3. -I reverts to GET
rc, o, _ = xh("-I", f":{P}/echo")
try:
    check("-I-reverts", json.loads(o)["method"] == "GET", o[:200])
except Exception as ex:
    check("-I-reverts", False, str(ex))
# 4. piped body is the feature
rc, o, _ = xh(f":{P}/echo", stdin='{"a":1}')
try:
    check("piped-body", json.loads(o)["body_json"] == {"a": 1}, o[:200])
except Exception as ex:
    check("piped-body", False, str(ex))
# 5. item zoo -> typed JSON body
d = tempfile.mkdtemp()
rc, o, _ = xh("-I", "--offline", f":{P}/echo", "s=1", "n:=2", "b:=true", "arr:=[1,2]", "emptystr=")
got = o.strip().splitlines()[-1]
check("item-zoo", got == '{"s":"1","n":2,"b":true,"arr":[1,2],"emptystr":""}', got)
# 6. query items stay GET and land in the URL
rc, o, _ = xh("-I", "--offline", f":{P}/get", "q==r1")
check("query-items", rc == 0 and o.splitlines()[0].strip().endswith("/get?q=r1 HTTP/1.1"), o.splitlines()[0])
# 7. unset header removes a default
rc, o, _ = xh("-I", "--offline", f":{P}/echo", "User-Agent:")
check("unset-header", rc == 0 and "user-agent:" not in o.lower(), o[:200])
# 8. form: urlencoded without files, multipart with
rc, o, _ = xh("-f", "-I", "--offline", f":{P}/echo", "a=1")
check("form-urlencoded", "application/x-www-form-urlencoded" in o and o.strip().splitlines()[-1] == "a=1", o[:200])
txt = os.path.join(d, "x.txt"); open(txt, "w").write("here")
rc, o, _ = xh("-f", "-I", "--offline", f":{P}/echo", "a=1", f"b@{txt}")
check("form-multipart-upgrade", "multipart/form-data" in o and 'filename="x.txt"' in o, o[:200])
# 9. status classes exit as class digits
rc, o, e = xh(f":{P}/status/404")
check("404-rc4", rc == 4 and "404" in o, f"rc={rc} out={o[:80]} err={e[:80]}")
rc, o, e = xh("--no-check-status", f":{P}/status/404")
check("nocheck-0", rc == 0, f"rc={rc}")
rc, o, e = xh(f":{P}/status/500")
check("500-rc5", rc == 5, f"rc={rc}")
# 10. timeout exits 2 (same digit as usage errors; message decides)
rc, o, e = xh("--timeout", "0.4", f":{P}/sleep?ms=2000")
check("timeout-rc2", rc == 2 and "timed out" in e, f"rc={rc} err={e[:120]}")
# 11. redirects: follow lands; max exceeded exits 6
rc, o, e = xh("--no-check-status", "--follow", f":{P}/redirect/2")
check("follow-lands", rc == 0 and '"set": true' in o, o[:120])
rc, o, e = xh("--no-check-status", "--follow", "--max-redirects", "1", f":{P}/redirect/3")
check("max-redirects-rc6", rc == 6 and "Too many redirects" in e, f"rc={rc} err={e[:120]}")
# 12. forced compression on the wire at -xx
rc, o, _ = xh("-I", "-b", "-xx", f":{P}/echo", "a=1")
check("compress-xx", '"Content-Encoding": "deflate"' in o, o[:200])
# 13. netrc matches the host string you typed
nrc1 = os.path.join(d, "netrc.localhost"); open(nrc1, "w").write("machine localhost login netu password netp\n")
rc, o, _ = xh("-b", f":{P}/whoami", env={"NETRC": nrc1})
try:
    auth = json.loads(o)["auth"]
    check("netrc-host-match", auth == "Basic " + base64.b64encode(b"netu:netp").decode(), auth)
except Exception as ex:
    check("netrc-host-match", False, str(ex))
nrc2 = os.path.join(d, "netrc.127"); open(nrc2, "w").write("machine 127.0.0.1 login netu password netp\n")
rc, o, _ = xh("-b", f":{P}/whoami", env={"NETRC": nrc2})
try:
    check("netrc-host-mismatch", json.loads(o)["auth"] == "", o[:200])
except Exception as ex:
    check("netrc-host-mismatch", False, str(ex))
# 14. session round-trip + plaintext auth persistence
xdg = os.path.join(d, "xdg")
rc, o, e = xh("-I", "--session", "s1", f":{P}/cookie", env={"XDG_CONFIG_HOME": xdg})
rc2, o2, e2 = xh("-I", "--session", "s1", f":{P}/whoami", env={"XDG_CONFIG_HOME": xdg})
rc3, o3, e3 = xh("-I", "--session", "s1", "-a", "u:p", f":{P}/whoami", env={"XDG_CONFIG_HOME": xdg})
sess = os.path.join(xdg, "xh", "sessions", f"localhost_{P}", "s1.json")
try:
    content = open(sess).read()
    cookie_back = json.loads(o2)["cookie"] == "sid=abc123"
    auth_plain = json.loads(o3)["auth"].startswith("Basic ") and '"raw_auth": "u:p"' in content
    check("session-roundtrip", cookie_back and auth_plain and '"about": "xh session file"' in content,
          f"o2={o2[:80]} auth_plain={auth_plain}")
except Exception as ex:
    check("session-roundtrip", False, f"{ex} :: {o2[:80]} {e2[:120]}")
# 15. piped -m prints the body, not metadata
rc, o, _ = xh("-I", "-m", f":{P}/get")
check("piped-m-body", "Elapsed" not in o and '"args"' in o, o[:120])
# 16. curl translation reveals the http default scheme
rc, o, e = xh("--curl", "-I", "example.org/get")
check("scheme-http-default", rc == 0 and o.strip() == "curl http://example.org/get", (o + e).strip()[:120])

srv.shutdown()
print("xh recipe-check: ALL PASS" if not failed else "xh recipe-check: %d FAILED" % len(failed))
sys.exit(1 if failed else 0)
```