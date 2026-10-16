---
name: minecraft-modpack-server
description: Use when installing, first-launching, or operating a modded Minecraft server from a CurseForge or Modrinth pack — choosing the right Java per game version, NeoForge/Forge installer flags, the EULA gate, server.properties and JVM tuning, Modrinth .mrpack server builds via mrpack-install, backups, and first-boot verification. Behaviors were verified live against NeoForge 21.11.48 and mrpack-install 0.16.10.
version: 1.0.0
author: H190K
license: MIT
platforms: [linux, macos]
---

# Minecraft Modpack Server

A guide for standing up a modded Minecraft server from a published pack: identify the pack
format, install the matching Java, install the mod loader, pass the EULA gate, configure and
tune, back the world up. Most steps below were verified end-to-end on a scratch box; claims
borrowed from external docs are labeled as such.

## When to use

The user wants any of these:

- A modded Minecraft server from a specific pack (All The Mods, Adrenaline, a custom pack).
- To move a pack's server files onto a server and get it running (loader install, EULA, port).
- JVM/RAM and GC tuning for a modded server, or automated world backups.
- To build a *server* directory out of a Modrinth `.mrpack` (client pack by default).

## 0. Gather preferences before generating config

If the user cares, ask before writing `server.properties`: server name/MOTD, seed, difficulty,
gamemode, `online-mode`, expected player count (drives RAM and view distance), PvP, whitelist,
backup cadence. Otherwise apply the defaults used below and say so.

## 1. Identify the pack format

- **CurseForge-style server pack (or any `.zip` containing `startserver.sh`/`run.sh`, an
  installer jar, `user_jvm_args.txt`, `mods/`)**: the pack already targets a server. Inspect the
  launch script for the loader (neoforge/forge), its version, and the Java it assumes.
- **Modrinth `.mrpack`**: by default a *client* pack — a small zip with `modrinth.index.json`
  and `overrides/`. See §7 for building a server from it.

Useful checks on an unknown zip: `unzip -l <pack> | head -30`, and inside
`modrinth.index.json` the `dependencies` object names `minecraft` plus the loader and version.

## 2. Install the right Java

Verified against Mojang's own version manifest — each version entry carries a `javaVersion`
field — so this table is authoritative, not folklore:

| Minecraft       | Java | Manifest `javaVersion.component` |
| --------------- | ---- | -------------------------------- |
| 26.1 – 26.3     | 25   | `java-runtime-epsilon`           |
| 1.20.5 – 1.21.x | 21   | `java-runtime-delta`             |
| 1.18 – 1.20.4   | 17   | `java-runtime-gamma`/`-beta`     |
| 1.17 – 1.17.1   | 16   | `java-runtime-alpha`             |
| 1.16.5 and older | 8    | `jre-legacy`                     |

Common wrong guess: 1.20.5/1.20.6 moved to Java 21 (with 1.21), not 17.

To check any version live:

```bash
curl -s https://piston-meta.mojang.com/mc/game/version_manifest_v2.json | python3 -c '
import json, sys, urllib.request
m = json.load(sys.stdin)
entry = {v["id"]: v for v in m["versions"]}["<MCVERSION>"]
print(json.load(urllib.request.urlopen(entry["url"]))["javaVersion"])'
```

On Ubuntu 24.04, `openjdk-25-jre-headless` is packaged (verified in the repos), so the 26.x Java
line installs normally: `sudo apt install openjdk-25-jre-headless` (or `-21-` for the 1.20.5+
line, `-17-` for 1.18–1.20.4, `-11-`/`-8-` for older). Verify with `java -version`.

## 3. Install the loader (NeoForge / Forge)

NeoForge installer jars live at
`https://maven.neoforged.net/releases/net/neoforged/neoforge/<ver>/neoforge-<ver>-installer.jar`.
The NeoForge version prefix tracks the game version (verified: NeoForge `21.11.48` runs
Minecraft 1.21.11; the `26.3.0.x` line builds for MC 26.3). Forge is still maintained too —
`https://files.minecraftforge.net/net/minecraftforge/forge/promotions_slim.json` lists
`<mcversion>-recommended` entries (verified: `26.2-recommended` = 65.1.0).

