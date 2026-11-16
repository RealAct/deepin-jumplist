#!/bin/sh
# Build an installable .deb (architecture: all) with dpkg-deb.
#   ./packaging/build-deb.sh   ->  dist/deepin-jumplist_<version>_all.deb
set -eu
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(sed -n 's/^VERSION = "\(.*\)"/\1/p' "$ROOT/deepin_jumplist/__init__.py")"
BUILD="$(mktemp -d)"
trap 'rm -rf "$BUILD"' EXIT
PKG="$BUILD/deepin-jumplist"

mkdir -p "$PKG/DEBIAN" "$PKG/usr/bin" "$PKG/usr/share/deepin-jumplist" \
         "$PKG/usr/share/applications" "$PKG/usr/share/icons/hicolor/scalable/apps" \
         "$PKG/usr/share/doc/deepin-jumplist"

cp -r "$ROOT/deepin_jumplist" "$PKG/usr/share/deepin-jumplist/"
find "$PKG" -name __pycache__ -type d -prune -exec rm -rf {} +
sed "s|@LIBDIR@|/usr/share/deepin-jumplist|" "$ROOT/data/deepin-jumplist.sh" > "$PKG/usr/bin/deepin-jumplist"
chmod 755 "$PKG/usr/bin/deepin-jumplist"
cp "$ROOT/data/deepin-jumplist.desktop" "$PKG/usr/share/applications/"
cp "$ROOT/deepin_jumplist/resources/deepin-jumplist.svg" "$PKG/usr/share/icons/hicolor/scalable/apps/"
cp "$ROOT/README.md" "$PKG/usr/share/doc/deepin-jumplist/"

cat > "$PKG/DEBIAN/control" <<CONTROL
Package: deepin-jumplist
Version: $VERSION
Section: utils
Priority: optional
Architecture: all
Depends: python3 (>= 3.7), python3-pyqt5, libqt5svg5
Recommends: python3-pyqt5.qtx11extras
Maintainer: Deepin Jumplist contributors <noreply@users.noreply.github.com>
Homepage: https://github.com/RealAct/deepin-jumplist
Description: Windows 11 style jump list for the Deepin dock
 Click the dock icon to get a rounded pop-up list of the files you opened
 most recently plus the ones you pinned, and open any of them in its default
 application with one click. Includes a tray icon with Options and About.
CONTROL

cat > "$PKG/DEBIAN/postinst" <<'POST'
#!/bin/sh
set -e
command -v update-desktop-database >/dev/null && update-desktop-database -q /usr/share/applications || true
command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -q -t /usr/share/icons/hicolor || true
exit 0
POST
cp "$PKG/DEBIAN/postinst" "$PKG/DEBIAN/postrm"
chmod 755 "$PKG/DEBIAN/postinst" "$PKG/DEBIAN/postrm"

mkdir -p "$ROOT/dist"
OUT="$ROOT/dist/deepin-jumplist_${VERSION}_all.deb"
dpkg-deb --root-owner-group --build "$PKG" "$OUT"
echo "Built $OUT"
