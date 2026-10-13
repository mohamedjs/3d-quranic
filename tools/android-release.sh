#!/usr/bin/env bash
# Builds the signed Android App Bundle (.aab) for Google Play.
#   bash tools/android-release.sh
# First run: creates the upload key android/rehla-release.jks and android/keystore.properties
# (both git-ignored). BACK THEM UP somewhere safe (not in git): without this key you cannot
# publish updates to the same app on Google Play.
set -euo pipefail
cd "$(dirname "$0")/.."
KS=android/rehla-release.jks PROPS=android/keystore.properties
if [ ! -f "$PROPS" ]; then
  echo "== First release: creating the upload key =="
  read -rsp "Choose a password for the key (min 6 chars): " PW; echo
  read -rsp "Repeat the password: " PW2; echo
  [ "$PW" = "$PW2" ] || { echo "Passwords do not match"; exit 1; }
  [ ${#PW} -ge 6 ] || { echo "Password too short"; exit 1; }
  keytool -genkeypair -v -keystore "$KS" -alias rehla -keyalg RSA -keysize 2048 -validity 10000 \
    -storepass "$PW" -keypass "$PW" -dname "CN=Rehla ma3 al-Quran, O=mohamedjs, C=EG"
  printf 'storeFile=rehla-release.jks\nstorePassword=%s\nkeyAlias=rehla\nkeyPassword=%s\n' "$PW" "$PW" > "$PROPS"
  chmod 600 "$PROPS" "$KS"
  echo ">> Key created. Copy android/rehla-release.jks + android/keystore.properties to a safe place NOW."
fi
npm run build
npx cap sync android
(cd android && ./gradlew bundleRelease)
OUT=android/app/build/outputs/bundle/release/app-release.aab
cp "$OUT" ~/Downloads/rehla-ma3-alquran.aab
echo
echo "Done: ~/Downloads/rehla-ma3-alquran.aab ($(du -h "$OUT" | cut -f1))"
echo "Next upload: raise versionCode in android/app/build.gradle first."
