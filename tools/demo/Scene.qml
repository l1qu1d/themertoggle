import QtQuick
import QtTest
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import qs.Commons
import "plugin"

ShellRoot {
  id: scene

  // This scene runs only in the isolated recording compositor and HOME.
  // The plugin and its popup retain their production positioning and input.
  TestCase { id: input; when: false }

  FileView {
    path: Quickshell.env("HOME") + "/.local/state/omarchy/current/theme/colors.toml"
    watchChanges: true
    onLoaded: Color.loadColors(text())
    onFileChanged: reload()
  }
  FileView {
    path: Quickshell.env("HOME") + "/.local/state/omarchy/current/theme/shell.toml"
    watchChanges: true
    onLoaded: Color.loadShell(text())
    onFileChanged: reload()
  }

  QtObject {
    id: fixtureBar
    property string position: "top"
    property bool vertical: false
    property int barSize: 52
    property string fontFamily: Style.font.family
    property color barForeground: Color.bar.text
    property color urgent: Color.urgent
    property bool foregroundAnimationEnabled: true
    property var activePopout: null
    property var clickTargets: []
    function requestPopout(item) { activePopout = item }
    function releasePopout(item) { if (activePopout === item) activePopout = null }
    function showTooltip(item, text) {}
    function hideTooltip(item) {}
    function registerClickTarget(item) { clickTargets = clickTargets.concat([item]) }
    function unregisterClickTarget(item) { clickTargets = clickTargets.filter(function(t) { return t !== item }) }
  }

  PanelWindow {
    id: desktop
    screen: Quickshell.screens[0]
    anchors { top: true; bottom: true; left: true; right: true }
    exclusionMode: ExclusionMode.Ignore
    WlrLayershell.layer: WlrLayer.Background
    color: Color.background
    Image {
      anchors.fill: parent
      source: widget.catalog.mode === "light" ? "light.png" : "dark.png"
      fillMode: Image.PreserveAspectCrop
    }
  }

  PanelWindow {
    id: barWindow
    screen: Quickshell.screens[0]
    anchors { top: true; left: true; right: true }
    implicitHeight: 52
    exclusionMode: ExclusionMode.Normal
    WlrLayershell.layer: WlrLayer.Top
    color: Color.bar.background

    Text {
      anchors.centerIn: parent
      text: "10:24"
      color: Color.bar.text
      font.family: Style.font.family
      font.pixelSize: 16
    }
    Text {
      anchors.right: widget.left
      anchors.rightMargin: 22
      anchors.verticalCenter: parent.verticalCenter
      text: "󰤨   󰁹"
      color: Color.bar.text
      font.family: Style.font.family
      font.pixelSize: 19
    }
    ThemeSelector {
      id: widget
      x: parent.width - 70
      anchors.verticalCenter: parent.verticalCenter
      bar: fixtureBar
    }
  }

  function click(item, button) {
    if (!item) { console.error("DEMO: missing click target"); return }
    input.mouseMove(item, item.width / 2, item.height / 2)
    input.mouseClick(item, item.width / 2, item.height / 2, button)
  }

  IpcHandler {
    target: "demo"
    function clickIcon(): void { scene.click(widget, Qt.LeftButton) }
    function rightClickIcon(): void { scene.click(widget, Qt.RightButton) }
    function hoverFirst(): void {
      var row = widget.themeList.itemAtIndex(0)
      var thumbnail = row ? row.contentItem.children[0] : null
      if (thumbnail) input.mouseMove(thumbnail, thumbnail.width / 2, thumbnail.height / 2)
    }
    function clickDark(): void { scene.click(widget.darkButton, Qt.LeftButton) }
    function selectFirst(): void { scene.click(widget.themeList.itemAtIndex(0), Qt.LeftButton) }
    function closeMenu(): void { scene.click(widget.closeButton, Qt.LeftButton) }
    function status(): void {
      var popupWindow = widget.themeList.QsWindow.window
      var point = popupWindow ? widget.themeList.mapToItem(widget.previewItem.sceneRoot, 0, 0) : Qt.point(0, 0)
      console.log("DEMO_STATUS " + JSON.stringify({
        screenWidth: desktop.width, screenHeight: desktop.height,
        iconX: widget.x, iconY: widget.y, iconWidth: widget.width, iconHeight: widget.height,
        opened: widget.opened, mode: widget.catalog.mode,
        listX: point.x, listY: point.y, listWidth: widget.themeList.width,
        listHeight: widget.themeList.height, previewVisible: widget.previewItem.visible
      }))
    }
  }
}
