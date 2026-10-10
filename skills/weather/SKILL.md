---
name: weather
description: Use when a task needs current weather, rain/temperature checks, a multi-day forecast, sunrise/sunset or moon phase, or when comparing locations or planning around conditions — wttr.in needs no key and answers in one curl.
version: 1.0.0
author: adapted from openclaw/openclaw (MIT); wttr.in service behavior measured live
license: MIT
platforms: [linux, macos, windows]
---

# Weather

Fetch weather in one line from `wttr.in` — no API key, no client library, no
rate-limit signup. This skill tells the agent what to request, how to read the
answer, and where the service quietly surprises you.

## When to use

- "Is it raining in `<place>` right now?" / "How hot will it be tomorrow?"
- Sunrise/sunset, moon phase, UV, pressure, humidity, feels-like.
- Comparing a handful of locations before travel or scheduling.
- You need weather inside a script or agent output and don't want a keyed API.

When the deliverable is heavy analysis (trend charts, historical data), use a
proper archive API instead — wttr.in forecasts 3 days max. For severe weather
and official warnings, verify against a national service.

## What the service gives you

One HTTP GET, three useful shapes:

- `?format=3` — one line: `Baghdad: 🌤️  +31°C`
- `?format=j1` — full JSON: current + 3-day forecast + hour-by-hour (≈40 KB)
- plain URL, no query — the 3-day ASCII-art panel for humans

The URL path is the location; flags ride the query string. Everything below was
measured live against the running service (2026-10-10).

## Pick the format deliberately

| Query | Returns | Use when |
| --- | --- | --- |
| `?format=3` | `<loc>: <icon> <temp>` one-liner | Quick check, one place |
| `?format=j1` | Full JSON, all fields, ≈40 KB | Structured extraction, hourly data |
| `?format=j2` | Same minus `hourly` — ≈3 KB | Current + daily; hourly not needed |
| `?0` | Current conditions block only (≈0.3 KB) | Tiny text answer |
| `?1` | Current + today's forecast (≈3 KB) | Current + today, no hourly |
| `?2` | Current + today + tomorrow | One extra day of panel |
| bare URL | Full 3-day ASCII panel (≈8 KB) | Human-readable dump to read |

`j2` is the compact shape and the first choice for agents; reach for `j1` only
when `hourly` — 3-hour slots — is needed for real.

## The JSON, precisely

`j1`/`j2` share the top level: `current_condition`, `nearest_area`, `request`,
`weather` (3 entries: today, tomorrow, day after). All values are JSON
**strings**, so cast before arithmetic. Measured field map:

- `current_condition[0]`: `temp_C`/`temp_F`, `FeelsLikeC`/`FeelsLikeF`,
  `humidity`, `precipMM`, `pressure`, `uvIndex`, `visibility`, `cloudcover`,
  `observation_time`, `weatherDesc[0].value`, and wind as
  `winddirDegree`/`winddir16Point`/`windspeedKmph`/`windspeedMiles`
- `weather[i]`: `date`, `maxtempC`/`mintempC`, `uvIndex`,
  `astronomy[0]` → `sunrise`/`sunset`, `moonrise`/`moonset`, `moon_phase`,
  `moon_illumination`
- j1 only: `weather[i].hourly` — 8 three-hour slots per day. `time` is
  `0,300,600…2100` — **not zero-padded** (`900` = 09:00, `1200` = noon).
  Each slot: `tempC`, `precipMM`, `chanceofrain`/`chanceofsnow`/
  `chanceofthunder`, `weatherDesc[0].value`, `windspeedKmph`.

`nearest_area[0]` reports the *resolved* place: `areaName[0].value`,
`region[0].value`, `country[0].value`, `latitude`/`longitude`. First measured
trap: the resolver scores fuzzy matches, so a misspelled location can answer
with data for a place you never asked about. **Read `nearest_area` back and
state the resolved place in your answer** — on a misspelling, correct it or
ask; don't trust the hit.

## Location syntax

- `/paris` city · `/Eiffel+tower` any landmark (`+` = space) · `/Москва` Unicode names work
- `/muc` 3-letter airport code · `/94107` US ZIP · `/@stackoverflow.com` domain → server location
- `/~30.5,47.8` raw GPS coordinates (`~` prefix) · `/Paris,FR` trailing `,CC` disambiguates same-named towns
- **`+` and `_` are different separators** — measured: `/New+York` → +17°C, `/New_York` → +27°C
  (a different `New York` place). `%20` also works; an underscore is a literal character.
- **A misspelled place usually does not error** — it fuzzy-hits something else
  (measured: `/pyras,FR` → a Paris-area match). Only hopeless strings fail:
  `/qqzzxxww` → HTTP **500** with a text body (`location not found: ...`),
  not a JSON error. Scripts: use `curl --fail` and check the body prefix.

## The gotchas, measured

1. **User-Agent decides content, not the URL.** Browser-like UA + `?format=3`
   returns a ~12 KB **HTML page** instead of the one-liner; the same URL with a
   `curl/8.5` UA returns the line. JSON (`j1`/`j2`) is UA-immune. In scripts
   set `-A 'curl/8.5'` and the trap disappears.