Installer CLI, verified against the real binary:

```text
--install-server, --installServer   Install a server to the given dir (default: current dir)
--debug       Run in debug mode -- don't delete any files
--offline     Don't attempt any network calls
--mirror URL  Use a specific mirror
--skip-hash-check   Skips the hash check when verifying outputs
--server-jar, --server.jar, --server-starter   Download an arg-free executable server jar
-h, --help    Help (also: --fat installer generation options)
```

Install (progress logs to `installer.jar.log`; success line reads
`The server installed successfully`):

```bash
curl -L -o installer.jar https://maven.neoforged.net/releases/net/neoforged/neoforge/<ver>/neoforge-<ver>-installer.jar
mkdir server && cd server
java -jar ../installer.jar --installServer
```

Verified produced layout: `run.sh`, `run.bat`, `user_jvm_args.txt`, and
`libraries/net/neoforged/neoforge/<ver>/unix_args.txt` (`win_args.txt` alongside). The shipped
`run.sh` is a one-liner:

```bash
exec java @user_jvm_args.txt @libraries/net/neoforged/neoforge/<ver>/unix_args.txt "$@"
```

Pack scripts often predate `run.sh` and may wrap the launch in an auto-restart loop — read the
pack's launcher once, then drive the plain `java @…args` command yourself so restarts are your
decision.

## 4. Launch: EULA gate, then "Done"

1. RAM: uncomment/append `-Xmx…G` (and `-Xms…G` to pin) in `user_jvm_args.txt`.
2. Accept the EULA: `echo "eula=true" > eula.txt`. Verified behavior without it: the server
   exits with code 1 within seconds and logs
   `You need to agree to the EULA in order to run the server. Go to eula.txt for more info.`
   — this check runs *before* worldgen, so a slow first boot is never the cause.
3. Launch: `./run.sh nogui` (or `java @user_jvm_args.txt @libraries/…/unix_args.txt nogui`).
4. Ready marker, verified in the log: `Done (X.XXs)! For help, type "help"`. Watch with
   `tail -f logs/latest.log`.

Write `server.properties` *before* the first launch — verified: pre-seeding a flat world with
low view distance reached `Done` in under a second. Delete `world/` to regenerate with a new
seed.

## 5. server.properties that matter for modded servers

Definitions verified against the `Server.properties` wiki page; the escaped-MOTD round-trip
(ESC form in, glyphs back) was verified live:

```properties
motd=\u00a7bServer Name \u00a7r\u00a78| \u00a7aModpack name   # \u00a7 escapes survive round-trip
server-port=25565
online-mode=true            # false for LAN/offline players
enforce-secure-profile=true # only Mojang-signed keys may join; pair with online-mode above
allow-flight=true           # false kicks players in Survival flight for 5s — breaks fly mods
max-tick-time=180000        # vanilla watchdog kills the server past the limit (default 60000);
                            # the kill message cites the tick time; -1 disables the watchdog
spawn-protection=0          # 0 disables spawn protection (value = side length 2x+1)
pause-when-empty-seconds=60 # default 60: server auto-pauses with no players; set 0 to tick always
```

Verified gotcha: with nothing connected, a fresh server logs
`Server empty for 60 seconds, pausing` — schedulers and automation that expect the tick loop to
run silently stop. Set `pause-when-empty-seconds` accordingly.

Performance baselines scaled to hardware (tune to the box): `view-distance` 16/10/8 and
`simulation-distance` 10/6/4 for light/moderate/heavy load respectively.

## 6. JVM sizing and GC flags (one flag is a trap)

