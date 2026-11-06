#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
printf 'mod_version=1.2.3-beta.1\n' > "$tmp/gradle.properties"
[[ $(bash "$root/scripts/read-version.sh" "$tmp/gradle.properties") == 1.2.3-beta.1 ]]
printf 'mod_version=1.2.3-01\n' > "$tmp/gradle.properties"
if bash "$root/scripts/read-version.sh" "$tmp/gradle.properties"; then exit 1; fi
printf 'mod_version=1.2.3\nmod_version=2.0.0\n' > "$tmp/gradle.properties"
if bash "$root/scripts/read-version.sh" "$tmp/gradle.properties"; then exit 1; fi
cat > "$tmp/CHANGELOG.md" <<'EOF'
# Changelog
## [1.2.3] - 2026-11-02

First release.
## 1.2.2

Earlier release.
EOF
[[ $(bash "$root/scripts/changelog-section.sh" 1.2.3 "$tmp/CHANGELOG.md") == $'## [1.2.3] - 2026-11-02\n\nFirst release.' ]]
[[ $(bash "$root/scripts/changelog-section.sh" 1.2.2 "$tmp/CHANGELOG.md") == *'Earlier release.'* ]]
if bash "$root/scripts/changelog-section.sh" 9.9.9 "$tmp/CHANGELOG.md"; then exit 1; fi
printf 'Script tests passed\n'
