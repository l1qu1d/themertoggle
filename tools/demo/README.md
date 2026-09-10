# Native demo capture

The video is one continuous 1600 × 1000 Wayland capture. The actual
`ThemeSelector.qml` renders its button, selector, and enlarged hover preview.
Neither the scene nor the video editor overrides popup coordinates.
Original wallpapers in `assets/demo/` demonstrate light and dark palettes.
The top bar is a minimal capture fixture; the setter only changes isolated state.

## Capture environment

Use a separate headless compositor with layer-shell, screencopy, output-management,
and virtual-pointer support. This recording used labwc with
`WLR_BACKENDS=headless`, `WLR_HEADLESS_OUTPUTS=1`, and `WLR_RENDERER=pixman`.
Use a private temporary `XDG_RUNTIME_DIR` (mode 0700), a temporary HOME,
and that compositor's `WAYLAND_DISPLAY`. Do not point this fixture at a personal
desktop. No compositor packages or binaries are bundled here.

1. Set the headless output to 1600 × 1000 at scale 1 with `wlr-randr`.
2. Stage `Scene.qml` as `shell.qml` in a temporary directory. Beside it, symlink
   `/usr/share/omarchy/shell/Commons` and `/usr/share/omarchy/shell/Ui`.
3. Copy the two wallpapers beside `shell.qml` as `light.png` and `dark.png`.
4. Create `plugin/` there with production `ThemeSelector.qml`, `manifest.json`,
   and this directory's recording-only `theme_toggle.py`.
5. In the isolated environment set `DEMO_ISOLATED=1`, then initialize with
   `python3 plugin/theme_toggle.py init light`. Launch Quickshell with
   `QT_QPA_PLATFORM=wayland` and `QT_QUICK_BACKEND=software` against the staging
   directory. The fixture's HOME must be the same as the mock setter's HOME.
6. Generate `pointer.h` and `pointer-protocol.c` from the upstream
   [wlr virtual-pointer protocol](https://gitlab.freedesktop.org/wlroots/wlr-protocols/-/blob/master/unstable/wlr-virtual-pointer-unstable-v1.xml)
   using `wayland-scanner client-header` and `wayland-scanner private-code`.
   Compile `pointer.c` with the generated code and `-lwayland-client`.
7. Set `DEMO_POINTER` to that executable and `DEMO_RECORDER` to `wf-recorder`.
   Run `python3 tools/demo/record.py` from the repo in the isolated environment.
   This replaces the source MP4 and writes the interaction timestamps to JSON.
8. Stop only the capture Quickshell and compositor. Run
   `python3 tools/build-demo.py` and visually review both exports.

The pointer follows actual screen coordinates. If native font sizes, bar size,
or menu geometry change, update the recording coordinates after inspecting the
scene. Camera keyframes live in `tools/build-demo.py`; they must pull back before
the enlarged preview appears so it remains fully visible.
