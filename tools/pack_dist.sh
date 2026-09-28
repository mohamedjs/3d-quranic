#!/bin/sh
# Pack the current build (only this build's hashed assets) for headless tests elsewhere.
cd "$(dirname "$0")/.." || exit 1
MIN=${1:-3}
tar czf blender/_bridge/out/dist.tgz -C dist $(cd dist && find assets -mmin -$MIN -type f) index.html $(cd dist && ls manifest.webmanifest sw.js 2>/dev/null) data audio models illustrations ui draco icons
ls -la blender/_bridge/out/dist.tgz
