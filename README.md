# EasyRestore

Linux desktop app for restoring an iPhone or iPad from an IPSW file, without using a terminal.

## Current status

Working today:

- Vendored libimobiledevice pin file and build script
- Helper D-Bus methods with PolicyKit on the system bus
- Full wizard (theme-aware UI, IPSW lookup/download/verify, preflight, restore, diagnostics)
- Packaging drafts: Flatpak, Snap (`raw-usb`), `.deb` skeleton, AppImage notes, udev rules
- Unit tests (`EASYRESTORE_RESTORE_STUB=1` simulates idevicerestore)

Still ahead: publishable store builds, vendored stack inside packages, and per-model DFU verification.

## Run the wizard

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
EASYRESTORE_RESTORE_STUB=1 python -m easyrestore --local-helper
```

Session-bus and `--local-helper` skip PolicyKit. System helper enforces it unless `EASYRESTORE_SKIP_POLKIT=1`.

## Tests

```bash
pytest
```

## Vendor stack

Pins live in `vendor/versions.lock`. Build into `vendor/prefix` (does not use or replace system libimobiledevice):

```bash
# Host packages: build-essential autoconf automake libtool pkg-config
# libssl-dev libusb-1.0-0-dev libcurl4-openssl-dev libzip-dev zlib1g-dev libreadline-dev
./vendor/build.sh
source vendor/env.sh
idevicerestore   # should print usage from vendor/prefix
```

The GUI and helper auto-detect `vendor/prefix` (or `EASYRESTORE_VENDOR_PREFIX`) and prefer those binaries, including `sbin/usbmuxd`.

`idevicerestore` is pinned to commit `405fcd1` (`asr: Increase timeouts for slow devices`). It is built `--without-limera1n`. Udev rules from the build land under `vendor/prefix/lib/udev/rules.d/` (never `/usr` during the vendor build).

## Packaging

See [packaging/README.md](packaging/README.md) for Flatpak, Snap, `.deb`, AppImage, and udev details.

```bash
# Install desktop/dbus/polkit/udev data (and optionally the Python package)
sudo ./packaging/install-data.sh
```
