#!/bin/sh
# Remove a per-user (default) or --system install made by install.sh.
set -eu
if [ "${1:-}" = "--system" ]; then
    PREFIX=/usr/local
    rm -rf "$PREFIX/share/deepin-jumplist"
    rm -f "$PREFIX/bin/deepin-jumplist" \
          "$PREFIX/share/applications/deepin-jumplist.desktop" \
          "$PREFIX/share/icons/hicolor/scalable/apps/deepin-jumplist.svg"
else
    DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
    "$HOME/.local/bin/deepin-jumplist" --quit 2>/dev/null || true
    rm -rf "$DATA/deepin-jumplist"
    rm -f "$HOME/.local/bin/deepin-jumplist" \
          "$DATA/applications/deepin-jumplist.desktop" \
          "$DATA/icons/hicolor/scalable/apps/deepin-jumplist.svg"
fi
rm -f "${XDG_CONFIG_HOME:-$HOME/.config}/autostart/deepin-jumplist.desktop"
echo "Removed. Your settings remain in ${XDG_CONFIG_HOME:-$HOME/.config}/deepin-jumplist."
