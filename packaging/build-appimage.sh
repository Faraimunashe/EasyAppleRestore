#!/usr/bin/env bash
# Build a portable EasyRestore AppImage for tester releases.
#
# Prerequisites:
#   - Built vendor stack: ./vendor/build.sh  (or existing vendor/prefix)
#   - Network once (to fetch appimagetool) unless TOOLS_DIR already has it
#   - python3 + venv + pip
#
# Output:
#   dist/EasyRestore-<version>-x86_64.AppImage
#   dist/EasyRestore-<version>-x86_64.AppDir.tar.gz  (fallback portable tree)
#
# USB access still needs host udev rules; after downloading the AppImage run:
#   sudo ./packaging/install-host-support.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

VERSION="$(python3 -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")"
ARCH="$(uname -m)"
BUILD_ROOT="${ROOT}/build/appimage"
APPDIR="${BUILD_ROOT}/EasyRestore.AppDir"
DIST="${ROOT}/dist"
TOOLS_DIR="${ROOT}/build/tools"
VENDOR_SRC="${EASYRESTORE_VENDOR_PREFIX:-${ROOT}/vendor/prefix}"
PYTHON="${PYTHON:-python3}"

KEEP_QT_LIBS=(
  libQt6Core
  libQt6DBus
  libQt6Gui
  libQt6Network
  libQt6OpenGL
  libQt6Svg
  libQt6SvgWidgets
  libQt6WaylandClient
  libQt6WaylandEglClientHwIntegration
  libQt6Widgets
  libQt6XcbQpa
  libQt6EglFSDeviceIntegration
  libQt6EglFsKmsSupport
  libicudata
  libicui18n
  libicuuc
  libQt6XkbCommonSupport
)

KEEP_QT_PLUGINS=(
  platforms
  platformthemes
  platforminputcontexts
  imageformats
  iconengines
  styles
  xcbglintegrations
  wayland-decoration-client
  wayland-graphics-integration-client
  wayland-shell-integration
  tls
  generic
)

KEEP_PYSIDE_MODULES=(
  QtCore
  QtGui
  QtWidgets
  QtDBus
  QtSvg
  QtSvgWidgets
  QtNetwork
  QtOpenGL
)

