# Release preparation

Repository: https://github.com/l1qu1d/themertoggle

Permanent plugin ID: `io.github.l1qu1d.themertoggle`.
Category: **Appearance**. Tags: **bar, quickshell, hyprland**.

The repository is public. Keep the manifest and displayed version at `1.0.0`
until the maintainer requests a release increment. Use Git commits to identify
development changes between releases.

Public visibility and marketplace publication are separate actions. Do not
describe the plugin as listed or verified before marketplace approval.

Before each release, run the checks in [CONTRIBUTING.md](CONTRIBUTING.md), review
the final diff and preview asset, and verify CI on the final commit. GitHub
private vulnerability reporting is enabled for confidential reports.

Main requires a pull request, resolved review conversations, and the current
`test` GitHub Actions check. Only squash merges are allowed; force pushes and
branch deletion are blocked. CodeRabbit is configured in `.coderabbit.yaml` for non-draft pull requests.
Its current open-source eligibility rules can skip automatic reviews for
repositories with fewer than 10 stars. If its status comment skips a review,
use the **Trigger review** checkbox or comment `@coderabbitai full review`.
Check its actual result on the PR before treating the review as complete.

Follow the current marketplace [submission guide](https://github.com/omacom/omarchy-plugin-marketplace/blob/main/SUBMISSION.md)
and [security policy](https://github.com/omacom/omarchy-plugin-marketplace/blob/main/SECURITY.md).
The root manifest, README, license, dependency descriptions, installation/removal
commands, and preview must remain present. Do not include agent-control instruction
files in the distributed plugin tree. Confirm that the permanent plugin ID is
still available, including retired IDs.

A submission draft is in [docs/marketplace-submission.md](docs/marketplace-submission.md).
Before submitting, confirm every checklist statement and obtain the owner's
explicit approval of the completed title and body. It must be a public repository
when submitted. The draft is preparation, not a submitted issue.

Marketplace checks and approval bind to the exact validated commit. New commits
require new matching evidence. Initial publication requires the marketplace's
`approved-and-verified` maintainer decision following its compatibility and
Automated Security Baseline checks. Local preflight results do not replace that
process or constitute a security audit. After listing, use the marketplace's
verification/update form to promote subsequent commits.
