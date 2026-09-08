import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui

Panel {
  id: root
  moduleName: "io.github.l1qu1d.themertoggle"
  manageIpc: false
  readonly property alias themeList: themes
  property string backendPath: decodeURIComponent(Qt.resolvedUrl("theme_toggle.py").toString().replace(/^file:\/\//, ""))
  property var catalog: ({themes: [], current: "", mode: "dark", light: "", dark: ""})
  property string errorText: ""
  property bool busy: false
  property bool externalBusy: false
  readonly property alias lightButton: lightTab
  readonly property alias darkButton: darkTab
  readonly property alias previewItem: enlargedPreview
  property bool themeApplied: false
  property bool statusPending: false
  readonly property bool applying: busy || externalBusy
  readonly property bool loading: applying && !themeApplied
  function themeReady() {
    if (applying) { themeApplied = true; refresh() }
  }
  Connections {
    target: Color
    function onThemeShellValuesChanged() { root.themeReady() }
  }
  function checkStatus() {
    if (statusCheck.running) statusPending = true
    else statusCheck.running = true
  }
  property var hoverAnchor: null
  property var hoverTheme: null
  property bool previewReady: false
  function clearPreview() {
    previewDelay.stop()
    previewReady = false
    hoverAnchor = null
    hoverTheme = null
  }
  function previewHover(theme, anchor, hovered) {
    if (!hovered) { if (hoverAnchor === anchor) clearPreview(); return }
    clearPreview()
    if (!theme.preview || loading) return
    hoverTheme = theme
    hoverAnchor = anchor
    previewDelay.restart()
  }
  onOpenedChanged: if (!opened) clearPreview()
  onSelectedModeChanged: clearPreview()
  Timer { id: previewDelay; interval: 300; onTriggered: root.previewReady = true }
  property string selectedMode: "light"
  readonly property var choices: catalog.themes.filter(function(t) { return t.mode === root.selectedMode })
  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  function refresh() {
    if (!listing.running) listing.running = true
  }
  function apply(args) {
    if (applying) return
    clearPreview()
    errorText = ""
    themeApplied = false
    busy = true
    action.command = ["python3", backendPath].concat(args)
    action.running = true
  }
  function press(buttonCode) {
    if (buttonCode === Qt.RightButton) {
      selectedMode = catalog.mode === "light" ? "light" : "dark"
      root.toggle()
      refresh()
    } else if (buttonCode === Qt.LeftButton) {
      apply(["toggle"])
    }
  }
  Component.onCompleted: { refresh(); statusCheck.running = true }
  FileView {
    path: Quickshell.env("HOME") + "/.local/state/omarchy-themertoggle/preferences.lock"
    watchChanges: true
    printErrors: false
    onFileChanged: { reload(); root.checkStatus() }
  }
  Process {
    id: statusCheck
    onExited: {
      if (root.statusPending) {
        root.statusPending = false
        Qt.callLater(root.checkStatus)
      }
    }
    command: ["python3", root.backendPath, "status"]
    stdout: StdioCollector {
      onStreamFinished: {
        try {
          var state = JSON.parse(text)
          if (state.busy === true && !root.applying) root.themeApplied = false
          root.externalBusy = state.busy === true
        }
        catch (e) { root.externalBusy = false }
      }
    }
  }
  Timer {
    interval: 100
    running: root.externalBusy
    repeat: true
    onTriggered: root.checkStatus()
  }
  FileView {
    path: Quickshell.env("HOME") + "/.local/state/omarchy/current/theme.name"
    watchChanges: true
    blockLoading: false
    printErrors: false
    onFileChanged: { reload(); root.refresh() }
  }
  Timer { interval: 60000; running: true; repeat: true; onTriggered: root.refresh() }
  Process {
    id: listing
    command: ["python3", root.backendPath, "list"]
    stdout: StdioCollector {
      onStreamFinished: {
        try { var next = JSON.parse(text); if (JSON.stringify(next) !== JSON.stringify(root.catalog)) root.catalog = next }
        catch (e) { root.errorText = "Could not read themes." }
      }
    }
    stderr: StdioCollector { id: listError }
    onExited: function(code) { if (code !== 0) root.errorText = listError.text.trim() || "Could not read themes." }
  }
  Process {
    id: action
    stderr: StdioCollector { id: actionError }
    onExited: function(code) {
      root.busy = false
      root.externalBusy = false
      root.checkStatus()
      if (code !== 0) {
        root.errorText = actionError.text.trim() || "Theme change failed."
        root.open()
      }
      root.refresh()
    }
  }
  BarIconButton {
    id: button
    objectName: "themeToggleButton"
    anchors.fill: parent
    bar: root.bar
    text: root.loading ? "󰔟" : (root.catalog.mode === "light" ? "󰖙" : "󰖔")
    textRotation: root.loading ? spinner.angle : 0
    QtObject { id: spinner; property real angle: 0 }
    NumberAnimation {
      target: spinner
      property: "angle"
      from: 0; to: 360; duration: 900
      loops: Animation.Infinite
      running: root.loading
    }
    tooltipText: root.loading ? "Applying theme…" : "Toggle light / dark\nRight-click to choose themes"
    onPressed: function(b) { root.press(b) }
  }
  KeyboardPanel {
    id: popup
    anchorItem: button
    owner: root
    bar: root.bar
    open: root.opened
    focusTarget: lightTab
    contentWidth: popup.fittedContentWidth(Style.space(400))
    contentHeight: popup.fittedContentHeight(content.implicitHeight, Style.space(500))
    // Paint within the menu's existing surface: no new popup, focus grab, or
    // compositor animation can interrupt the thumbnail's hover state.
    Rectangle {
      id: enlargedPreview
      z: 100
      readonly property real gap: Style.space(12)
      readonly property Item sceneRoot: {
        var item = parent
        while (item && item.parent) item = item.parent
        return item
      }
      TransformWatcher { id: parentWatcher; a: enlargedPreview.sceneRoot; b: enlargedPreview.parent }
      readonly property point parentOrigin: {
        parentWatcher.transform
        return parent.mapToItem(sceneRoot, 0, 0)
      }
      readonly property real menuLeft: parentOrigin.x - parent.x
      readonly property real menuRight: menuLeft + popup.contentWidth
      readonly property real leftRoom: Math.max(0, menuLeft - gap * 2)
      readonly property real rightRoom: Math.max(0, popup.screenW - menuRight - gap * 2)
      readonly property bool onLeft: leftRoom >= rightRoom
      width: Math.max(0, Math.min(Style.space(620), Math.max(leftRoom, rightRoom), popup.screenW - gap * 2))
      height: Math.max(0, Math.min(Style.space(390), popup.screenH - gap * 2))
      x: Math.max(gap, Math.min(popup.screenW - width - gap,
          onLeft ? menuLeft - width - gap : menuRight + gap)) - parentOrigin.x
      y: {
        parentWatcher.transform
        var point = root.hoverAnchor ? root.hoverAnchor.mapToItem(sceneRoot, 0, 0) : Qt.point(0, 0)
        return Math.max(gap, Math.min(popup.screenH - height - gap, point.y - height / 2)) - parentOrigin.y
      }
      visible: root.opened && root.previewReady && root.hoverTheme !== null && largeImage.status === Image.Ready && width > Style.space(100)
      color: Color.background
      border.color: Color.accent
      border.width: Math.max(1, Style.space(2))
      ColumnLayout {
        anchors.fill: parent
        anchors.margins: Style.space(12)
        Text {
          text: root.hoverTheme ? root.hoverTheme.name : ""
          textFormat: Text.PlainText
          color: Color.foreground
          font.family: Style.font.family
          font.pixelSize: Style.font.body
        }
        Image {
          id: largeImage
          Layout.fillWidth: true
          Layout.fillHeight: true
          source: root.opened && root.hoverTheme ? root.hoverTheme.preview : ""
          sourceSize.width: Math.round(enlargedPreview.width * 2)
          fillMode: Image.PreserveAspectFit
          asynchronous: true
        }
      }
    }
    ColumnLayout {
      id: content
      anchors.fill: parent
      spacing: Style.space(10)
      Keys.onEscapePressed: root.close()
      Text {
        text: "ThemerToggle"
        color: Color.foreground
        font.family: Style.font.family
        font.pixelSize: Style.font.body
        font.bold: true
      }
      Text {
        Layout.fillWidth: true
        text: root.loading ? "Applying theme…" : "Choose a theme to use and remember."
        color: Color.foreground
        font.family: Style.font.family
        font.pixelSize: Style.font.caption
        wrapMode: Text.WordWrap
      }
      RowLayout {
        Layout.fillWidth: true
        Button {
          id: lightTab
          Layout.fillWidth: true
          Layout.preferredWidth: 1
          text: "☀  Light"
          focusable: true
          selected: root.selectedMode === "light"
          onClicked: root.selectedMode = "light"
        }
        Button {
          id: darkTab
          Layout.fillWidth: true
          Layout.preferredWidth: 1
          text: "☾  Dark"
          focusable: true
          selected: root.selectedMode === "dark"
          onClicked: root.selectedMode = "dark"
        }
      }
      ListView {
        id: themes
        Layout.fillWidth: true
        Layout.fillHeight: true
        implicitHeight: Math.min(contentHeight, Style.space(290))
        clip: true
        onMovementStarted: root.clearPreview()
        model: root.choices
        spacing: Style.space(2)
        ScrollBar.vertical: ScrollBar {}
        delegate: ItemDelegate {
          required property var modelData
          width: themes.width
          height: Style.space(78)
          enabled: !root.applying
          highlighted: root.catalog[root.selectedMode] === modelData.id
          text: (root.catalog.current === modelData.id ? "✓  " : "    ") + modelData.name
          onClicked: root.apply(["select", modelData.id])
          contentItem: RowLayout {
            spacing: Style.space(12)
            Rectangle {
              id: thumbnailBox
              objectName: "themeThumbnail-" + modelData.id
              Component.onDestruction: if (root.hoverAnchor === thumbnailBox) root.clearPreview()
              MouseArea {
                anchors.fill: parent
                z: 1
                hoverEnabled: true
                acceptedButtons: Qt.NoButton
                onEntered: root.previewHover(modelData, thumbnailBox, true)
                onExited: root.previewHover(modelData, thumbnailBox, false)
              }
              Layout.preferredWidth: Style.space(104)
              Layout.preferredHeight: Style.space(60)
              color: Qt.alpha(Color.foreground, 0.08)
              radius: Style.space(4)
              clip: true
              Image {
                id: thumbnail
                anchors.fill: parent
                source: root.opened ? (modelData.preview || "") : ""
                sourceSize.width: Math.round(Style.space(208))
                sourceSize.height: Math.round(Style.space(120))
                fillMode: Image.PreserveAspectCrop
                asynchronous: true
              }
              Text {
                anchors.centerIn: parent
                visible: thumbnail.status !== Image.Ready
                text: modelData.mode === "light" ? "☀" : "☾"
                color: Color.foreground
                font.pixelSize: Style.space(24)
              }
            }
            Text {
              Layout.fillWidth: true
              text: (root.catalog.current === modelData.id ? "✓  " : "") + modelData.name
              textFormat: Text.PlainText
              color: Color.foreground
              font.family: Style.font.family
              font.pixelSize: Style.font.body
              elide: Text.ElideRight
              verticalAlignment: Text.AlignVCenter
            }
          }
          background: Rectangle {
            radius: Style.space(4)
            color: parent.highlighted || parent.hovered || parent.activeFocus ? Qt.alpha(Color.accent, 0.2) : "transparent"
          }
        }
      }
      Text {
        visible: root.choices.length === 0
        text: "No " + root.selectedMode + " themes installed."
        color: Color.foreground
        font.pixelSize: Style.font.body
      }
      Text {
        Layout.fillWidth: true
        visible: root.errorText !== ""
        text: root.errorText
        textFormat: Text.PlainText
        color: Color.urgent
        font.pixelSize: Style.font.caption
        wrapMode: Text.WrapAnywhere
      }
    }
  }
}