2. **ANSI escapes ride in terminal output by default** — ~11 escape sequences
   per panel; add flag `T` (measured: 11 → 0) or use JSON formats.
3. **Units are a query flag, not a path segment**: `?m` metric (default outside
   the US), `?u` USCS, `?M` wind in m/s — measured: London `?u` → `+52°F … 11mph`, `?M` → `5m/s`.
4. **`wttr.is` is the drop-in mirror** (same operator; `:help` calls it a
   "fully equivalent replacement"): `/Baghdad?format=3` returned identically.
   Use it when wttr.in is slow or erroring.
5. **`?lang=ar` localizes condition text** (measured: `مشمس +33°C`);
   `fr.wttr.in/Paris` and `Accept-Language` work the same way.
6. **Moon phase**: the one-liner formats carry no moon data — use j1/j2's
   `astronomy[0].moon_phase` + `moon_illumination`, or the graphic
   `/moon?format=%m`; `/moon@2026-10-25` targets a date.
7. **`+` in the format prints a space** (measured: `?format=%t+feels+%f` →
   `+31°C feels +28°C`) — separators inside format strings are `+`.
8. **Condition text carries a trailing space**: `%C` → `Partly Cloudy ` and
   j1/j2 `weatherDesc[0].value` → `'Partly Cloudy '` (measured). Composed
   lines show it (`Partly Cloudy , +31°C`) and string compares silently fail —
   `.strip()` before matching or presenting.

## The format language

Placeholders measured live (Baghdad, 2026-10-10):

| Placeholder | Meaning | Sample output |
| --- | --- | --- |
| `%l` | resolved location | `Baghdad` |
| `%c` | emoji condition icon | `🌤️` |
| `%C` | condition text | `Partly Cloudy` |
| `%t` / `%f` | temperature / feels-like | `+31°C` / `+28°C` |
| `%w` | wind | `↓19km/h` |
| `%h` | humidity | `26%` |
| `%p` | precipitation | `0.0mm` |
| `%P` | pressure | `1014hPa` |
| `%u` | UV index | `2` |
| `%S` / `%s` | sunrise / sunset | `06:02:45` / `17:36:05` |
| `%D` / `%d` | dawn / dusk | `05:36:48` / `18:02:24` |
| `%T` | location's local time | `10:06:47+0300` |
| `%m` | ASCII moon-phase graphic | ~20-line moon art |
| `%W` | **unimplemented** — echoes literally | `%W` |

(%S/%s measured as a pair; the service prints dawn/dusk and sunrise/sunset in
`HH:MM:SS` local time.)

Compose one line, then eyeball the result before scripting it further:

```bash
curl -fsS --max-time 20 -A curl/8.5 \
  'https://wttr.in/Baghdad?format=%l:+%c+%C,+%t,+feels+%f,+rain+%p,+wind+%w'
# → Baghdad: 🌤️  Partly Cloudy , +31°C, feels +28°C, rain 0.0mm, wind ↓19km/h
#   (note the space before the comma — gotcha 8 below)
```

## One-line recipes

```bash
# All recipes: no key, safe from any shell with curl. Prefix used throughout:
CURL="curl -fsS --max-time 20 -A curl/8.5"

# Current conditions, one line
$CURL 'https://wttr.in/Paris,FR?format=3'

# Compact JSON for extraction (no hourly) — parse with python/jq
$CURL 'https://wttr.in/Baghdad?format=j2'

# Hour-by-hour (three-hour slots) — only j1 carries hourly
$CURL 'https://wttr.in/Baghdad?format=j1'

# Full ASCII panel, colors stripped, for logs or reports
$CURL 'https://wttr.in/Baghdad?T'

# Sunrise/sunset for scheduling
$CURL 'https://wttr.in/Baghdad?format=%l:+sunrise+%S,+sunset+%s'

# Rain risk across today (slot 900 = 09:00 … 2100 = 21:00)
$CURL 'https://wttr.in/Baghdad?format=j1' | python3 -c \
  'import json,sys
d=json.load(sys.stdin)
for h in d["weather"][0]["hourly"]:
    print(h["time"], h["tempC"], h["chanceofrain"])'
```

## Rules

- Set a non-browser User-Agent (`-A curl/8.5`) or add flag `A`/`T` — otherwise
  one-liner queries come back as HTML.
- Prefer `j2` for extraction; take the ~13× bigger `j1` only for hourly slots.
- For one-place questions answer with a one-liner; ship the full panel only
  when a full view was asked for — and state the resolved place (from
  `nearest_area`) in the answer.
- Values are strings; cast before arithmetic.
- On failure: a hopeless location string makes `curl -f` exit non-zero (code
  22) on the HTTP 500; without `-f`, detect it by the `location not found`
  body prefix. Retry with a corrected or `,CC`-disambiguated query. Service
  slow or down: same paths on `wttr.is`.

## Related skills

- `research` — when the weather lookup is one input of a broader task, the
  fetch discipline and uncertainty notes there still apply.
- `grounded-citations` — if the deliverable cites these fetched values, follow
  its citation marker rules.