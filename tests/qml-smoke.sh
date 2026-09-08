#!/usr/bin/env bash
set -euo pipefail
project_dir=$(cd -- "$(dirname -- "$0")/.." && pwd)
test_dir=$(mktemp -d)
trap 'rm -rf "$test_dir"' EXIT
ln -s "${OMARCHY_PATH:-/usr/share/omarchy}/shell/Commons" "$test_dir/Commons"
ln -s "${OMARCHY_PATH:-/usr/share/omarchy}/shell/Ui" "$test_dir/Ui"
mkdir "$test_dir/plugin"
cp "$project_dir/ThemeSelector.qml" "$test_dir/plugin/"
cat > "$test_dir/plugin/theme_toggle.py" <<'PY'
import json
import sys
from pathlib import Path
# Original demo palette fixture, generated without external image dependencies.
import struct, zlib
preview = Path(__file__).with_name('demo.png')
if not preview.exists():
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    rects = [(40,40,760,460,(226,217,199)), (65,65,735,110,(88,120,107)),
             (65,135,265,435,(210,159,110)), (290,135,735,275,(128,156,136)),
             (290,300,500,435,(101,121,145)), (525,300,735,435,(185,137,128))]
    rows = []
    for y in range(500):
        row = bytearray([0])
        for x in range(800):
            color = (243,239,231)
            for x1,y1,x2,y2,c in rects:
                if x1 <= x < x2 and y1 <= y < y2: color = c
            row.extend(color)
        rows.append(row)
    preview.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB',800,500,8,2,0,0,0)) + chunk(b'IDAT', zlib.compress(b''.join(rows))) + chunk(b'IEND', b''))
if sys.argv[1] == 'list':
    print(json.dumps(dict(themes=[dict(id='day',name='Daylight',mode='light',preview=preview.as_uri()),dict(id='night',name='Night',mode='dark')],current='night',mode='dark',light='day',dark='night')))
elif sys.argv[1] == 'status':
    print(json.dumps({'busy':False}))
else:
    import time
    time.sleep(0.65)
    with (Path(__file__).parent / 'calls').open('a') as f:
        f.write(json.dumps(sys.argv[1:])+'\n')
PY
# Build the demo asset before timed UI assertions begin.
python3 "$test_dir/plugin/theme_toggle.py" list > /dev/null
cat > "$test_dir/shell.qml" <<'QML'
import QtQuick
import Quickshell
import QtTest
import Quickshell.Io
import "plugin"
ShellRoot {
  ThemeSelector {
    id: widget
    property int menuCalls: 0
    function toggle() { menuCalls++ } // Verify routing without mapping a popup.
  }
  TestCase { id: testInput; when: false }
  Process {
    id: capture
    command: ["grim", "-g", Quickshell.env("THEME_TEST_REGION") || "0,0 1128x752", Quickshell.env("THEME_TEST_CAPTURE")]
    onExited: { widget.close(); console.log("THEME_TOGGLE_QML_PASS"); Qt.quit() }
  }
  property int step: 0
  function check(value, message) { if (!value) throw new Error(message) }
  Timer {
    id: steps
    interval: 500; repeat: true; running: true
    onTriggered: {
      try {
        if (step === 0) {
          if (widget.catalog.themes.length === 0) return
          check(widget.catalog.themes.length === 2, "Catalog did not load")
          check(widget.choices.length === 1, "Theme grouping failed")
          widget.children.find(function(c) { return c.objectName === "themeToggleButton" }).triggerPress(Qt.LeftButton)
          check(widget.busy, "Left click did not start toggle")
          widget.press(Qt.LeftButton) // A second press must not enqueue another theme switch.
        } else if (step === 1) {
          check(widget.loading, "Spinner stopped before the setter finished")
          var button = widget.children.find(function(c) { return c.objectName === "themeToggleButton" })
          check(button.textRotation > 0, "Loading icon is not animated")
        } else if (step === 2) {
          check(!widget.loading && widget.errorText === "", "Spinner stayed on after completion")
          widget.children.find(function(c) { return c.objectName === "themeToggleButton" }).triggerPress(Qt.RightButton)
          check(widget.menuCalls === 1 && widget.selectedMode === "dark", "Right-click menu route failed")
          widget.previewHover({name: "Day", preview: "file:///fake.png"}, widget, true)
          check(!widget.previewReady, "Preview did not wait for hover delay")
        } else if (step === 3) {
          check(widget.previewReady, "Hover preview did not open")
          widget.previewHover({}, widget, false)
          check(!widget.previewReady && widget.hoverTheme === null, "Preview did not close on leave")
          widget.previewHover({name: "Day", preview: "file:///fake.png"}, widget, true)
          widget.selectedMode = "light"
          check(widget.hoverTheme === null, "Tab change left stale preview")
          widget.apply(["select", "day"])
        } else if (step === 4) {
          check(widget.loading, "Selection spinner missing")
        } else {
          check(!widget.loading && widget.errorText === "", "Selection failed")
          if (step === 5) { widget.open() }
          else if (step === 7) {
            check(widget.previewItem.visible, "Decoded preview did not become visible: ready=" + widget.previewReady + ", hover=" + JSON.stringify(widget.hoverTheme))
            check(widget.previewItem.QsWindow.window === widget.themeList.QsWindow.window, "Preview created a separate window")
            check(Math.abs(widget.lightButton.width - widget.darkButton.width) < 1, "Light and dark widths differ")
          }
          else if (step === 6) {
            var row = widget.themeList.itemAtIndex(0)
            var thumb = row ? row.contentItem.children[0] : null
            check(thumb !== null, "Thumbnail item missing, count=" + widget.themeList.count + ",height=" + widget.themeList.height)
            testInput.mouseMove(widget.lightButton, widget.lightButton.width / 2, widget.lightButton.height / 2, 100)
            testInput.mouseMove(thumb, thumb.width / 2, thumb.height / 2, 50)
          } else {
            check(widget.previewReady && widget.previewItem.visible, "Stable hover preview flickered or disappeared")
            if (Quickshell.env("THEME_TEST_CAPTURE")) {
              steps.stop()
              capture.running = true
            } else {
              widget.close()
              console.log("THEME_TOGGLE_QML_PASS")
              Qt.quit()
            }
          }
        }
        step++
      } catch (e) { console.error("THEME_TOGGLE_QML_FAIL: " + e); Qt.quit() }
    }
  }
}
QML
timeout 10 quickshell -p "$test_dir" > "$test_dir/log" 2>&1
cat "$test_dir/log"
rg -q 'THEME_TOGGLE_QML_PASS' "$test_dir/log"
if rg -q 'TypeError|ReferenceError|Binding loop|THEME_TOGGLE_QML_FAIL' "$test_dir/log"; then exit 1; fi
python3 - "$test_dir/plugin/calls" <<'PY'
import json, sys
from pathlib import Path
calls=[json.loads(line) for line in Path(sys.argv[1]).read_text().splitlines()]
assert calls == [['toggle'],['select','day']], calls
print('QML catalog, grouping, toggle, busy guard, and selection passed')
PY
