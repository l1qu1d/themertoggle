#!/usr/bin/env python3
"""Small, stateful backend for the Omarchy Quattro theme toggle widget.

The Omarchy theme commands remain the source of truth for applying a theme and
for deciding whether a palette is light or dark.  This module only discovers
the available themes, chooses a deterministic pair, and stores the user's
choice for each mode.
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from typing import Any, Iterator, Mapping, Sequence


DEFAULT_OMARCHY_PATH = Path("/usr/share/omarchy")
DEFAULT_THEME_COLOR = DEFAULT_OMARCHY_PATH / "bin" / "omarchy-theme-color"
PREFERENCE_FILENAME = "preferences.json"
LOCK_FILENAME = "preferences.lock"
MODES = ("light", "dark")


class ThemeError(RuntimeError):
    """An expected, user-facing failure while inspecting or applying themes."""


class ThemeBusy(ThemeError):
    """Another switch is already applying; repeated requests are ignored."""


@dataclass(frozen=True)
class Theme:
    """A discovered theme and the two directories that may contribute it."""

    id: str
    name: str
    mode: str
    packaged_path: Path | None = None
    user_path: Path | None = None

    def source_path(self, relative_name: str) -> Path | None:
        """Return the effective path for a file using theme-set's overlay order."""

        # theme-set copies the packaged theme first and then copies the user
        # theme over it.  A user file therefore wins, including a user
        # colors.toml, while an omitted user file leaves the packaged one in
        # place.  ``is_file`` follows ordinary user-created symlinks just as
        # the shell command's copy operation does.
        if self.user_path is not None:
            candidate = self.user_path / relative_name
            # theme-set deliberately stages a theme cloned from a repository
            # without following symlinked files.  Keep mode classification in
            # step with that rule; a local user theme (including a symlink to
            # a working copy) may still use its own symlinks.
            repo_clone = not self.user_path.is_symlink() and (self.user_path / ".git").is_dir()
            if candidate.is_file() and not (repo_clone and candidate.is_symlink()):
                return candidate
        if self.packaged_path is not None:
            candidate = self.packaged_path / relative_name
            if candidate.is_file():
                return candidate
        return None


def _home() -> Path:
    """Resolve HOME at call time so test fixtures and launched widgets agree."""

    configured = os.environ.get("HOME")
    return Path(configured).expanduser() if configured else Path.home()


def _omarchy_root() -> Path:
    configured = os.environ.get("OMARCHY_PATH")
    return Path(configured).expanduser() if configured else DEFAULT_OMARCHY_PATH


def _packaged_themes_path() -> Path:
    return _omarchy_root() / "themes"


def _user_themes_path() -> Path:
    return _home() / ".config" / "omarchy" / "themes"


def preferences_path() -> Path:
    return _home() / ".local" / "state" / "omarchy-themertoggle" / PREFERENCE_FILENAME


def current_theme_path() -> Path:
    return _home() / ".local" / "state" / "omarchy" / "current" / "theme.name"


def current_theme_directory() -> Path:
    """Return Omarchy's staged effective theme directory, if present."""

    return current_theme_path().parent / "theme"


def _resolver_path() -> Path:
    # The override is useful for isolated tests and for an Omarchy checkout
    # whose helper lives alongside its themes.  In a normal installation the
    # packaged root points directly at the canonical resolver.
    configured = os.environ.get("OMARCHY_THEME_COLOR")
    if configured:
        return Path(configured).expanduser()
    candidate = _omarchy_root() / "bin" / "omarchy-theme-color"
    if candidate.is_file():
        return candidate
    return DEFAULT_THEME_COLOR


def _display_name(theme_id: str) -> str:
    """Match omarchy-theme-list's slug-to-name formatting."""

    return re.sub(
        r"(^|-)([a-z])",
        lambda match: match.group(1) + match.group(2).upper(),
        theme_id,
    ).replace("-", " ")


def _directory_entries(path: Path, *, include_symlinks: bool) -> dict[str, Path]:
    if not path.is_dir():
        return {}

    entries: dict[str, Path] = {}
    try:
        children = path.iterdir()
    except OSError:
        return entries

    for child in children:
        # Omarchy rejects names beginning with a dot when applying a theme.
        # Skipping them here also avoids exposing metadata directories in the
        # widget's menu.  ``Path.is_dir`` follows a user theme symlink.
        if child.name.startswith("."):
            continue
        if child.is_dir() or (include_symlinks and child.is_symlink()):
            entries[child.name] = child
    return entries


