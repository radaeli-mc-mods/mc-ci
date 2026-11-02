#!/usr/bin/env bash
set -euo pipefail
mapfile -t values < <(sed -nE 's/^[[:space:]]*mod_version[[:space:]]*=[[:space:]]*([^[:space:]#]+)[[:space:]]*$/\1/p' "${1:-gradle.properties}")
if (( ${#values[@]} != 1 )) || [[ ! ${values[0]} =~ ^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-([0-9A-Za-z-]+\.)*[0-9A-Za-z-]+)?(\+([0-9A-Za-z-]+\.)*[0-9A-Za-z-]+)?$ ]]; then
  echo 'Expected exactly one semver mod_version' >&2; exit 1
fi
pre=${values[0]%%+*}; pre=${pre#*-}
if [[ ${values[0]%%+*} == *-* ]]; then
  IFS=. read -ra parts <<< "$pre"
  for part in "${parts[@]}"; do [[ ! $part =~ ^0[0-9]+$ ]] || { echo 'Invalid prerelease' >&2; exit 1; }; done
fi
printf '%s\n' "${values[0]}"
