# Packaging

EasyRestore targets four distribution channels from day one. The GUI is
sandboxed where needed; privileged restore stays in a narrow system helper
authorized by PolicyKit (see the project brief).

| Channel | Path | Status |
|---|---|---|
| AppImage | `packaging/build-appimage.sh` | **Builds** → `dist/EasyRestore-*-x86_64.AppImage` |
| Host USB | `packaging/install-host-support.sh` | udev (+ optional helper) |
| `.deb` | `packaging/debian/` | Skeleton (GUI + helper packages) |
| Flatpak | `packaging/flatpak/io.easyrestore.EasyRestore.yml` | Manifest draft |
| Snap | `packaging/snap/snapcraft.yaml` | Manifest draft (`raw-usb`) |

## Permission model

1. **Host helper (preferred)** — `easyrestore-helper` on the system bus runs
   `idevicerestore` / usbmuxd after PolicyKit. Flatpak talks to it with
   `--system-talk-name=io.easyrestore.Helper`.
2. **udev** — `data/udev/39-easyrestore.rules` tags Apple USB (`05ac`) with
   `uaccess` / `plugdev` so non-root detection works.
3. **Flatpak** — declares `--device=all` for USB visibility (documented in the
   manifest). Restore still prefers the host helper.
4. **Snap** — plugs `raw-usb` (+ `hardware-observe`). Auto-connect must be
   requested from Canonical; until then:
   `sudo snap connect easyrestore:raw-usb`.

## Local data install

```bash
sudo ./packaging/install-data.sh
# optional: PREFIX=$HOME/.local EASYRESTORE_INSTALL_PYTHON=0 ./packaging/install-data.sh
```

## Debian package build (skeleton)

From the repository root:

```bash
ln -sfn packaging/debian debian
# Install build deps, then:
# dpkg-buildpackage -us -uc
```

The debian files assume a future `dh-sequence` install of desktop/dbus/polkit
assets; treat this as the starting layout, not a finished uploadable package.

## Flatpak

```bash
flatpak-builder --user --force-clean build-dir \
  packaging/flatpak/io.easyrestore.EasyRestore.yml
```

Install `easyrestore-helper` on the host first (`.deb` or `install-data.sh`).

## Snap

```bash
cd packaging/snap
snapcraft
sudo snap install --dangerous easyrestore_*.snap
sudo snap connect easyrestore:raw-usb
```
