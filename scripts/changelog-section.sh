#!/usr/bin/env bash
set -euo pipefail
version=$1; file=${2:-CHANGELOG.md}
[[ -f $file ]] || exit 1
awk -v v="$version" '
 /^## / { if(found) exit; title=$0; sub(/^##[[:space:]]+/, "", title); sub(/[[:space:]]+-.*/, "", title); if (title==v || title=="[" v "]") { found=1; print; next } }
 found { print; content=1 }
 END { if (!found || !content) exit 1 }
' "$file"
