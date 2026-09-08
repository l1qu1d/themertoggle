# ThemerToggle

Your favorite light and dark themes, one click apart.

A native bar plugin for **Omarchy Quattro**. Left-click to switch between your
remembered light and dark themes. Right-click to choose either theme, with
thumbnails and a larger preview on hover.

![ThemerToggle preview](preview.png)

- Switch immediately, with a rotating icon while Omarchy applies the theme.
- Choose from installed stock themes, custom themes, and user overlays.
- Discover preview images automatically as themes are added, removed, or edited.
- Keep Omarchy's theme templates, app integrations, backgrounds, and hooks.
- Leave keyboard shortcuts entirely up to you.

The screenshot uses original demo palettes to illustrate the selector.

## Install

Requires Omarchy Quattro with its Quickshell shell, Python 3.10 or newer, and the
installed `omarchy` and `omarchy-theme-color` commands. Python uses only its
standard library. This plugin uses Omarchy's native bar, not a separate tray daemon.

```bash
omarchy plugin add https://github.com/l1qu1d/themertoggle.git --enable
```

While this repository is private, cloning requires access through your existing
GitHub credentials. After it becomes public, the same command works without access
being granted. The plugin needs no custom setup script.

Move the icon with the bar settings or:

```bash
omarchy bar move io.github.l1qu1d.themertoggle --section right
```

## Use

Left-click the icon to toggle. Right-click to open the selector. The Light and
Dark tabs have equal widths; selecting a row applies and remembers that theme.
A check marks the current theme and a highlight marks the remembered choice.
Hover over a thumbnail briefly to see a large preview beside the menu.

Switching begins without an artificial delay. Further presses while this plugin
is applying a theme are ignored. An in-progress Omarchy theme change finishes
normally so its app configurations and hooks can complete together.

Mode detection follows Omarchy's own resolver, including custom palettes and
overlays. The active theme is watched for changes made elsewhere. Theme lists
refresh when the selector opens and once a minute as a fallback.

Images are discovered locally: `preview.png`, `.jpg`, `.jpeg`, `.webp`, `.gif`, or
`.bmp`, then the first still image in `backgrounds/`. User theme images take
precedence over stock images. Themes without a still preview show a sun or moon.
The large preview shares the menu surface and appears only after decoding.

Selections are stored in `~/.local/state/omarchy-themertoggle/preferences.json`.
If a remembered theme disappears, the first available theme of that mode is used.
If no matching theme exists, the plugin shows an error without applying one.
The current theme is remembered when toggling away from it.

## Optional command line

```bash
python3 ~/.config/omarchy/plugins/io.github.l1qu1d.themertoggle/theme_toggle.py toggle
python3 ~/.config/omarchy/plugins/io.github.l1qu1d.themertoggle/theme_toggle.py select catppuccin-latte
python3 ~/.config/omarchy/plugins/io.github.l1qu1d.themertoggle/theme_toggle.py list
python3 ~/.config/omarchy/plugins/io.github.l1qu1d.themertoggle/theme_toggle.py status
```

You can bind the toggle command using your own desktop configuration. ThemerToggle
does not install, replace, or remove any keyboard bindings.

## Disable or remove

```bash
omarchy plugin disable io.github.l1qu1d.themertoggle
omarchy plugin remove io.github.l1qu1d.themertoggle --yes
```

Preferences remain for reinstallation. Removing the plugin does not revert your
current Omarchy theme. Remove any shortcut you created yourself if no longer needed.

## Development and security

See [CONTRIBUTING.md](CONTRIBUTING.md) for tests and dependencies,
[SECURITY.md](SECURITY.md) for runtime access and reporting, and
[RELEASING.md](RELEASING.md) for marketplace preparation.

Licensed under [GPL-3.0-only](LICENSE). See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
