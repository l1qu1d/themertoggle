"""Recording-only setter. All state stays under the isolated capture HOME."""
import json
import os
from pathlib import Path
import sys
import time

assert os.environ.get('DEMO_ISOLATED') == '1', 'Recording-only backend requires an isolated capture environment'
home = Path(os.environ['HOME'])
state = home / '.local/state/omarchy/current'
state.mkdir(parents=True, exist_ok=True)
theme = state / 'theme'
theme.mkdir(exist_ok=True)
current = state / 'theme.name'
mode = current.read_text().strip() if current.exists() else 'light'
root = Path(__file__).resolve().parent.parent
command = sys.argv[1]
if command == 'status':
    print(json.dumps({'busy': False}))
elif command == 'list':
    print(json.dumps(dict(current=mode, mode=mode, light='light', dark='dark', themes=[
        dict(id=m, name=n, mode=m, preview=(root / (m+'.png')).as_uri())
        for m, n in [('light', 'Daylight'), ('dark', 'Midnight')]])))
else:
    selected = sys.argv[2] if command in ('select', 'init') else ('dark' if mode == 'light' else 'light')
    if command != 'init':
        time.sleep(.35)
    light = selected == 'light'
    bg, fg, accent = ('#f6f1e7', '#243d43', '#537d72') if light else ('#101c2b', '#d9e4ed', '#86afa9')
    (theme / 'colors.toml').write_text(f'background = "{bg}"\nforeground = "{fg}"\naccent = "{accent}"\n')
    (theme / 'shell.toml').write_text('[font]\nfamily = "CaskaydiaMono Nerd Font"\nbase-size = 14\n')
    current.write_text(selected)
    print(json.dumps({'event': 'ready', 'selected': selected, 'mode': selected}), flush=True)