def _discover_candidates() -> Iterator[Theme]:
    """Discover packaged and user themes with user files overlaid on stock."""

    packaged = _directory_entries(_packaged_themes_path(), include_symlinks=False)
    user = _directory_entries(_user_themes_path(), include_symlinks=True)

    for theme_id in sorted(set(packaged) | set(user)):
        packaged_path = packaged.get(theme_id)
        user_path = user.get(theme_id)
        # A dangling symlink can be listed by some find implementations but
        # cannot be applied by omarchy-theme-set; omit it from the usable list.
        if user_path is not None and not user_path.is_dir():
            user_path = None
        if packaged_path is None and user_path is None:
            continue
        yield Theme(theme_id, _display_name(theme_id), "", packaged_path, user_path)


def _classify(theme: Theme) -> Theme:
    return Theme(theme.id, theme.name,
                 _resolve_mode(theme.id, theme.packaged_path, theme.user_path),
                 theme.packaged_path, theme.user_path)


def discover_themes() -> list[Theme]:
    """Classify the full catalog only when it is needed for the menu."""
    return [_classify(theme) for theme in _discover_candidates()]


def _resolve_mode(theme_id: str, packaged_path: Path | None, user_path: Path | None) -> str:
    """Resolve a theme mode with the canonical Omarchy color helper.

    The temporary directory is deliberate: ``omarchy-theme-color`` looks for
    ``light.mode`` beside the colors file, so passing an overlaid colors file
    without its effective marker would change the answer for legacy themes.
    """

    effective = Theme(theme_id, _display_name(theme_id), "", packaged_path, user_path)
    resolver = _resolver_path()
    with tempfile.TemporaryDirectory(prefix="theme-toggle-") as temporary:
        directory = Path(temporary)
        colors_path = directory / "colors.toml"
        source_colors = effective.source_path("colors.toml")
        if source_colors is not None:
            try:
                shutil.copyfile(source_colors, colors_path)
            except OSError as exc:
                raise ThemeError(f"could not read colors for theme '{theme_id}': {exc}") from exc

        # Preserve the effective marker even when a user overlay only replaces
        # colors.toml.  The stock light.mode must remain visible in that case.
        source_marker = effective.source_path("light.mode")
        if source_marker is not None:
            try:
                shutil.copyfile(source_marker, directory / "light.mode")
            except OSError as exc:
                raise ThemeError(f"could not read mode marker for theme '{theme_id}': {exc}") from exc

        try:
            completed = subprocess.run(
                [str(resolver), "--file", str(colors_path), "mode"],
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError as exc:
            raise ThemeError(f"could not resolve mode for theme '{theme_id}': {exc}") from exc

    if completed.returncode != 0:
        details = (completed.stderr or completed.stdout or "").strip()
        suffix = f": {details}" if details else ""
        raise ThemeError(f"could not resolve mode for theme '{theme_id}'{suffix}")

    mode = completed.stdout.strip().lower()
    if mode not in MODES:
        raise ThemeError(
            f"could not resolve mode for theme '{theme_id}': "
            f"resolver returned {mode or 'no mode'}"
        )
    return mode


def _read_current_id() -> str | None:
    try:
        value = current_theme_path().read_text(encoding="utf-8").strip()
    except (FileNotFoundError, OSError, UnicodeError):
        return None
    return value or None


def _active_mode(current_id: str | None, current: Theme | None) -> str | None:
    """Resolve the mode of the currently staged theme before source themes.

    Omarchy applies a merged copy into ``current/theme``.  That copy can be
    newer than a user theme directory, and it can remain available briefly
    after the source theme is removed.  Prefer it for the active state while
    retaining the discovered theme as a safe fallback if the staged directory
    is absent or incomplete.
    """

    staged = current_theme_directory()
    if staged.is_dir():
        try:
            return _resolve_mode(current_id or "current", staged, None)
        except ThemeError:
            pass
    return current.mode if current is not None and current.mode in MODES else None


def read_preferences(path: Path | None = None) -> dict[str, str]:
    """Read valid mode selections; malformed or stale state is treated as empty."""

    target = path or preferences_path()
    try:
        with target.open("r", encoding="utf-8") as stream:
            value = json.load(stream)
    except (FileNotFoundError, OSError, json.JSONDecodeError, UnicodeError):
        return {}
    if not isinstance(value, Mapping):
        return {}
    return {
        mode: value[mode]
        for mode in MODES
        if isinstance(value.get(mode), str) and value[mode]
    }


def write_preferences(preferences: Mapping[str, str], path: Path | None = None) -> None:
    """Atomically replace the preference JSON file."""

    target = path or preferences_path()
    parent = target.parent
    parent.mkdir(parents=True, exist_ok=True)
    cleaned = {
        mode: preferences[mode]
        for mode in MODES
        if isinstance(preferences.get(mode), str) and preferences[mode]
    }
    temporary_name: str | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{target.name}.",
            dir=str(parent),
            text=True,
        )
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(cleaned, stream, sort_keys=True, separators=(",", ":"))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, target)
        temporary_name = None
        try:
            directory_descriptor = os.open(parent, os.O_RDONLY)
        except OSError:
            directory_descriptor = -1
        if directory_descriptor >= 0:
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
    finally:
        if temporary_name is not None:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(temporary_name)


