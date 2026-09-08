import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).parents[1]
sys.path.insert(0, str(PROJECT))
spec = importlib.util.spec_from_file_location('theme_toggle', PROJECT / 'theme_toggle.py')
backend = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = backend
spec.loader.exec_module(backend)

class ThemeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.stock = self.home / 'omarchy'
        self.bin = self.home / 'bin'
        self.bin.mkdir()
        self.env = {'HOME': str(self.home), 'OMARCHY_PATH': str(self.stock),
                    'OMARCHY_THEME_COLOR': os.environ.get('OMARCHY_THEME_COLOR', '/usr/share/omarchy/bin/omarchy-theme-color'),
                    'PATH': str(self.bin) + ':' + os.environ['PATH']}
        self.patch = patch.dict(os.environ, self.env)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        fake = self.bin / 'omarchy'
        fake.write_text('''#!/usr/bin/env python3
import json,os,sys
from pathlib import Path
h=Path.home()
with (h/'calls').open('a') as f: f.write(json.dumps(sys.argv[1:])+'\\n')
if (h/'fail').exists():
    print('test setter failure',file=sys.stderr)
    sys.exit(1)
(h/'.local/state/omarchy/current/theme.name').write_text(sys.argv[3])
''')
        fake.chmod(0o755)
        self.theme('day', 'mode = "light"')
        self.theme('night', 'mode = "dark"')
        backend.current_theme_path().parent.mkdir(parents=True)
        backend.current_theme_path().write_text('night')

    def theme(self, name, colors, user=False, marker=False):
        base = self.home / '.config/omarchy/themes' if user else self.stock / 'themes'
        p = base / name
        p.mkdir(parents=True, exist_ok=True)
        if colors is not None:
            (p / 'colors.toml').write_text(colors+'\n')
        if marker:
            (p / 'light.mode').touch()
        return p

    def calls(self):
        p = self.home / 'calls'
        return [json.loads(s) for s in p.read_text().splitlines()] if p.exists() else []

    def test_catalog_read_only_and_overlay_modes(self):
        self.theme('day', None, user=True)
        self.theme('legacy', 'background = "#000000"', marker=True)
        self.theme('legacy', 'background = "#111111"', user=True)
        self.theme('bright', 'background = "#ffffff"', user=True)
        self.theme('type', 'theme_type = "light"', user=True)
        self.theme('explicit', 'mode = "dark"', marker=True)
        c = backend.catalog()
        modes = {t['id']: t['mode'] for t in c['themes']}
        self.assertEqual(modes, dict(day='light', night='dark', legacy='light', bright='light', type='light', explicit='dark'))
        self.assertFalse(backend.preferences_path().parent.exists())
        self.assertEqual(c['current'], 'night')
        self.assertEqual(c['mode'], 'dark')

    def test_toggle_round_trip_remembers_pair(self):
        self.assertEqual(backend.toggle_theme().id, 'day')
        self.assertEqual(backend.toggle_theme().id, 'night')
        self.assertEqual(backend.read_preferences(), dict(light='day', dark='night'))
        self.assertEqual(self.calls(), [['theme','set','day'], ['theme','set','night']])

    def test_select_remembers_and_toggle_uses_selection(self):
        self.theme('other-light', 'mode = "light"', user=True)
        backend.select_theme('other-light')
        backend.toggle_theme()
        self.assertEqual(backend.toggle_theme().id, 'other-light')

    def test_failed_apply_keeps_preferences(self):
        backend.write_preferences(dict(light='day', dark='night'))
        before = backend.preferences_path().read_bytes()
        (self.home / 'fail').touch()
        with self.assertRaisesRegex(backend.ThemeError, 'test setter failure'):
            backend.select_theme('day')
        self.assertEqual(backend.preferences_path().read_bytes(), before)
        with self.assertRaises(backend.ThemeError):
            backend.toggle_theme()
        self.assertEqual(backend.preferences_path().read_bytes(), before)

    def test_removed_choice_falls_back(self):
        backend.write_preferences(dict(light='deleted'))
        self.assertEqual(backend.toggle_theme().id, 'day')

    def test_unknown_choice_never_runs_setter(self):
        with self.assertRaises(backend.ThemeError):
            backend.select_theme('../bad; touch injected')
        self.assertEqual(self.calls(), [])

    def test_no_opposite_mode(self):
        import shutil
        shutil.rmtree(self.stock / 'themes/day')
        with self.assertRaisesRegex(backend.ThemeError, 'no light'):
            backend.toggle_theme()
        self.assertEqual(self.calls(), [])

    def test_dangling_symlink_is_omitted(self):
        p = self.home / '.config/omarchy/themes'
        p.mkdir(parents=True)
        (p / 'missing').symlink_to(self.home / 'absent')
        self.assertNotIn('missing', [t.id for t in backend.discover_themes()])

    def test_clone_symlink_does_not_override_stock(self):
        p = self.theme('night', None, user=True)
        (p / '.git').mkdir()
        (p / 'colors.toml').symlink_to(self.stock / 'themes/day/colors.toml')
        self.assertEqual({t.id:t.mode for t in backend.discover_themes()}['night'], 'dark')

    def test_staged_mode_wins_after_source_edit(self):
        staged = backend.current_theme_directory()
        staged.mkdir()
        (staged / 'colors.toml').write_text('mode = "light"\n')
        self.assertEqual(backend.catalog()['mode'], 'light')
        self.assertEqual(backend.toggle_theme().mode, 'dark')

    def test_cli_json_and_failure(self):
        p = subprocess.run([sys.executable, str(PROJECT/'theme_toggle.py'), 'list'], text=True, capture_output=True)
        self.assertEqual(p.returncode, 0)
        self.assertEqual(json.loads(p.stdout)['mode'], 'dark')
        p = subprocess.run([sys.executable, str(PROJECT/'theme_toggle.py'), 'select', 'missing'], text=True, capture_output=True)
        self.assertEqual(p.returncode, 1)
        self.assertIn('unknown theme', p.stderr)

    def test_preview_priority_and_live_changes(self):
        stock = self.stock / 'themes/day'
        (stock / 'preview.png').write_bytes(b'stock preview')
        first = next(t for t in backend.catalog()['themes'] if t['id'] == 'day')['preview']
        self.assertTrue(first.startswith((stock / 'preview.png').as_uri()))
        user = self.theme('day', None, user=True)
        (user / 'backgrounds').mkdir()
        wallpaper = user / 'backgrounds/a space # image.jpg'
        wallpaper.write_bytes(b'user wallpaper')
        preview = next(t for t in backend.catalog()['themes'] if t['id'] == 'day')['preview']
        self.assertTrue(preview.startswith(wallpaper.as_uri()))
        self.assertIn('%23', preview)
        custom = user / 'preview.webp'
        custom.write_bytes(b'custom preview')
        revised = next(t for t in backend.catalog()['themes'] if t['id'] == 'day')['preview']
        self.assertTrue(revised.startswith(custom.as_uri()))
        custom.write_bytes(b'edited custom preview with more bytes')
        self.assertNotEqual(revised, next(t for t in backend.catalog()['themes'] if t['id'] == 'day')['preview'])
        custom.unlink()
        wallpaper.unlink()
        self.assertEqual(first, next(t for t in backend.catalog()['themes'] if t['id'] == 'day')['preview'])

    def test_preview_missing_is_empty(self):
        self.assertTrue(all(t['preview'] == '' for t in backend.catalog()['themes']))

    def test_added_removed_theme_updates_catalog(self):
        import shutil
        p = self.theme('new-theme', 'mode = "dark"', user=True)
        (p/'PREVIEW.PNG').write_bytes(b'preview')
        self.assertTrue(next(t for t in backend.catalog()['themes'] if t['id'] == 'new-theme')['preview'])
        shutil.rmtree(p)
        self.assertNotIn('new-theme', [t['id'] for t in backend.catalog()['themes']])

    def test_busy_status_and_lock_release_on_failure(self):
        self.assertFalse(backend.is_busy())
        with self.assertRaises(RuntimeError):
            with backend.preferences_lock():
                self.assertTrue(backend.is_busy())
                result = subprocess.run([sys.executable, str(PROJECT/'theme_toggle.py'), 'status'], text=True, capture_output=True)
                self.assertTrue(json.loads(result.stdout)['busy'])
                raise RuntimeError('interrupted operation')
        self.assertFalse(backend.is_busy())

    def test_busy_requests_return_without_queueing_or_applying(self):
        with backend.preferences_lock():
            for args in (['toggle'], ['select', 'day']):
                result = subprocess.run([sys.executable, str(PROJECT/'theme_toggle.py'), *args],
                                        capture_output=True, text=True, timeout=1)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout), {'busy': True})
            self.assertEqual(self.calls(), [])
        self.assertEqual(self.calls(), [])

    def test_running_apply_is_not_interrupted(self):
        import time
        fake = self.bin / 'omarchy'
        fake.write_text(fake.read_text().replace("if (h/'fail').exists():",
            "import time\nwhile not (h/'release').exists(): time.sleep(.01)\nif (h/'fail').exists():"))
        first = subprocess.Popen([sys.executable, str(PROJECT/'theme_toggle.py'), 'toggle'],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 3
            while not self.calls() and time.monotonic() < deadline:
                time.sleep(.01)
            self.assertEqual(self.calls(), [['theme','set','day']])
            second = subprocess.run([sys.executable, str(PROJECT/'theme_toggle.py'), 'toggle'],
                                    capture_output=True, text=True, timeout=1)
            self.assertEqual(json.loads(second.stdout), {'busy': True})
            self.assertIsNone(first.poll())
            (self.home/'release').touch()
            output, errors = first.communicate(timeout=3)
            self.assertEqual(first.returncode, 0, errors)
            self.assertEqual(json.loads(output)['selected'], 'day')
            self.assertEqual(self.calls(), [['theme','set','day']])
        finally:
            if first.poll() is None:
                first.kill()
                first.wait()

    def test_select_only_classifies_selected_theme(self):
        for i in range(20):
            self.theme(f'extra-{i}', 'mode = "dark"')
        with patch.object(backend, '_resolve_mode', wraps=backend._resolve_mode) as resolve:
            backend.select_theme('day')
        self.assertEqual(resolve.call_count, 1)

    def test_remembered_toggle_only_classifies_active_and_target(self):
        for i in range(20):
            self.theme(f'extra-{i}', 'mode = "dark"')
        backend.write_preferences({'light': 'day', 'dark': 'night'})
        with patch.object(backend, '_resolve_mode', wraps=backend._resolve_mode) as resolve:
            backend.toggle_theme()
        self.assertEqual(resolve.call_count, 2)

    def test_changed_remembered_mode_uses_fallback(self):
        self.theme('other', 'mode = "dark"')
        backend.write_preferences({'light': 'other'})
        self.assertEqual(backend.toggle_theme().id, 'day')
