# Release preparation

Repository: https://github.com/l1qu1d/themertoggle

Permanent plugin ID: `io.github.l1qu1d.themertoggle`.
Category: **Appearance**. Tags: **bar, quickshell, hyprland**.

The repository starts private. Public visibility and marketplace publication are
separate actions. Do not describe it as listed or verified before publication.

Before making it public, run the checks in [CONTRIBUTING.md](CONTRIBUTING.md),
review the final diff and preview asset, and verify CI on the final commit. Enable
GitHub private vulnerability reporting when public visibility makes it available.
Remove the README's private-access paragraph at that point.

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
