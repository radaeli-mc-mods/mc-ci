#!/usr/bin/env bash
set -euo pipefail
usage='Usage: onboard-repo.sh OWNER/REPO REVIEWER_LOGIN [--apply] [--ref main|v1]'
[[ $# -ge 2 ]] || { echo "$usage" >&2; exit 2; }
repo=$1; reviewer=$2; shift 2
apply=false; ref=main
while (( $# )); do
  case "$1" in --apply) apply=true; shift;; --ref) ref=${2:?missing ref}; shift 2;; *) echo "$usage" >&2; exit 2;; esac
done
[[ $repo =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ && $reviewer =~ ^[A-Za-z0-9-]+$ && $ref =~ ^(main|v1)$ ]] || { echo 'Invalid argument' >&2; exit 2; }
root=$(cd "$(dirname "$0")/.." && pwd)
branch=$(gh api "repos/$repo" --jq .default_branch)
visibility=$(gh api "repos/$repo" --jq .visibility)
[[ $visibility == public ]] || { echo 'Required reviewers require a public repository on Free.' >&2; exit 1; }
reviewer_id=$(gh api "users/$reviewer" --jq .id)
echo "Repository: $repo; default branch: $branch; reviewer: $reviewer ($reviewer_id); workflow ref: $ref"
echo 'Will configure environment and write templates into the CURRENT local directory; rulesets require separate setup.'
if [[ $apply != true ]]; then echo 'Dry run. Re-run with --apply in the mod checkout.'; exit; fi
[[ $(git remote get-url origin) == *"$repo"* ]] || { echo 'Current checkout origin does not match requested repository' >&2; exit 1; }
for f in .github/workflows/ci.yml .github/workflows/tag.yml .github/workflows/release.yml .github/mod-pipeline.json .github/dependabot.yml; do
  [[ ! -e $f ]] || { echo "Refusing to overwrite $f" >&2; exit 1; }
done
if gh api "repos/$repo/environments/curseforge" >/dev/null 2>&1; then
  echo 'Environment curseforge already exists; inspect and configure it manually.' >&2; exit 1
fi
payload=$(jq -n --argjson id "$reviewer_id" '{wait_timer:0,prevent_self_review:false,reviewers:[{type:"User",id:$id}],deployment_branch_policy:{protected_branches:false,custom_branch_policies:true}}')
printf '%s' "$payload" | gh api --method PUT "repos/$repo/environments/curseforge" --input - >/dev/null
jq -n '{name:"v*",type:"tag"}' | gh api --method POST "repos/$repo/environments/curseforge/deployment-branch-policies" --input - >/dev/null
mkdir -p .github/workflows
for name in ci tag release; do sed "s/@v1/@$ref/g" "$root/templates/$name.yml" > ".github/workflows/$name.yml"; done
sed -i "s/branches: \[main\]/branches: [$branch]/" .github/workflows/tag.yml
cp "$root/templates/mod-pipeline.json" .github/mod-pipeline.json
cp "$root/templates/dependabot.yml" .github/dependabot.yml
echo 'Edit mod-pipeline.json and remove old workflows in a reviewed PR. Configure branch and tag rulesets separately.'
