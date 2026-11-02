#!/usr/bin/env bash
set -euo pipefail
usage='Usage: configure-rulesets.sh OWNER/REPO APP_ID "CONFIRMED_STATUS_CONTEXT" [--apply]'
[[ $# -eq 3 || ( $# -eq 4 && $4 == --apply ) ]] || { echo "$usage" >&2; exit 2; }
repo=$1; app_id=$2; status=$3; apply=${4:-}
[[ $repo =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ && $app_id =~ ^[0-9]+$ ]] || { echo 'Invalid repository or App ID' >&2; exit 2; }
root=$(cd "$(dirname "$0")/.." && pwd)
payload=$(python3 "$root/scripts/rulesets.py" --app-id "$app_id" --status "$status")
echo "$payload" | jq .
if [[ $apply != --apply ]]; then echo 'Dry run; verify the status context in a successful canary PR before using --apply.'; exit; fi
existing=$(gh api --paginate "repos/$repo/rulesets?per_page=100" --jq '.[].name')
for name in 'mc-ci: default branch' 'mc-ci: release tag creation' 'mc-ci: release tag immutability'; do
  if grep -Fxq "$name" <<< "$existing"; then echo "Ruleset exists: $name; inspect it rather than overwrite" >&2; exit 1; fi
done
for index in 0 1 2; do
  jq -c ".[$index]" <<< "$payload" | gh api --method POST "repos/$repo/rulesets" --input - --jq '"Created: \(.name) (\(.id))"'
done
echo 'If interrupted, inspect the rulesets before retrying; no rollback is automatic.'
