#!/usr/bin/env bash
set -euo pipefail
project_dir=$(cd -- "$(dirname -- "$0")/.." && pwd)
test_dir=$(mktemp -d)
trap 'rm -rf "$test_dir"' EXIT
ln -s "${OMARCHY_PATH:-/usr/share/omarchy}/shell/Commons" "$test_dir/Commons"
ln -s "${OMARCHY_PATH:-/usr/share/omarchy}/shell/Ui" "$test_dir/Ui"
mkdir "$test_dir/plugin"
cp "$project_dir/ThemeSelector.qml" "$project_dir/manifest.json" "$test_dir/plugin/"
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
current_path = Path(__file__).with_name('current')
current = current_path.read_text() if current_path.exists() else 'night'
if sys.argv[1] == 'list':
    print(json.dumps(dict(themes=[dict(id='day',name='Daylight',mode='light',preview=preview.as_uri()),dict(id='night',name='Night',mode='dark')],current=current,mode='light' if current == 'day' else 'dark',light='day',dark='night')))
elif sys.argv[1] == 'status':
    print(json.dumps({'busy':False}))
else:
    import time
    with (Path(__file__).parent / 'calls').open('a') as f:
        f.write(json.dumps(sys.argv[1:])+'\n')
    time.sleep(0.65)
    selected = sys.argv[2] if sys.argv[1] == 'select' else ('day' if current == 'night' else 'night')
    current_path.write_text(selected)
    print(json.dumps({'event':'ready','selected':selected,'mode':'light' if selected == 'day' else 'dark'}),flush=True)
    time.sleep(1.5) # Slow hooks remain supervised after readiness.
