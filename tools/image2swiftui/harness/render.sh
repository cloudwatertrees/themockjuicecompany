#!/bin/zsh
# Renders a generated Swift file through SwiftUI on the Mac: render.sh Art.swift out.png [width height scale]
set -e
HERE=${0:A:h}
SDK=$(xcrun --show-sdk-path --sdk macosx)
BIN=$(mktemp -t image2swiftui_render)
xcrun swiftc -O -sdk "$SDK" -target "$(uname -m)-apple-macos14.0" "$1" "$HERE/main.swift" -o "$BIN"
"$BIN" "$2" "${3:-937}" "${4:-1678}" "${5:-1}"
rm -f "$BIN"
