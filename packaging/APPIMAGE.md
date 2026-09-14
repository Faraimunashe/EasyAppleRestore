# EasyRestore — AppImage

AppImage is the primary “download and run” artifact while Flatpak/Snap reviews
are pending.

## Build

```bash
./vendor/build.sh          # once, if vendor/prefix is missing
./packaging/build-appimage.sh
```

Artifacts land in `dist/`:

| File | Purpose |
|---|---|
| `EasyRestore-<ver>-x86_64.AppImage` | Primary tester download |
| `EasyRestore-<ver>-x86_64.AppDir.tar.gz` | Same tree without the AppImage wrapper |
| `README-TESTING.txt` | Short tester instructions |

The build embeds a trimmed PySide6, `dbus-next`, and the vendored
libimobiledevice prefix under `usr/lib/easyrestore/`.

## Host USB support

An AppImage cannot install udev rules. For real-device restores:

```bash
sudo ./packaging/install-host-support.sh              # udev only
sudo ./packaging/install-host-support.sh --with-helper # + D-Bus/PolicyKit helper
```

Without the helper, the GUI falls back to in-process restores (`LocalHelperClient`).

## Layout

```
EasyRestore.AppDir/
  AppRun
  io.easyrestore.EasyRestore.desktop
  io.easyrestore.EasyRestore.png
  usr/
    bin/easyrestore
    lib/easyrestore/
      vendor/     # EASYRESTORE_VENDOR_PREFIX
      venv/       # Python + PySide6 + easyrestore
    share/…
```
