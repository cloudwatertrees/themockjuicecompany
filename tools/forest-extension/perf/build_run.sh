#!/bin/zsh
# Builds the perf host (-O) with the live and extension art files and runs it on the simulator.
set -e
APP=/Users/laverath/Desktop/themockjuicecompany/tools/forest-extension/perf/PerfHost.app; rm -rf $APP; mkdir -p $APP
SDK=$(xcrun --sdk iphonesimulator --show-sdk-path)
xcrun -sdk iphonesimulator swiftc -O -parse-as-library -target arm64-apple-ios18.0-simulator -sdk $SDK \
  -Xlinker -platform_version -Xlinker ios-simulator -Xlinker 18.0 -Xlinker 18.5 -o $APP/Host /Users/laverath/Desktop/themockjuicecompany/tools/forest-extension/perf/PerfHost.swift \
  /Users/laverath/Desktop/themockjuicecompany/ios/mockjuice/Views/Components/ForestPathIllustration.swift \
  /Users/laverath/Desktop/themockjuicecompany/ios/mockjuice/Views/Components/ForestPathExtension.swift
cat > $APP/Info.plist <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict><key>CFBundleIdentifier</key><string>com.scratch.forestperf</string><key>CFBundleExecutable</key><string>Host</string>
<key>CFBundlePackageType</key><string>APPL</string><key>CFBundleVersion</key><string>1</string><key>CFBundleShortVersionString</key><string>1.0</string>
<key>MinimumOSVersion</key><string>18.0</string><key>CFBundleSupportedPlatforms</key><array><string>iPhoneSimulator</string></array><key>UILaunchScreen</key><dict/></dict></plist>
PL
codesign -s - -f $APP >/dev/null 2>&1 || true
xcrun simctl install C79B1642-6DE6-4BD5-9BE2-8F6C49BC0929 $APP
for i in 1 2; do xcrun simctl launch --console-pty --terminate-running-process C79B1642-6DE6-4BD5-9BE2-8F6C49BC0929 com.scratch.forestperf 2>&1 | grep perf; done