PY
# Build the demo asset before timed UI assertions begin.
python3 "$test_dir/plugin/theme_toggle.py" list > /dev/null
cat > "$test_dir/shell.qml" <<'QML'
import QtQuick
import Quickshell
import QtTest
import qs.Commons
import Quickshell.Io
import "plugin"
ShellRoot {
  PanelWindow {
    implicitWidth: 160
    implicitHeight: 40
    anchors { top: true; left: true }
    exclusionMode: ExclusionMode.Ignore
    ThemeSelector {
    anchors.centerIn: parent
    id: widget
    property int menuCalls: 0
    property int sourceCalls: 0
    function openSource() { sourceCalls++ }
    function toggle() { menuCalls++ } // Verify routing without mapping a popup.
  }
  }
  TestCase { id: testInput; when: false }
  Process {
    id: capture
    command: ["grim", "-g", Quickshell.env("THEME_TEST_REGION") || "0,0 1128x752", Quickshell.env("THEME_TEST_CAPTURE")]
    onExited: function(code) { if (code !== 0) console.error("THEME_TOGGLE_QML_FAIL: capture failed") }
  }
  property int step: 0
  function check(value, message) { if (!value) throw new Error(message) }
  function findIcon(item) {
    if (item.objectName === "centeredThemeIcon") return item
    for (var i = 0; i < item.children.length; i++) {
      var found = findIcon(item.children[i])
      if (found) return found
    }
    return null
  }
  function checkIcon() {
    var icon = findIcon(widget)
    check(icon !== null, "Icon component missing")
    check(Math.abs(icon.paintedCenterY - icon.height / 2) < 0.1, "Icon not vertically centered")
  }
  function checkBounds() {
    var preview = widget.previewItem
    var point = preview.mapToItem(preview.sceneRoot, 0, 0)
    check(point.x >= 0 && point.y >= 0, "Preview crossed top/left screen edge")
    check(point.x + preview.width <= preview.sceneRoot.width + 1, "Preview crossed right screen edge")
    check(point.y + preview.height <= preview.sceneRoot.height + 1, "Preview crossed bottom screen edge")
  }
  Timer {
    id: steps
    interval: 500; repeat: true; running: true
    onTriggered: {
      try {
        if (step === 0) {
          if (widget.catalog.themes.length === 0) return
          check(widget.catalog.themes.length === 2, "Catalog did not load")
          check(widget.choices.length === 1, "Theme grouping failed")
          checkIcon()
          testInput.mouseClick(widget, widget.width / 2, widget.height / 2, Qt.LeftButton)
          check(widget.busy, "Left click did not start toggle")
          widget.press(Qt.LeftButton) // A second press must not enqueue another theme switch.
        } else if (step === 1) {
          check(widget.loading, "Spinner stopped before the setter finished")
          var button = widget.children.find(function(c) { return c.objectName === "themeToggleButton" })
          check(button.textRotation > 0, "Loading icon is not animated")
          checkIcon()
          Color.loadShell("")
          check(!widget.loading && widget.busy, "Spinner waited for post-theme work")
          widget.press(Qt.LeftButton) // Completion work must still be guarded.
        } else if (step === 2) {
          check(!widget.loading && widget.errorText === "", "Spinner stayed on after completion")
          check(widget.finishingActions > 0, "Test did not retain slow post-theme work")
          testInput.mouseClick(widget, widget.width / 2, widget.height / 2, Qt.LeftButton)
          check(widget.busy, "Second stationary-pointer click did not start toggle")
          steps.stop()
          testInput.tryCompare(widget, "busy", false, 3000)
          steps.start()
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
          widget.externalBusy = true // Model a previously sampled lock status.
        } else {
          check(!widget.loading && widget.errorText === "", "Selection failed")
          if (step === 5) { widget.open() }
          else if (step === 7) {
            if (!widget.hoverTheme) {
              var thumbRetry = widget.themeList.itemAtIndex(0).contentItem.children[0]
              testInput.mouseMove(widget.lightButton, widget.lightButton.width / 2, widget.lightButton.height / 2, 100)
              testInput.mouseMove(thumbRetry, thumbRetry.width / 2, thumbRetry.height / 2, 100)
              return
            }
            if (!widget.previewItem.visible) return // Allow asynchronous image decoding and hover delay.
            check(widget.previewItem.QsWindow.window === widget.themeList.QsWindow.window, "Preview created a separate window")
            check(Math.abs(widget.lightButton.width - widget.darkButton.width) < 1, "Light and dark widths differ")
            checkBounds()
            if (Quickshell.env("THEME_TEST_CAPTURE")) {
              var card = widget.previewItem.parent.parent
              capture.command = ["grim", "-g", Math.round(card.x) + "," + Math.round(card.y) + " " + Math.floor(card.width) + "x" + Math.floor(card.height), Quickshell.env("THEME_TEST_CAPTURE")]
              capture.running = true
            }
          }
          else if (step === 6) {
            var row = widget.themeList.itemAtIndex(0)
            var thumb = row ? row.contentItem.children[0] : null
            check(thumb !== null, "Thumbnail item missing, count=" + widget.themeList.count + ",height=" + widget.themeList.height)
            testInput.mouseMove(widget.lightButton, widget.lightButton.width / 2, widget.lightButton.height / 2, 100)
            testInput.mouseMove(thumb, thumb.width / 2, thumb.height / 2, 50)
          } else if (step === 8) {
            check(widget.previewReady && widget.previewItem.visible, "Stable hover preview flickered or disappeared")
            widget.previewItem.parent.parent.x = widget.previewItem.sceneRoot.width - widget.previewItem.parent.parent.width - 6
          } else if (step === 9) {
            checkBounds()
            check(widget.previewItem.onLeft, "Right-edge menu did not put preview on left")
            widget.previewItem.parent.parent.x = 6
            widget.previewItem.parent.parent.y = widget.previewItem.sceneRoot.height - widget.previewItem.parent.parent.height - 6
          } else if (step === 10) {
            checkBounds()
            check(!widget.previewItem.onLeft, "Left-edge menu did not put preview on right")
          } else {
            checkBounds()
            check(widget.titleLabel.text === "ThemerToggle", "Menu title missing")
            check(widget.versionLabel.y >= widget.titleLabel.y + widget.titleLabel.height, "Version is not below title")
            var titleCenter = widget.titleLabel.parent.x + widget.titleLabel.x + widget.titleLabel.width / 2
            check(titleCenter < widget.titleLabel.parent.parent.width / 2, "Title is not beside the logo")
            check(widget.closeButton.fontSize >= 20, "Close glyph is too small")
            check(widget.versionLabel.text === "v1.0.0", "Header version does not match manifest")
            check(widget.versionLabel.x === widget.titleLabel.x, "Title and version are not left aligned")
            check(widget.sourceButton.x + widget.sourceButton.width <= widget.closeButton.x, "Source button overlaps Close")
            check(widget.sourceUrl.toString() === "https://github.com/l1qu1d/themertoggle", "Incorrect source URL")
            testInput.mouseClick(widget.sourceButton, widget.sourceButton.width / 2, widget.sourceButton.height / 2, Qt.LeftButton)
            check(widget.sourceCalls === 1, "Source button did not activate")
            testInput.mouseClick(widget.closeButton, widget.closeButton.width / 2, widget.closeButton.height / 2, Qt.LeftButton)
            check(!widget.opened, "Close button did not close selector")
            console.log("THEME_TOGGLE_QML_PASS")
            Qt.quit()
          }
        }
        step++
      } catch (e) { console.error("THEME_TOGGLE_QML_FAIL: " + e); Qt.quit() }
    }
  }
}
QML
test_status=0
timeout 15 quickshell -p "$test_dir" > "$test_dir/log" 2>&1 || test_status=$?
cat "$test_dir/log"
(( test_status == 0 ))
rg -q 'THEME_TOGGLE_QML_PASS' "$test_dir/log"
if rg -q 'TypeError|ReferenceError|Binding loop|THEME_TOGGLE_QML_FAIL' "$test_dir/log"; then exit 1; fi
python3 - "$test_dir/plugin/calls" <<'PY'
import json, sys
from pathlib import Path
calls=[json.loads(line) for line in Path(sys.argv[1]).read_text().splitlines()]
assert calls == [['toggle'],['toggle'],['select','day']], calls
print('QML catalog, grouping, toggle, busy guard, and selection passed')
PY
