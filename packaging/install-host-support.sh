#!/usr/bin/env bash
# Install host-side pieces the AppImage cannot provide: udev rules, and
# optionally the D-Bus/PolicyKit helper for privileged restores.
#
# Usage:
#   sudo ./packaging/install-host-support.sh              # udev only
#   sudo ./packaging/install-host-support.sh --with-helper
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PREFIX="${PREFIX:-/usr/local}"
DESTDIR="${DESTDIR:-}"
WITH_HELPER=0

for arg in "$@"; do
  case "${arg}" in
    --with-helper) WITH_HELPER=1 ;;
    --prefix=*) PREFIX="${arg#*=}" ;;
    -h|--help)
      sed -n '1,12p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown option: ${arg}" >&2
      exit 2
      ;;
  esac
done

if [[ "$(id -u)" -ne 0 && -z "${DESTDIR}" ]]; then
  echo "Run as root (sudo) to install into ${PREFIX}" >&2
  exit 1
fi

install_file() {
  local src="$1" dest="$2" mode="${3:-644}"
  install -d "${DESTDIR}$(dirname "${dest}")"
  install -m "${mode}" "${src}" "${DESTDIR}${dest}"
  echo "installed ${dest}"
}

install_file "${ROOT}/data/udev/39-easyrestore.rules" \
  "${PREFIX}/lib/udev/rules.d/39-easyrestore.rules"

if [[ "${WITH_HELPER}" -eq 1 ]]; then
  install_file "${ROOT}/data/dbus/io.easyrestore.Helper.conf" \
    "${PREFIX}/share/dbus-1/system.d/io.easyrestore.Helper.conf"
  install_file "${ROOT}/data/dbus/io.easyrestore.Helper.service" \
    "${PREFIX}/share/dbus-1/system-services/io.easyrestore.Helper.service"
  install_file "${ROOT}/data/polkit/io.easyrestore.policy" \
    "${PREFIX}/share/polkit-1/actions/io.easyrestore.policy"
  install_file "${ROOT}/data/systemd/easyrestore-helper.service" \
    "${PREFIX}/lib/systemd/system/easyrestore-helper.service"

  # Prefer an already-installed console script; otherwise point at python -m.
  if command -v easyrestore-helper >/dev/null 2>&1; then
    HELPER_BIN="$(command -v easyrestore-helper)"
  else
    HELPER_BIN="/usr/bin/env python3 -m easyrestore.helper"
    echo "note: easyrestore-helper not on PATH; service uses: ${HELPER_BIN}" >&2
  fi
  # Rewrite systemd unit ExecStart if we have a concrete binary.
  if [[ -x "${HELPER_BIN}" ]]; then
    sed "s|ExecStart=.*|ExecStart=${HELPER_BIN} --system|" \
      "${ROOT}/data/systemd/easyrestore-helper.service" \
      > "${DESTDIR}${PREFIX}/lib/systemd/system/easyrestore-helper.service"
  fi

  if command -v systemctl >/dev/null 2>&1 && [[ -z "${DESTDIR}" ]]; then
    systemctl daemon-reload || true
    systemctl enable --now easyrestore-helper.service || true
  fi
fi

if command -v udevadm >/dev/null 2>&1 && [[ -z "${DESTDIR}" ]]; then
  udevadm control --reload-rules || true
  udevadm trigger --subsystem-match=usb || true
fi

echo "Host support installed (udev$([ "${WITH_HELPER}" -eq 1 ] && echo '+helper'))."
echo "Add your user to the plugdev group if Apple USB nodes are not accessible."
