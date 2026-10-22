#!/bin/zsh
# usage: build_host.sh dev|repo   -> builds and installs com.scratch.forestrender[.repo]
set -e
SP=/Users/laverath/Desktop/themockjuicecompany/tools/scene-trace/work
REPO=/Users/laverath/Desktop/themockjuicecompany
UDID=C79B1642-6DE6-4BD5-9BE2-8F6C49BC0929
MODE=$1
if [[ $MODE == dev ]]; then
  $SP/venv/bin/python $SP/tools/mkdev.py ${ART_SRC:-$REPO/ios/mockjuice/Views/Components/ForestPathIllustration.swift} $SP/host/ArtDev.swift
  ART=$SP/host/ArtDev.swift; BID=com.scratch.forestrender; APP=$SP/host/Dev.app
else
  ART=${ART_FILE:-$REPO/ios/mockjuice/Views/Components/ForestPathIllustration.swift}; BID=com.scratch.forestrender.repo; APP=$SP/host/Repo.app
fi
rm -rf $APP; mkdir -p $APP
SDK=$(xcrun --sdk iphonesimulator --show-sdk-path)
xcrun -sdk iphonesimulator swiftc -O -parse-as-library -target arm64-apple-ios18.0-simulator -sdk $SDK \
  -Xlinker -platform_version -Xlinker ios-simulator -Xlinker 18.0 -Xlinker 18.5 \
  -o $APP/Host $SP/host/Host.swift $ART
cat > $APP/Info.plist <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleIdentifier</key><string>$BID</string>
<key>CFBundleExecutable</key><string>Host</string>
<key>CFBundleName</key><string>Host</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>CFBundleShortVersionString</key><string>1.0</string>
<key>CFBundleVersion</key><string>1</string>
<key>MinimumOSVersion</key><string>18.0</string>
<key>CFBundleSupportedPlatforms</key><array><string>iPhoneSimulator</string></array>
<key>UIDeviceFamily</key><array><integer>1</integer></array>
<key>UILaunchScreen</key><dict/>
</dict></plist>
PL
codesign -s - -f $APP >/dev/null 2>&1 || true
xcrun simctl install $UDID $APP
otool -l $APP/Host | grep -A4 LC_BUILD_VERSION | grep -E 'minos|sdk' | tr '\n' ' '; echo
echo "installed $BID"