log() { printf '==> %s\n' "$*" >&2; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

need_vendor() {
  [[ -x "${VENDOR_SRC}/bin/idevicerestore" ]] || die "Missing ${VENDOR_SRC}/bin/idevicerestore — run ./vendor/build.sh first"
  [[ -x "${VENDOR_SRC}/sbin/usbmuxd" || -x "${VENDOR_SRC}/bin/usbmuxd" ]] || die "Missing usbmuxd in vendor prefix"
}

fetch_appimagetool() {
  mkdir -p "${TOOLS_DIR}"
  local tool="${TOOLS_DIR}/appimagetool-${ARCH}.AppImage"
  if [[ -x "${tool}" ]]; then
    echo "${tool}"
    return
  fi
  local url="https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-${ARCH}.AppImage"
  log "Downloading appimagetool (${ARCH})"
  curl -fsSL -o "${tool}" "${url}"
  chmod +x "${tool}"
  echo "${tool}"
}

prune_pyside() {
  local pyside="$1"
  local qt="${pyside}/Qt"
  [[ -d "${pyside}" ]] || return 0

  log "Pruning PySide6 extras under ${pyside}"

  # Drop QML, docs, designer tooling, translations bulk, examples.
  rm -rf "${qt}/qml" "${pyside}/doc" "${pyside}/examples" \
    "${pyside}/metatypes" "${pyside}/typesystems" \
    "${pyside}/glue" "${pyside}/include" \
    "${qt}/translations" 2>/dev/null || true
  rm -f "${pyside}"/{assistant,balsam,balsamui,designer,linguist,lrelease,lupdate,qmlformat,qmllint,qmlls,qsb,rcc,uic} 2>/dev/null || true

  # Keep only needed Qt shared libraries (and their symlinks).
  if [[ -d "${qt}/lib" ]]; then
    local keep_re
    keep_re="$(IFS='|'; echo "${KEEP_QT_LIBS[*]}")"
    find "${qt}/lib" -maxdepth 1 -type f -o -maxdepth 1 -type l | while read -r path; do
      base="$(basename "${path}")"
      if ! [[ "${base}" =~ ^(${keep_re})(\.so|[-.]) ]]; then
        # Also keep FFmpeg stubs only if multimedia kept — drop them.
        if [[ "${base}" == libav* || "${base}" == libQt6FFmpeg* || "${base}" == libsw* ]]; then
          rm -f "${path}"
          continue
        fi
        if [[ "${base}" == *.so* ]]; then
          rm -f "${path}"
        fi
      fi
    done
  fi

  # Plugin folders.
  if [[ -d "${qt}/plugins" ]]; then
    local plug
    for plug in "${qt}/plugins"/*; do
      [[ -e "${plug}" ]] || continue
      name="$(basename "${plug}")"
      keep=0
      for k in "${KEEP_QT_PLUGINS[@]}"; do
        if [[ "${name}" == "${k}" ]]; then keep=1; break; fi
      done
      if [[ "${keep}" -eq 0 ]]; then
        rm -rf "${plug}"
      fi
    done
  fi

  # Python extension modules / stubs for unused Qt modules.
  local mod
  for path in "${pyside}"/Qt*.abi3.so "${pyside}"/Qt*.pyi "${pyside}"/Qt*; do
    [[ -e "${path}" ]] || continue
    base="$(basename "${path}")"
    case "${base}" in
      Qt.py|Qt|__init__.py|__pycache__) continue ;;
    esac
    stem="${base%%.*}"
    stem="${stem%.abi3}"
    keep=0
    for k in "${KEEP_PYSIDE_MODULES[@]}"; do
      if [[ "${stem}" == "${k}" ]]; then keep=1; break; fi
    done
    # Keep package dirs for essentials only
    if [[ -d "${path}" ]]; then
      if [[ "${keep}" -eq 0 && "${base}" == Qt* ]]; then
        case "${base}" in
          QtAsyncio|Qt) ;;
          *) rm -rf "${path}" ;;
        esac
      fi
      continue
    fi
    if [[ "${keep}" -eq 0 ]]; then
      rm -f "${path}"
    fi
  done

  # Optional large support libs that Essentials sometimes ships.
  rm -f "${pyside}"/libpyside6qml* 2>/dev/null || true
}

write_apprun() {
  cat > "${APPDIR}/AppRun" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
HERE="$(dirname "$(readlink -f "$0")")"
VENDOR="${HERE}/usr/lib/easyrestore/vendor"
VENV="${HERE}/usr/lib/easyrestore/venv"
PYSIDE_QT="${VENV}/lib/python"*"/site-packages/PySide6/Qt"

export EASYRESTORE_VENDOR_PREFIX="${VENDOR}"
export PATH="${VENDOR}/sbin:${VENDOR}/bin:${VENV}/bin:${PATH:-}"
if [[ -d "${VENDOR}/lib" ]]; then
  export LD_LIBRARY_PATH="${VENDOR}/lib${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"
fi
if [[ -d "${VENDOR}/lib64" ]]; then
  export LD_LIBRARY_PATH="${VENDOR}/lib64${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"
fi

# Prefer bundled Qt plugins when present.
for plug in ${PYSIDE_QT}/plugins; do
  if [[ -d "${plug}" ]]; then
    export QT_PLUGIN_PATH="${plug}${QT_PLUGIN_PATH:+:${QT_PLUGIN_PATH}}"
  fi
done
for lib in ${PYSIDE_QT}/lib; do
  if [[ -d "${lib}" ]]; then
    export LD_LIBRARY_PATH="${lib}${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"
  fi
done

# AppImage: use system helper when installed; otherwise LocalHelperClient.
exec "${VENV}/bin/python" -m easyrestore "$@"
EOF
  chmod +x "${APPDIR}/AppRun"
}

prepare_appdir() {
  log "Preparing AppDir at ${APPDIR}"
  rm -rf "${APPDIR}"
  mkdir -p \
    "${APPDIR}/usr/bin" \
    "${APPDIR}/usr/lib/easyrestore" \
    "${APPDIR}/usr/share/applications" \
    "${APPDIR}/usr/share/metainfo" \
    "${APPDIR}/usr/share/icons/hicolor"

  # Vendor libimobiledevice stack (relocatable via EASYRESTORE_VENDOR_PREFIX).
  mkdir -p "${APPDIR}/usr/lib/easyrestore/vendor"
  rsync -a --delete \
    --exclude 'share/man' \
    --exclude 'share/doc' \
    "${VENDOR_SRC}/" "${APPDIR}/usr/lib/easyrestore/vendor/"

  # Embedded Python environment (copied binaries so AppImage is relocatable).
  log "Creating embedded venv"
  "${PYTHON}" -m venv --copies "${APPDIR}/usr/lib/easyrestore/venv"
  # shellcheck disable=SC1091
  source "${APPDIR}/usr/lib/easyrestore/venv/bin/activate"
  pip install --upgrade pip wheel
  # Essentials only (no PySide6_Addons / WebEngine / Multimedia).
  pip install --no-compile "PySide6_Essentials>=6.6.0" "dbus-next>=0.2.3"
  pip install --no-compile --no-deps "${ROOT}"
  deactivate

  local pyver
  pyver="$("${APPDIR}/usr/lib/easyrestore/venv/bin/python" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
  local site="${APPDIR}/usr/lib/easyrestore/venv/lib/python${pyver}/site-packages"
  prune_pyside "${site}/PySide6"

  # Desktop + icons (AppImage top-level + freedesktop paths).
  install -m644 "${ROOT}/data/desktop/io.easyrestore.EasyRestore.desktop" \
    "${APPDIR}/io.easyrestore.EasyRestore.desktop"
  install -m644 "${ROOT}/data/desktop/io.easyrestore.EasyRestore.desktop" \
    "${APPDIR}/usr/share/applications/io.easyrestore.EasyRestore.desktop"
  # AppImage desktop Exec must be AppRun-relative binary name.
  sed -i 's|^Exec=.*|Exec=easyrestore|' "${APPDIR}/io.easyrestore.EasyRestore.desktop"
  # usr/bin shim for desktop integration (AppDir root is ../.. from usr/bin).
  cat > "${APPDIR}/usr/bin/easyrestore" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$(readlink -f "$0")")/../.." && pwd)"
exec "${ROOT}/AppRun" "$@"
EOF
  chmod +x "${APPDIR}/usr/bin/easyrestore"

  install -m644 "${ROOT}/data/metainfo/io.easyrestore.EasyRestore.metainfo.xml" \
    "${APPDIR}/usr/share/metainfo/io.easyrestore.EasyRestore.metainfo.xml" 2>/dev/null || true

  rsync -a "${ROOT}/data/icons/hicolor/" "${APPDIR}/usr/share/icons/hicolor/"
  install -Dm644 "${ROOT}/data/icons/io.easyrestore.EasyRestore.svg" \
    "${APPDIR}/usr/share/icons/hicolor/scalable/apps/io.easyrestore.EasyRestore.svg"
  # Top-level icon for appimagetool
  install -m644 "${ROOT}/data/icons/hicolor/256x256/apps/io.easyrestore.EasyRestore.png" \
    "${APPDIR}/io.easyrestore.EasyRestore.png"

  write_apprun
}

build_tarball() {
  mkdir -p "${DIST}"
  local out="${DIST}/EasyRestore-${VERSION}-${ARCH}.AppDir.tar.gz"
  log "Writing portable AppDir tarball ${out}"
  tar -C "${BUILD_ROOT}" -czf "${out}" EasyRestore.AppDir
  echo "${out}"
}

build_appimage() {
  mkdir -p "${DIST}"
  local tool out
  tool="$(fetch_appimagetool)"
  out="${DIST}/EasyRestore-${VERSION}-${ARCH}.AppImage"
  log "Packing ${out}"
  # Extracted appimagetool needs FUSE; prefer --appimage-extract-and-run.
  ARCH="${ARCH}" "${tool}" --appimage-extract-and-run "${APPDIR}" "${out}"
  chmod +x "${out}"
  echo "${out}"
}

smoke_test() {
  local appimage="$1"
  log "Smoke-testing AppImage (imports + vendor tools)"
  # Mount-free extract run via --appimage-extract-and-run for CI-ish hosts.
  EASYRESTORE_RESTORE_STUB=1 \
    "${appimage}" --appimage-extract-and-run --help >/dev/null 2>&1 || true
  # Direct AppDir smoke (more reliable than FUSE).
  EASYRESTORE_RESTORE_STUB=1 \
    "${APPDIR}/AppRun" -c 'pass' 2>/dev/null || \
  "${APPDIR}/usr/lib/easyrestore/venv/bin/python" - <<'PY'
from easyrestore.backend.identifier import ensure_vendor_env, vendor_tool_report
import os
# AppRun sets this; simulate for direct python smoke when run from script:
# caller should have exported EASYRESTORE_VENDOR_PREFIX already if needed.
print("vendor", ensure_vendor_env())
report = vendor_tool_report()
missing = [k for k, v in report.items() if not v]
assert not missing, missing
print("tools ok", report)
from PySide6.QtWidgets import QApplication
print("PySide6 ok")
PY
}

main() {
  need_vendor
  prepare_appdir
  # Point smoke at bundled vendor.
  export EASYRESTORE_VENDOR_PREFIX="${APPDIR}/usr/lib/easyrestore/vendor"
  export PATH="${EASYRESTORE_VENDOR_PREFIX}/sbin:${EASYRESTORE_VENDOR_PREFIX}/bin:${PATH}"
  export LD_LIBRARY_PATH="${EASYRESTORE_VENDOR_PREFIX}/lib${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"
  "${APPDIR}/usr/lib/easyrestore/venv/bin/python" - <<'PY'
from easyrestore.backend.identifier import ensure_vendor_env, vendor_tool_report
from PySide6.QtWidgets import QApplication
assert ensure_vendor_env() is not None
report = vendor_tool_report()
missing = [k for k, v in report.items() if not v]
assert not missing, missing
print("smoke: vendor tools", report)
print("smoke: PySide6 import ok")
PY

  local tarball appimage
  tarball="$(build_tarball)"
  appimage="$(build_appimage)"
  log "Built:"
  ls -lh "${tarball}" "${appimage}"
  cat > "${DIST}/README-TESTING.txt" <<EOF
EasyRestore ${VERSION} — tester build (${ARCH})

Files
-----
- EasyRestore-${VERSION}-${ARCH}.AppImage   — primary download
- EasyRestore-${VERSION}-${ARCH}.AppDir.tar.gz — same tree without AppImage wrapper

Quick start
-----------
1. chmod +x EasyRestore-${VERSION}-${ARCH}.AppImage
2. ./EasyRestore-${VERSION}-${ARCH}.AppImage
3. For USB restore with a real device, install host udev rules (once):
     sudo ./packaging/install-host-support.sh
   (from the source tree) or copy data/udev/39-easyrestore.rules into
   /etc/udev/rules.d/ and reload udev.

Notes
-----
- The AppImage bundles Python, PySide6 (trimmed), and the libimobiledevice stack.
- If no system helper is installed, restores run in-process (LocalHelper).
- Optional privileged helper: sudo ./packaging/install-host-support.sh --with-helper
EOF
  log "Done. Artifacts in ${DIST}/"
}

main "$@"
