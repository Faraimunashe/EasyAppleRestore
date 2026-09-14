# EasyRestore — AppImage notes (skeleton)
#
# AppImage is the "just works" download while Flatpak/Snap reviews are pending.
# Proposed layout once the vendor prefix is built:
#
#   EasyRestore.AppDir/
#     AppRun
#     io.easyrestore.EasyRestore.desktop
#     usr/bin/easyrestore
#     usr/bin/easyrestore-helper   # optional; host polkit/system helper preferred
#     usr/lib/easyrestore/...      # vendored libimobiledevice
#     usr/share/...
#
# Build outline:
#   1. ./vendor/build.sh with PREFIX=$AppDir/usr
#   2. pip install --prefix=$AppDir/usr .
#   3. copy data/* into $AppDir/usr/share
#   4. appimagetool EasyRestore.AppDir EasyRestore-x86_64.AppImage
#
# USB access inside an AppImage still benefits from a system-installed helper
# + udev rules; document that on the download page.
