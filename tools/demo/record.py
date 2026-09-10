"""Record real pointer interactions on the isolated 1600x1000 compositor.

Requires DEMO_POINTER, DEMO_RECORDER and the capture WAYLAND_DISPLAY/runtime.
Never run against a personal desktop. Scene.qml must already be running.
"""
import json
import os
from pathlib import Path
import signal
import subprocess
import time

root = Path(__file__).resolve().parents[2]
assert os.environ.get('DEMO_ISOLATED') == '1', 'Explicit isolated capture environment required'
pointer = subprocess.Popen([os.environ['DEMO_POINTER']], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)


def command(text):
    pointer.stdin.write(text+'\n')
    pointer.stdin.flush()
    assert pointer.stdout.readline().strip() == 'done'


command('move 1300 450 .01')
log = open('/tmp/themertoggle-recorder.log', 'w')
recorder = subprocess.Popen([os.environ['DEMO_RECORDER'], '--no-dmabuf', '-D', '-r', '30',
    '-c', 'libx264', '-p', 'crf=17', '-x', 'yuv420p', '-f', str(root/'assets/source/demo-native.mp4')], stdout=log, stderr=log)
start = time.monotonic()
events = []


def at(second, text):
    time.sleep(max(0, start+second-time.monotonic()))
    events.append({'time': round(time.monotonic()-start, 3), 'input': text})
    command(text)


try:
    at(1, 'move 1545 26 1.4')
    at(4, 'click 272')                 # Left-click: light to dark.
    at(8.5, 'click 273')               # Right-click opens the native menu.
    at(11, 'move 1208 264 1.0')        # Native delayed enlarged preview.
    at(15, 'move 1250 189 .7')
    at(16, 'click 272')                # Light tab.
    at(17, 'move 1208 264 .7')
    at(20, 'move 1380 265 .6')
    at(21, 'click 272')                # Select remembered light favorite.
    at(23, 'move 1555 103 .7')
    at(24, 'click 272')                # Native close control.
    at(25, 'move 1545 26 .7')
    at(27, 'click 272')                # One-click back to remembered dark.
    at(29, 'move 1430 420 .9')
    time.sleep(max(0, start+32-time.monotonic()))
finally:
    recorder.send_signal(signal.SIGINT)
    recorder.wait(timeout=20)
    pointer.stdin.close()
    pointer.wait(timeout=3)
    log.close()
(root/'assets/source/demo-events.json').write_text(json.dumps(events, indent=2)+'\n')
assert recorder.returncode == 0, 'Recording failed; inspect /tmp/themertoggle-recorder.log'
