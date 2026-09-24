#!/bin/sh
# usage: ill.sh name [pct]
cd "$(dirname "$0")/.." && echo "exec(open('/var/www/html/old/3d-quranic/blender/illustrations/illustrations.py').read()); run('$1', pct=${2:-50})" | python3 _bridge/bx.py - 170 2>&1 | grep -v INFO | tail -${3:-25}