Rule-of-thumb RAM for modded: 100–200 mods → 6–12 GB, 200–350+ mods → 12–24 GB; leave ≥8 GB
for the OS. The classic G1 set still applies, with one trap verified on Java 21:
`-XX:SurvivorRatio=32` is **rejected** — `SurvivorRatio (32) must be less than or equal to
ergonomic SurvivorRatio maximum (16)` — that value predates modern JVM ergonomics. Use `16`
(verified accepted) or drop the flag; keep experimental G1 keys after
`-XX:+UnlockExperimentalVMOptions`:

```text
-XX:+UseG1GC
-XX:+ParallelRefProcEnabled
-XX:MaxGCPauseMillis=200
-XX:+UnlockExperimentalVMOptions
-XX:+DisableExplicitGC
-XX:+AlwaysPreTouch
-XX:G1NewSizePercent=30
-XX:G1MaxNewSizePercent=40
-XX:G1HeapRegionSize=8M
-XX:G1ReservePercent=20
-XX:G1HeapWastePercent=5
-XX:G1MixedGCCountTarget=4
-XX:InitiatingHeapOccupancyPercent=15
-XX:G1MixedGCLiveThresholdPercent=90
-XX:G1RSetUpdatingPauseTimePercent=5
-XX:SurvivorRatio=16
-XX:+PerfDisableSharedMem
-XX:MaxTenuringThreshold=1
```

Validate any proposed flag set *before* putting it into production — an invalid flag fails at JVM
init, so `-version` accepts the same flags in seconds and refuses bad ones with the JVM's own
error:

```bash
java -Xms64m -Xmx128m <flags> -version
```

## 7. Modrinth `.mrpack` route (verified end-to-end)

The Modrinth API is read-usable without a key: `/v2/project/<slug>` and
`/v2/project/<slug>/version` return project and version metadata, and the version's `files[]`
carry direct CDN `url`s. A `.mrpack` is a zip containing `modrinth.index.json` (verified keys:
`files[].path`, `files[].hashes`, `files[].env.client` / `env.server`, `files[].downloads[]`,
`files[].fileSize`, top-level `dependencies`, and `overrides/`). `env.server` is
`required`, `optional`, or `unsupported` — that mark is the difference between a client instance
and a server directory.

**Automated (verified against `mrpack-install` v0.16.10, a Go binary from nothub/mrpack-install):**

```bash
curl -sL -o mrpack-install https://github.com/nothub/mrpack-install/releases/download/v0.16.10/mrpack-install-linux
chmod +x mrpack-install
mrpack-install <slug> [<version>]            # or a local .mrpack path or URL
```

Verified on a real pack: it downloaded exactly the `env.server: required` mods (20 of 31),
skipped `unsupported`-marked client-only mods, extracted `overrides/`, installed the Fabric
loader jar (`fabric-server-mc.<mc>-loader.<loader>-launcher.<n>.jar`), and recorded the
deployment in `modpack.json` (pack name/version plus per-file hashes and links, which its
`update` subcommand re-reads). Flags from `--help`: `--server-dir`, `--server-file`,
`--host`, `--download-threads`, `--retry-times`, `--proxy`; subcommands `server`, `update`,
`ping`, `version`.

Two verified gotchas: it does **not** create `eula.txt` or `server.properties` — the EULA step
above is still yours; and its current README can be **stale relative to the binary** — v0.16.10
rejects a flag its README documents (`Error: unknown flag: --optional-select`), so trust the
binary's `--help`.

**Manual build** (when you want more control or no extra binary): unzip the pack, then

```bash
python3 -c '
import json, urllib.request
idx = json.load(open("modrinth.index.json"))
for f in idx["files"]:
    if f["env"]["server"] in ("required", "optional"):
        urllib.request.urlretrieve(f["downloads"][0], f["path"])'
```

then copy `overrides/` contents over the server dir and install the loader named in
`dependencies` (Fabric ships that launcher-jar form; NeoForge/Forge use the installer from §3).

## 8. CurseForge route

- Many packs publish a ready server-pack zip from the pack page — prefer it; that is the zip
  flow of §1–§6.
