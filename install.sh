#!/bin/sh
# Install Deepin Jumplist for the current user (no root needed).
#   ./install.sh            install
#   ./install.sh --system   install for all users into /usr/local (run with sudo)
set -eu

SRC="$(cd "$(dirname "$0")" && pwd)"
if [ "${1:-}" = "--system" ]; then
    PREFIX=/usr/local
    LIBDIR="$PREFIX/share/deepin-jumplist"
    BINDIR="$PREFIX/bin"
    APPDIR="$PREFIX/share/applications"
    ICONDIR="$PREFIX/share/icons/hicolor/scalable/apps"
else
    DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
    LIBDIR="$DATA/deepin-jumplist"
    BINDIR="$HOME/.local/bin"
    APPDIR="$DATA/applications"
    ICONDIR="$DATA/icons/hicolor/scalable/apps"
fi

if ! python3 -c "import PyQt5.QtWidgets, PyQt5.QtNetwork" 2>/dev/null; then
    echo "PyQt5 is missing. Install it first:"
    echo "    sudo apt install python3-pyqt5 libqt5svg5"
    exit 1
fi

mkdir -p "$LIBDIR" "$BINDIR" "$APPDIR" "$ICONDIR"
rm -rf "$LIBDIR/deepin_jumplist"
cp -r "$SRC/deepin_jumplist" "$LIBDIR/"
find "$LIBDIR" -name __pycache__ -type d -prune -exec rm -rf {} +

sed "s|@LIBDIR@|$LIBDIR|" "$SRC/data/deepin-jumplist.sh" > "$BINDIR/deepin-jumplist"
chmod 755 "$BINDIR/deepin-jumplist"

# Use the absolute launcher path so the dock entry works even if ~/.local/bin
# is not on the PATH of the session.
sed "s|^Exec=deepin-jumplist|Exec=$BINDIR/deepin-jumplist|" \
    "$SRC/data/deepin-jumplist.desktop" > "$APPDIR/deepin-jumplist.desktop"
cp "$SRC/deepin_jumplist/resources/deepin-jumplist.svg" "$ICONDIR/"

command -v update-desktop-database >/dev/null && update-desktop-database "$APPDIR" 2>/dev/null || true

echo "Installed. Open the launcher, find \"Deepin Jumplist\", right-click it and choose \"Send to dock\"."