@contextlib.contextmanager
def preferences_lock() -> Iterator[None]:
    """Hold one switch lock without queueing repeated clicks or shortcuts."""

    lock_path = preferences_path().with_name(LOCK_FILENAME)
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("a+") as stream:
            try:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ThemeBusy("a theme switch is already running") from None
            try:
                stream.seek(0)
                stream.truncate()
                stream.write(str(os.getpid()) + "\n")
                stream.flush()  # Notify the tray's file watcher after acquiring the lock.
                yield
            finally:
                stream.seek(0)
                stream.truncate()
                stream.flush()
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
    except OSError as exc:
        raise ThemeError(f"could not lock preferences: {exc}") from exc


def is_busy() -> bool:
    """Read the actual lock, so an interrupted switch cannot leave a spinner stuck."""
    try:
        with preferences_path().with_name(LOCK_FILENAME).open("r") as stream:
            try:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return True
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
    except FileNotFoundError:
        pass
    return False


def _theme_by_id(themes: Sequence[Theme], theme_id: str) -> Theme | None:
    for theme in themes:
        if theme.id == theme_id:
            return theme
    return None


def _mode_theme(themes: Sequence[Theme], mode: str) -> Theme | None:
    return next((theme for theme in themes if theme.mode == mode), None)


def _pair(
    themes: Sequence[Theme],
    preferences: Mapping[str, str],
    current: Theme | None,
    current_mode: str | None = None,
) -> dict[str, str | None]:
    """Return remembered choices, with current-mode and sorted fallbacks."""

    pair: dict[str, str | None] = {}
    for mode in MODES:
        remembered = preferences.get(mode)
        remembered_theme = _theme_by_id(themes, remembered) if remembered else None
        if remembered_theme is not None and remembered_theme.mode == mode:
            pair[mode] = remembered_theme.id
            continue
        if current is not None and (current_mode or current.mode) == mode:
            pair[mode] = current.id
            continue
        fallback = _mode_theme(themes, mode)
        pair[mode] = fallback.id if fallback is not None else None
    return pair


IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp")


def preview_for(theme: Theme) -> str:
    """Use Omarchy's preview-first, wallpaper-fallback convention.

    Inspect the user theme before stock, like omarchy-theme-switcher. A file
    revision in the URL invalidates Qt's image cache after an in-place edit.
    Themes with no still image retain the menu's mode-icon placeholder.
    """
    for directory in (theme.user_path, theme.packaged_path):
        if directory is None or not directory.is_dir():
            continue
        try:
            files = sorted(directory.iterdir())
            candidates = [p for ext in IMAGE_EXTENSIONS for p in files
                          if p.name.lower() == "preview" + ext]
            backgrounds = directory / "backgrounds"
            if backgrounds.is_dir():
                candidates += sorted(p for p in backgrounds.iterdir()
                                     if p.suffix.lower() in IMAGE_EXTENSIONS)
            for candidate in candidates:
                if candidate.is_file():
                    stat = candidate.stat()
                    return candidate.absolute().as_uri() + f"?v={stat.st_mtime_ns}-{stat.st_size}"
        except OSError:
            continue
    return ""


