#!/usr/bin/env bash
# Validate every skill in skills/: front matter, description budget, relative refs.
set -uo pipefail
cd "$(dirname "$0")/.."
fail=0
shopt -s nullglob

for dir in skills/*/; do
  name=$(basename "$dir")
  f="$dir/SKILL.md"
  err=""
  if [[ ! -f $f ]]; then
    echo "FAIL  $name — no SKILL.md"; fail=1; continue
  fi

  fm_name=$(sed -n 's/^name: *//p' "$f" | head -1 | tr -d '"')
  fm_desc=$(sed -n 's/^description: *//p' "$f" | head -1 | tr -d '"')

  [[ -z $fm_name ]] && err+="front matter has no name; "
  [[ -n $fm_name && "$fm_name" != "$name" ]] && err+="name: '$fm_name' does not match directory; "

  if [[ -z $fm_desc ]]; then
    err+="front matter has no description; "
  else
    dlen=${#fm_desc}
    if   (( dlen > 1024 )); then err+="description is $dlen chars (max 1024); "
    elif (( dlen > 500  )); then echo "warn  $name — description is $dlen chars; aim for under 500"; fi
  fi

  # relative file references mentioned in the body must resolve
  while read -r ref; do
    [[ -e "$dir$ref" ]] || err+="references missing file: $ref; "
  done < <(grep -oE '`(scripts|references|templates|assets)/[A-Za-z0-9._/-]+`' "$f" 2>/dev/null | tr -d '`' | sort -u)

  if [[ -n $err ]]; then
    echo "FAIL  $name — $err"; fail=1
  else
    echo "ok    $name"
  fi
done

exit $fail
