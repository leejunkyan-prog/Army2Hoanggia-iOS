#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
mode="${1:-fixed}"
mkdir -p build
app="$PWD/build/WatchReturn296-$mode.app"
mkdir -p "$app/viewer"
cp -R viewer/. "$app/viewer/"
sdk="$(xcrun --sdk iphonesimulator --show-sdk-path)"
set --
if [ "$mode" = baseline ]; then set -- '-DWATCH_PRODUCTION="SpectatorBaseline294.m"'; fi
xcrun --sdk iphonesimulator clang -arch arm64 -isysroot "$sdk" \
 -mios-simulator-version-min=18.0 -fobjc-arc -fblocks -O1 \
 -Wno-deprecated-declarations -Wno-nullability-completeness \
 -framework UIKit -framework Foundation -framework WebKit -framework CoreGraphics -framework QuartzCore \
 "$@" WatchSurface.m test_watch_return296.m -o "$app/WatchReturn296"
python3 - "$app" "$mode" <<'PY'
import plistlib,sys
from pathlib import Path
info={'CFBundleIdentifier':'vn.army2hoanggia.return296test.'+sys.argv[2],
      'CFBundleExecutable':'WatchReturn296','CFBundleName':'WatchReturn296',
      'CFBundleVersion':'1','CFBundleShortVersionString':'1.0','CFBundlePackageType':'APPL',
      'MinimumOSVersion':'18.0','LSRequiresIPhoneOS':True,
      'CFBundleSupportedPlatforms':['iPhoneSimulator'],'UIDeviceFamily':[1,2]}
(Path(sys.argv[1])/'Info.plist').write_bytes(plistlib.dumps(info))
PY
codesign --force --sign - --timestamp=none "$app"
xcrun simctl list devices available --json > build/simulator296-devices.json
device="$(python3 - <<'PY'
import json
x=json.load(open('build/simulator296-devices.json'))
phones=[d for group in x['devices'].values() for d in group if 'iPhone' in d['name']]
assert phones
print(next((d for d in phones if d['state']=='Booted'),phones[0])['udid'])
PY
)"
if ! xcrun simctl list devices booted | grep -q "$device"; then xcrun simctl boot "$device"; fi
xcrun simctl bootstatus "$device" -b
bundle="vn.army2hoanggia.return296test.$mode"
xcrun simctl install "$device" "$app"
container="$(xcrun simctl get_app_container "$device" "$bundle" data)"
rm -f "$container/Documents/return296-result.json"
xcrun simctl launch --terminate-running-process "$device" "$bundle"
for attempt in $(seq 1 180); do
 if [ -f "$container/Documents/return296-result.json" ]; then break; fi
 sleep 1
done
if [ ! -f "$container/Documents/return296-result.json" ]; then
 xcrun simctl spawn "$device" log show --last 3m --style compact --predicate 'process == "WatchReturn296"' > "build/return296-$mode-timeout.txt" 2>&1 || true
 tail -80 "build/return296-$mode-timeout.txt"
 exit 1
fi
cp "$container/Documents/return296-result.json" "build/return296-$mode-result.json"
python3 - "$mode" <<'PY'
import json,sys
mode=sys.argv[1];r=json.load(open('build/return296-'+mode+'-result.json'))
print(json.dumps(r,indent=2))
if mode=='baseline':
    assert not r['passed'] and 'Manual leave did not send SP2 then room0' in r['reason'],r
    print('PASS expected Build294 failure: production manual-leave flow omitted room0 refresh')
else:
    assert r['passed'],r
    print('PASS production return flow and restored input on iOS Simulator')
PY

