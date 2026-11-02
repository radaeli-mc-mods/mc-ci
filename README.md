# mc-ci

Reusable GitHub Actions pipelines for Minecraft mods in `radaeli-mc-mods`. This repository is under development: use `@main` only in designated canaries until the release flow has been exercised end to end. Do not use the `@v1` templates until a tested `v1` tag exists.

## Pipeline

- Pull requests run the configured checks and a build for each target; jars are retained for seven days. The `result` job aggregates the checks.
- A push to the default branch creates an annotated `v<mod_version>` tag when that tag does not already exist. A GitHub App token causes the tag push to trigger the release workflow.
- A matching tag runs the build and waits for approval of the `curseforge` environment before uploading to CurseForge. Jars are retained for 90 days; this pipeline does not create GitHub Releases.

The reusable workflows and composites currently refer to `main` internally. Before cutting `v1.0.0` and `v1`, update those internal references to `v1`, validate the resulting commit using an appropriate canary, and then tag it. Keep major tags current only after verification. A moving major is a trust boundary: protect its tag and review changes to this repository.

## Prerequisites

- Public mod repositories; install a GitHub App with repository Contents read/write, set organization variable `RELEASE_APP_ID` and organization secret `RELEASE_APP_PRIVATE_KEY`, and make both available to the selected repositories.
- Make the organization secret `CURSEFORGE_TOKEN` available to the selected repositories. Only the protected publish job consumes it.
- Configure a `curseforge` environment in every caller repository with a required reviewer, self-review allowed if desired, and custom deployment policy allowing tags matching `v*`. Environment approvals apply to jobs. Depending on scheduling, matrix jobs may require separate reviews; verify the actual review experience for the canary.
- After the canary PR confirms the exact aggregate check context, run `bash scripts/configure-rulesets.sh OWNER/REPO APP_ID "CHECK_CONTEXT"` to preview repository rulesets; append `--apply` to create them. The branch ruleset requires PRs and that check and blocks force pushes. Two tag rulesets restrict `v*` creation to the App and organization admins, and updates/deletions to organization admins. Rulesets are applied per repository to avoid affecting repos that have not been onboarded. The script refuses to replace existing named rulesets; inspect partial results if an API call fails. Test these policies before relying on them.

## Onboarding

The script defaults to a dry run; it reads the repository metadata and reviewer identity. In the mod checkout run `bash /path/to/mc-ci/scripts/onboard-repo.sh OWNER/REPO REVIEWER --apply --ref main` for a canary. It creates the environment and copies templates only when the destination files and environment do not already exist. It does not apply rulesets, delete old workflows, commit changes, or publish; apply rulesets separately after validating the canary status context. Environment creation and policy creation are separate API operations: if interrupted, inspect the environment before retrying. The `--ref v1` option is for after the first validated release.

Edit `.github/mod-pipeline.json`: supply the display name, installed Java versions, checks, CurseForge project ID, release type, and one target per artifact. Each target needs an ID, a single Gradle task, file globs, loaders, game versions, Java version, and mc-publish dependency strings. The target Java version must occur in the top-level Java list. The build must yield exactly one primary jar per target; `-sources` and `-javadoc` jars are additional files, while `-dev`, `-dev-shadow`, and `-slim` jars are excluded. Each configured glob must match. Scope globs narrowly if several primary jars are produced.

The version is read from exactly one `mod_version` entry in root `gradle.properties` and must be SemVer. `auto` maps `-alpha*` to alpha, `-beta*` and `-rc*` to beta, and other versions to release. Changelog headings may be `## [1.2.3]` or `## 1.2.3`, optionally followed by a date. Missing notes fall back to a compare link when possible. Remove old `auto-tag.yml`, `pr-checks.yml`, and `release-on-tag.yml` in the onboarding PR to avoid duplicate workflows. Tagging now follows `mod_version`, rather than Conventional Commits.

Local, untracked jar dependencies do not exist on GitHub runners. Resolve or commit those dependencies before onboarding affected projects, including sophisticated-backpack-is-addon, minecolonies-butler, sable-horses, hqspeaker-sable-compat and flight-safety-instruments. RoadWeaver and tectonic use hardcoded build versions and are outside this rollout. Known CurseForge IDs from the plan: Copycat Replace `1662789`, Fly by Instruments `1766429`, Hotbar Locker `1702281`, Sophisticated Backpacks Digital Storage `1742266`; verify these against the owning projects before use.

## Validation before rollout

Run the repository self-test. With single-loader and multi-loader canaries on `@main`, verify PRs (including a fork), status-check names and artifacts; pushes with and without version bumps; App-created tags triggering release; manually mismatched tags failing; and approval followed by a CurseForge alpha upload with correct files, versions, loaders and dependencies. Validate tag protection and repeated or partially failed publishing separately; retrying a partially completed upload may create duplicates. Only then release this CI repository and onboard the remaining mods.

Local script checks: `bash tests/scripts-test.sh` and `python3 -m unittest discover -s tests -p 'test_*.py'`. `self-test.yml` also runs actionlint and zizmor.