def catalog() -> dict[str, Any]:
    """Build the exact JSON object consumed by the Quickshell widget."""

    themes = discover_themes()
    current_id = _read_current_id()
    current = _theme_by_id(themes, current_id) if current_id else None
    active_mode = _active_mode(current_id, current)
    preferences = read_preferences()
    pair = _pair(themes, preferences, current, active_mode)
    return {
        "themes": [
            {"id": theme.id, "name": theme.name, "mode": theme.mode, "preview": preview_for(theme)}
            for theme in themes
        ],
        "current": current.id if current is not None else current_id,
        "mode": active_mode,
        "light": pair["light"],
        "dark": pair["dark"],
    }


def _apply_theme(theme_id: str) -> None:
    """Apply exactly the command used by Omarchy's public CLI."""

    try:
        completed = subprocess.run(
            ["omarchy", "theme", "set", theme_id],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise ThemeError(f"could not apply theme '{theme_id}': {exc}") from exc
    if completed.returncode != 0:
        details = (completed.stderr or completed.stdout or "").strip()
        suffix = f": {details}" if details else ""
        raise ThemeError(f"could not apply theme '{theme_id}'{suffix}")


def select_theme(theme_id: str) -> Theme:
    """Apply and remember one theme only after Omarchy reports success."""

    with preferences_lock():
        theme = _theme_by_id(list(_discover_candidates()), theme_id)
        if theme is None:
            raise ThemeError(f"unknown theme '{theme_id}'")
        theme = _classify(theme)
        _apply_theme(theme.id)
        preferences = read_preferences()
        if theme.mode in MODES:
            preferences[theme.mode] = theme.id
            try:
                write_preferences(preferences)
            except OSError as exc:
                raise ThemeError(f"could not save preferences: {exc}") from exc
        return theme


def toggle_theme() -> Theme:
    """Switch to the remembered opposite mode or its deterministic fallback."""

    with preferences_lock():
        themes = list(_discover_candidates())
        current_id = _read_current_id()
        current = _theme_by_id(themes, current_id) if current_id else None
        # The staged palette is authoritative. Only resolve the source when
        # no usable staged palette exists, and classify candidates on demand.
        active_mode = _active_mode(current_id, None)
        classified: dict[str, Theme] = {}
        def classify(theme: Theme) -> Theme:
            if theme.id not in classified:
                classified[theme.id] = _classify(theme)
            return classified[theme.id]
        if active_mode is None and current is not None:
            active_mode = classify(current).mode
        if active_mode is None:
            shown = current_id or "unknown"
            raise ThemeError(f"cannot determine current theme mode for '{shown}'")
        target_mode = "dark" if active_mode == "light" else "light"
        preferences = read_preferences()
        remembered = preferences.get(target_mode)
        target = _theme_by_id(themes, remembered) if remembered else None
        if target is not None:
            target = classify(target)
        if target is None or target.mode != target_mode:
            target = next((resolved for candidate in themes
                           if (resolved := classify(candidate)).mode == target_mode), None)
        if target is None:
            raise ThemeError(f"no {target_mode} theme is installed")

        # Do not alter either preference until the external command succeeds.
        _apply_theme(target.id)
        if current_id:
            preferences[active_mode] = current_id
        preferences[target_mode] = target.id
        try:
            write_preferences(preferences)
        except OSError as exc:
            raise ThemeError(f"could not save preferences: {exc}") from exc
        return target


def _print_json(value: Mapping[str, Any]) -> None:
    json.dump(value, sys.stdout, sort_keys=False, separators=(",", ":"))
    sys.stdout.write("\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Toggle Omarchy light and dark themes")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status", help="report whether a theme switch is running")
    commands.add_parser("list", help="print the theme catalog as JSON")
    select_parser = commands.add_parser("select", help="apply one theme slug")
    select_parser.add_argument("slug")
    commands.add_parser("toggle", help="apply the remembered opposite-mode theme")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "status":
            _print_json({"busy": is_busy()})
        elif args.command == "list":
            _print_json(catalog())
        else:
            theme = select_theme(args.slug) if args.command == "select" else toggle_theme()
            _print_json({"selected": theme.id, "mode": theme.mode})
    except ThemeBusy:
        _print_json({"busy": True})
    except ThemeError as exc:
        print(f"themertoggle: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
