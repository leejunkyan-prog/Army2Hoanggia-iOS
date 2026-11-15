#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p build/CraftDiagnostics302.app
app="$PWD/build/CraftDiagnostics302.app"
sdk="$(xcrun --sdk iphonesimulator --show-sdk-path)"
xcrun --sdk iphonesimulator clang -arch arm64 -isysroot "$sdk" \
 -mios-simulator-version-min=18.0 -fobjc-arc -O1 -Wno-deprecated-declarations \
 -framework UIKit -framework Foundation -framework CoreGraphics -framework QuartzCore \
 -DAG_RETURN_DIAGNOSTIC=1 -DAG_RETURN_BUILD=302 -DAG_CRAFT_DIAGNOSTIC=1 ReturnDiagnostics.m CraftDiagnostics.c test_craft_diagnostics302.m \
 -o "$app/CraftDiagnostics302"
python3 - <<'PY'
import plistlib
from pathlib import Path
info={'CFBundleIdentifier':'vn.army2hoanggia.craftdiagnostics302test','CFBundleExecutable':'CraftDiagnostics302',
      'CFBundleName':'CraftDiagnostics302','CFBundleVersion':'1','CFBundleShortVersionString':'1.0',
      'CFBundlePackageType':'APPL','MinimumOSVersion':'18.0','LSRequiresIPhoneOS':True,
      'CFBundleSupportedPlatforms':['iPhoneSimulator'],'UIDeviceFamily':[1,2]}
Path('build/CraftDiagnostics302.app/Info.plist').write_bytes(plistlib.dumps(info))
PY
codesign --force --sign - --timestamp=none "$app"
xcrun simctl list devices available --json > build/simulator302-devices.json
device="$(python3 - <<'PY'
import json
x=json.load(open('build/simulator302-devices.json'))
phones=[d for group in x['devices'].values()for d in group if 'iPhone' in d['name']]
assert phones,'An iPhone simulator is required'
print(next((d for d in phones if d['state']=='Booted'),phones[0])['udid'])
PY
)"
if ! xcrun simctl list devices booted | grep -q "$device"; then xcrun simctl boot "$device"; fi
xcrun simctl bootstatus "$device" -b
xcrun simctl install "$device" "$app"
xcrun simctl launch --terminate-running-process "$device" vn.army2hoanggia.craftdiagnostics302test
container="$(xcrun simctl get_app_container "$device" vn.army2hoanggia.craftdiagnostics302test data)"
for attempt in $(seq 1 20); do
 if [ -f "$container/Documents/craft302-result.json" ]; then break; fi
 sleep 1
done
cp "$container/Documents/craft302-result.json" build/craft302-result.json
python3 - <<'PY'
import json
r=json.load(open('build/craft302-result.json'));print(json.dumps(r,indent=2))
assert r['passed'],r
PY



