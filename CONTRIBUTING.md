# Contributing

Keep the plugin small and native to Omarchy Quattro. Use the canonical Omarchy
color resolver and theme setter; preserve user overlays and theme hooks.

## Checks

On Omarchy Quattro:

```bash
python3 -m unittest discover -s tests -v
omarchy plugin validate .
bash tests/qml-smoke.sh
```

Backend tests use temporary homes and a fake setter, so they do not change your
desktop theme. They need the installed `omarchy-theme-color` resolver; set
`OMARCHY_THEME_COLOR` to another checkout's resolver when testing off Omarchy.
The native QML smoke test needs Quickshell, QtTest, ripgrep, and a running Wayland
session. It briefly opens its own test selector and exercises clicks, busy state,
equal tab widths, and stable hover previews. It never runs the real theme setter.

CI runs backend tests and manifest validation against the exact upstream Omarchy
commit recorded in `.github/workflows/ci.yml`. Native compositor testing remains
a local check. Run it after changing QML or updating the tested shell version.

Use `omarchy plugin add` for normal installation. During development, copy the
three runtime files (`manifest.json`, `ThemeSelector.qml`, `theme_toggle.py`) into
your installed plugin folder, then rescan with `omarchy-shell shell rescanPlugins`.
If the shell retains cached QML, restart it when no active shell app will be interrupted.

Describe observable behavior changes and the checks performed in pull requests.
Report security issues through [SECURITY.md](SECURITY.md). Contributions are
licensed under GPL-3.0-only.