- Automated CurseForge downloads need a CurseForge API key (the API is not key-free). The
  `itzg/minecraft-server` Docker image documents automated pack fetching for both platforms —
  its readthedocs pages (verified accessible) cover server properties, mods management, and
  modpack platforms, including `MODRINTH_PROJECTS` and `EULA` environment variables.

## 9. Container alternative

`itzg/minecraft-server` runs the whole flow from env vars (`EULA=TRUE`,
`MODRINTH_PROJECTS=<pack:version>`, property overrides). Use it when the runtime is already
Docker; the image's documentation at docker-minecraft-server.readthedocs.io is the contract.
Bare metal remains the most transparent path when debugging a misbehaving pack.

## 10. Backups

Keep a rolling `tar.gz` of `world/`, prune old ones, run it from cron. The trim-below-max logic
is verified (3 backups, `MAX_BACKUPS=2` left exactly the 2 newest). For a consistent snapshot,
run the backup right after `save-all` in the console (or during a planned stop):

```bash
#!/bin/bash
SERVER_DIR="/srv/minecraft/server"
BACKUP_DIR="/srv/minecraft/backups"
WORLD_DIR="$SERVER_DIR/world"
MAX_BACKUPS=24
mkdir -p "$BACKUP_DIR"
[ -d "$WORLD_DIR" ] || { echo "[BACKUP] No world folder"; exit 0; }
STAMP=$(date +%Y-%m-%d_%H-%M-%S)
tar -czf "$BACKUP_DIR/world_${STAMP}.tar.gz" -C "$SERVER_DIR" world
COUNT=$(ls -1t "$BACKUP_DIR"/world_*.tar.gz 2>/dev/null | wc -l)
if [ "$COUNT" -gt "$MAX_BACKUPS" ]; then
    REMOVE=$((COUNT - MAX_BACKUPS))
    ls -1t "$BACKUP_DIR"/world_*.tar.gz | tail -n "$REMOVE" | xargs rm -f
fi
```

Schedule hourly with crontab (`0 * * * * <path>/backup.sh >> <path>/backup.log 2>&1`).

Firewall (comment syntax verified in ufw ≥0.35 docs): `sudo ufw allow 25565/tcp comment
"Minecraft Server"`.

## Pitfalls

- Wrong Java is the #1 failure: match the table in §2; the server dies at startup, not with a
  friendly message about Java.
- EULA exits in seconds *before* worldgen (verified) — a hung first boot is not the EULA.
- First startup of a real pack is slow (worldgen for big packs) and `Can't keep up!` warnings
  during it are normal; they settle.
- With no players, modern servers self-pause after `pause-when-empty-seconds` (verified
  default 60; marker `Server empty for 60 seconds, pausing`).
- `allow-flight=true` is required for most modded packs (fly items).
- If `online-mode=false`, set `enforce-secure-profile=false` too — offline players have no
  Mojang-signed key and are rejected otherwise; also expect unsigned chat (wiki-verified
  behavior).
- Pack launch scripts often restart-loop; use the plain `run.sh`/args command.
- A `.mrpack` is a client pack; `env.server` decides the server mod list — never copy all mods.
- Tool READMEs can lag binaries (verified with `mrpack-install`); re-run `--help` on the
  installed version before scripting flags.

## Verify before reporting done

- `java -version` matches the pack's Minecraft version (table in §2).
- Loader installed: `run.sh`/`user_jvm_args.txt`/`unix_args.txt` exist (NeoForge) or the pack's
  own launcher artifacts are in place.
- `logs/latest.log` contains `Done (…)!` and no `FATAL`/crash lines; `pgrep -fa <loader>` shows
  the running process (its full command line contains the loader's args path, which is what
  `-f` matches).
- Port reachable from outside: `nc -zv <server-host> 25565` (and the firewall rule above).
- Backup cron lists with `crontab -l` and one dry-run of the script exists in `backups/`.