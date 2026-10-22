#!/bin/zsh
# usage: build_app.sh [Debug|Release]  -> builds the mockjuice app target with swiftc + actool (xcodebuild is blocked
# by the sandbox: it cannot write DerivedData/info.plist) and installs it on the booted iPhone 16 Pro simulator.
set -e
CONF=${1:-Debug}
REPO=/Users/laverath/Desktop/themockjuicecompany
SRC=$REPO/ios/mockjuice
OUT=$REPO/tools/scene-trace/app/build-$CONF
UDID=C79B1642-6DE6-4BD5-9BE2-8F6C49BC0929
BID=app.themockjuicecompany.mockjuice-swiftui-system
APP=$OUT/mockjuice.app
rm -rf $APP; mkdir -p $APP $OUT/tmp
SDK=$(xcrun --sdk iphonesimulator --show-sdk-path)
OPT=(-Onone -g); [[ $CONF == Release ]] && OPT=(-O)
# Sources compiled from a copy with top-level #Preview blocks removed: the macro plugin server cannot run in the
# sandbox ("swift-plugin-server produced malformed response"). The app's files are not modified.
rm -rf $OUT/src; mkdir -p $OUT/src
for f in $(cd $SRC && find . -name '*.swift'); do
  mkdir -p $OUT/src/${f:h}
  awk 'BEGIN{skip=0} /^#Preview/{skip=1} { if (!skip) print; else if ($0 ~ /^}/) skip=0 }' $SRC/$f > $OUT/src/$f
done
SECONDS=0
xcrun -sdk iphonesimulator swiftc $OPT -parse-as-library -target arm64-apple-ios18.0-simulator -sdk $SDK \
  -swift-version 5 -enable-upcoming-feature MemberImportVisibility -module-name mockjuice \
  -Xlinker -platform_version -Xlinker ios-simulator -Xlinker 18.0 -Xlinker 18.2 \
  -o $APP/mockjuice $(find $OUT/src -name '*.swift')
echo "swiftc $CONF: ${SECONDS}s"
xcrun actool $SRC/Assets.xcassets --compile $APP --platform iphonesimulator --minimum-deployment-target 18.0 \
  --app-icon AppIcon --accent-color AccentColor --output-partial-info-plist $OUT/tmp/assets.plist \
  --target-device iphone --target-device ipad --output-format human-readable-text --errors >/dev/null 2>&1 || true
# actool cannot run in the sandbox (coresymbolicationd connection refused): no Assets.car. The home scene is vector art
# and needs none of the catalog's images.
[[ -f $APP/Assets.car ]] || echo 'note: no Assets.car (actool unavailable)'
cp -R $SRC/Resources/* $APP/ 2>/dev/null || true
cp -R $SRC/mockjuice_images $APP/ ; cp $SRC/questions.json $APP/
cat > $APP/Info.plist <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleIdentifier</key><string>$BID</string>
<key>CFBundleExecutable</key><string>mockjuice</string>
<key>CFBundleName</key><string>mockjuice</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>CFBundleShortVersionString</key><string>1.0</string>
<key>CFBundleVersion</key><string>1</string>
<key>MinimumOSVersion</key><string>18.0</string>
<key>CFBundleSupportedPlatforms</key><array><string>iPhoneSimulator</string></array>
<key>UIDeviceFamily</key><array><integer>1</integer><integer>2</integer></array>
<key>UILaunchScreen</key><dict/>
<key>UIApplicationSceneManifest</key><dict><key>UIApplicationSupportsMultipleScenes</key><true/></dict>
<key>UISupportedInterfaceOrientations</key><array><string>UIInterfaceOrientationPortrait</string></array>
</dict></plist>
PL
codesign -s - -f $APP >/dev/null 2>&1 || true
xcrun simctl install $UDID $APP
echo "installed $BID ($CONF) $(du -sh $APP/mockjuice | cut -f1) binary"
