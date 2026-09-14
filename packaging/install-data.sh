#!/usr/bin/env bash
# Install EasyRestore data files and Python package for local development.
# Does not build the vendored C stack — run ./vendor/build.sh separately.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PREFIX="${PREFIX:-/usr/local}"
DESTDIR="${DESTDIR:-}"

install_file() {
  local src="$1" dest="$2" mode="${3:-644}"
  install -d "${DESTDIR}$(dirname "${dest}")"
  install -m "${mode}" "${src}" "${DESTDIR}${dest}"
  echo "installed ${dest}"
}

install_file "${ROOT}/data/desktop/io.easyrestore.EasyRestore.desktop" \
  "${PREFIX}/share/applications/io.easyrestore.EasyRestore.desktop"
install_file "${ROOT}/data/metainfo/io.easyrestore.EasyRestore.metainfo.xml" \
  "${PREFIX}/share/metainfo/io.easyrestore.EasyRestore.metainfo.xml"
install_file "${ROOT}/data/dbus/io.easyrestore.Helper.conf" \
  "${PREFIX}/share/dbus-1/system.d/io.easyrestore.Helper.conf"
install_file "${ROOT}/data/dbus/io.easyrestore.Helper.service" \
  "${PREFIX}/share/dbus-1/system-services/io.easyrestore.Helper.service"
install_file "${ROOT}/data/polkit/io.easyrestore.policy" \
  "${PREFIX}/share/polkit-1/actions/io.easyrestore.policy"
install_file "${ROOT}/data/systemd/easyrestore-helper.service" \
  "${PREFIX}/lib/systemd/system/easyrestore-helper.service"
install_file "${ROOT}/data/udev/39-easyrestore.rules" \
  "${PREFIX}/lib/udev/rules.d/39-easyrestore.rules"
install_file "${ROOT}/data/icons/io.easyrestore.EasyRestore.svg" \
  "${PREFIX}/share/icons/hicolor/scalable/apps/io.easyrestore.EasyRestore.svg"

for size in 16 24 32 48 64 128 256 512; do
  install_file \
    "${ROOT}/data/icons/hicolor/${size}x${size}/apps/io.easyrestore.EasyRestore.png" \
    "${PREFIX}/share/icons/hicolor/${size}x${size}/apps/io.easyrestore.EasyRestore.png"
done

if [[ "${EASYRESTORE_INSTALL_PYTHON:-1}" == "1" ]]; then
  python3 -m pip install --prefix="${DESTDIR}${PREFIX}" "${ROOT}"
fi

if command -v gtk-update-icon-cache >/dev/null 2>&1 && [[ -z "${DESTDIR}" ]]; then
  gtk-update-icon-cache -f "${DESTDIR}${PREFIX}/share/icons/hicolor" 2>/dev/null || true
fi

if command -v udevadm >/dev/null 2>&1 && [[ -z "${DESTDIR}" ]]; then
  udevadm control --reload-rules || true
  udevadm trigger --subsystem-match=usb || true
fi

echo "Done. Prefix=${PREFIX}. Build the vendor stack with ./vendor/build.sh if needed."
echo "Add your user to the plugdev group if Apple USB nodes are not accessible."
