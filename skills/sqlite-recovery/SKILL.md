---
name: sqlite-recovery
description: Use when a SQLite database fails PRAGMA integrity_check, opens with "database disk image is malformed" or "file is not a database", or a full-text index starts erroring — extract the readable data and rebuild a clean database with working FTS5 indexes.
version: 1.0.0
author: H190K
license: MIT
platforms: [linux, macos, windows]
---

# SQLite Recovery

## Overview

A corrupt SQLite database is often more salvageable than it looks: corruption typically lands in
freelist pages, indexes, or FTS auxiliary tables, while the b-tree holding the actual rows is intact.
The procedure is always the same three moves — assess without trusting the connection, extract the
readable rows, rebuild a clean database — followed by re-creating any full-text indexes and verifying.

Everything below was exercised on a deliberately corrupted database (one damaged index page; contents
recovered intact) and on a heavier variant (two clobbered data pages) so the failure modes are real,
not theoretical.

## Phase 1 — Assess, expecting the connection itself to fight you

With journal mode off (recovery, not normal operation) run, wrapped per statement in try/except:

1. `PRAGMA integrity_check` — the headline symptom. **It can itself raise `database disk image is
   malformed` instead of listing problems** when data pages are damaged; an exception here does not
   mean nothing is readable.
2. List tables from `sqlite_master`; fetch each table's `sql` — schema text is usually recoverable
   even from bad files.
3. `SELECT COUNT(*)` per table. **On index-page-only corruption the data reads may all succeed** while
   `integrity_check` fails — that is the salvageable case, so always try the counts before declaring
   the file lost.

```python
import sqlite3
conn = sqlite3.connect("corrupt.db")
conn.execute("PRAGMA journal_mode=OFF")
for step in ("PRAGMA integrity_check", "SELECT name, sql FROM sqlite_master", ...):
    try:
        print(conn.execute(step).fetchall())
    except sqlite3.DatabaseError as e:
        print("failed:", step, e)   # keep going — later steps can still succeed
```

Expect `PRAGMA table_info(...)` and schema reads to be the most reliable reads in a damaged file.

Two other common symptoms: opening a non-SQLite file raises `file is not a database`, and an FTS
query fails with `OperationalError: no such column: X` when the FTS declaration drifted from the
content table (rebuild the index, below).

## Phase 1.5 — When plain SELECT cannot read the rows

If SELECTs fail with `database disk image is malformed` (data pages themselves damaged), try:

```bash
sqlite3 corrupt.db ".recover" | sqlite3 recovered.db    # needs the sqlite_dbpage extension built in
sqlite3 corrupt.db ".dump"    > dumped.sql              # best-effort readable rows; tolerates partial reads
```

- **`.recover` is not universally available**: on a stock sqlite3 3.45.1 CLI it failed with
  `sql error: no such table: sqlite_dbpage` — the distribution build lacked the extension. `.dump`
  still ran. Check both; if `.recover` is unavailable, `.dump` plus manual salvage is the fallback.
- Python's `sqlite3` module will not save you here — `Connection.iterdump()` raised
  `database disk image is malformed` on the same file `.dump` handled. The CLI and the stdlib module
  are different builds with different capabilities; try both.
- Heavier byte damage (clobbered data pages) can defeat both tools: every read path ends in
  `malformed`, and only sector-level salvage outside SQLite remains.

## Phase 2 — Extract with explicit column names

**Get column names from `PRAGMA table_info()` — never assume column order matches `SELECT *` output,
and never rely on positional inserts.**

```python
extracted = {}
for tname in tables:                    # the non-FTS table names from Phase 1
    cols = [r[1] for r in conn.execute(f'PRAGMA table_info("{tname}")')]
    sel = ", ".join(f'"{c}"' for c in cols)
    extracted[tname] = (cols, conn.execute(f'SELECT {sel} FROM "{tname}"').fetchall())
```

`PRAGMA table_info` returns `(cid, name, type, notnull, dflt_value, pk)` — the **name is index 1**, not
index 0. Using index 0 gives `table X has no column named 0`.

## Phase 3 — Rebuild into a fresh database

1. **Keep the corrupt file.** Rename it aside (`mv corrupt.db corrupt.db.bak`) and never delete it
   until verification passes; a bug in the recovery script must be retryable from the original.
2. Create a fresh database, set `PRAGMA journal_mode=WAL` if the application expects concurrent
   readers, and re-execute the saved `CREATE TABLE` statements.
3. Insert rows with explicit column lists and `?` placeholders:

```python
new = sqlite3.connect("fresh.db")
new.execute("PRAGMA journal_mode=WAL")
for stmt in create_statements:
    new.execute(stmt)
for tname, (cols, rows) in extracted.items():
    ph = ",".join("?" * len(cols))
    cl = ",".join(f'"{c}"' for c in cols)
    new.executemany(f'INSERT INTO "{tname}" ({cl}) VALUES ({ph})', rows)
new.commit()
```

## Phase 4 — Rebuild FTS5 indexes

Drop stale FTS tables from the fresh database, then re-create them **naming only columns that exist in
the content table** — an FTS5 declaration referencing an absent column fails at creation with
`no such column: X`. Check `PRAGMA table_info('<content table>')` first.

Rebuild the index by reinserting from the content table:

```python
new.execute(
    'CREATE VIRTUAL TABLE "doc_fts" USING fts5('
    'content, session_id UNINDEXED, role UNINDEXED, '
    'content="doc", content_rowid="id", tokenize="trigram")'
)
new.execute(
    'INSERT INTO "doc_fts"(rowid, content, session_id, role) '
    'SELECT id, content, session_id, role FROM "doc"'
)
```

- **Preserve the original tokenizer.** Trigram enables substring matching (`gatew` finds `gateway`);
  rebuilding with the default tokenizer silently changes search behaviour — verify with a substring
  query after rebuild.
- External-content tables (`content=` / `content_rowid=`) hold no text themselves; an empty FTS table
  after rebuild almost always means the reinsert step was skipped.

## Phase 5 — Verify

- [ ] `PRAGMA integrity_check` returns `ok`
- [ ] Row counts match the extracted originals (per table)
- [ ] Spot-check content: some rows read back verbatim
- [ ] FTS search returns expected hits, including a substring query if the index is trigram
- [ ] The application opens the database and its queries run
- [ ] The corrupt original is still on disk (backup, not deleted)

## Related skills

- **Why the database got this way** — the `systematic-debugging` skill: find the corruption's root
  cause (disk full, abrupt shutdown, missing `journal_mode=WAL` under concurrency) before trusting the
  rebuilt database in production again.
- **Evidence before reporting done** — the `verification-before-completion` skill; the Phase 5 list is
  its application here.