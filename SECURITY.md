# Security

## Runtime access

ThemerToggle runs as your user inside Omarchy's unsandboxed Quickshell shell.
Its Python helper reads installed theme directories, their colors and preview
images, and Omarchy's current-theme state. It writes remembered theme IDs and a
process lock under `~/.local/state/omarchy-themertoggle/`.

Theme changes run `omarchy theme set <installed-theme-id>` using an argument
array, without shell interpolation. Omarchy then updates its normal application
configurations and runs the user's installed theme hooks. ThemerToggle does not
bypass those hooks or stop the setter midway. Only one plugin switch may run at
a time; repeated requests are ignored rather than queued.

The plugin makes no network requests, downloads no code, collects no telemetry,
and accesses no account credentials. Preview images are local files loaded by Qt.
No sudo or pkexec is required. It installs no services and edits no keyboard
bindings. Omarchy's own theme command and user hooks may have additional effects.

Dependencies are supplied by the installed Omarchy system. Test CI checks out an
immutable upstream Omarchy commit and pins GitHub Actions by full commit SHA.
There are no bundled executable binaries or third-party runtime packages.

## Reporting

Report vulnerabilities privately using
[GitHub private vulnerability reporting](https://github.com/l1qu1d/themertoggle/security/advisories/new)
once the repository is public and reporting is enabled. While it is private,
contact the repository owner through an existing private channel. Do not post
credentials, personal data, or exploit details in public issues.

Include the affected commit, Omarchy version, and a minimal reproduction with
sensitive data removed. Security fixes target the latest version on `main`.

## Verification scope

Local tests and marketplace compatibility checks are not a security audit or
certification. Marketplace review applies to an exact commit. A newer commit
requires fresh review; standard Omarchy installation follows upstream HEAD.
This project does not claim marketplace approval before that process completes.
