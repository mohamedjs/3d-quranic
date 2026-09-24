#!/usr/bin/env python3
"""Tiny client for the BlenderMCP add-on socket (localhost:9876).
  bl.py run  script.py        run a Python file inside Blender
  bl.py shot out.png [size]   save a viewport screenshot
  bl.py info                  scene summary
"""
import json, socket, sys, os

def call(cmd, params=None, timeout=600):
    s = socket.create_connection(('localhost', 9876), timeout=timeout)
    s.sendall(json.dumps({'type': cmd, 'params': params or {}}).encode())
    buf = b''
    while True:
        chunk = s.recv(65536)
        if not chunk: break
        buf += chunk
        try: return json.loads(buf)
        except json.JSONDecodeError: continue
    return json.loads(buf)

if __name__ == '__main__':
    op = sys.argv[1]
    if op == 'run':
        r = call('execute_code', {'code': open(sys.argv[2]).read()})
    elif op == 'shot':
        r = call('get_viewport_screenshot', {'filepath': os.path.abspath(sys.argv[2]), 'max_size': int(sys.argv[3]) if len(sys.argv) > 3 else 1000})
    else:
        r = call('get_scene_info')
    print(json.dumps(r, ensure_ascii=False)[:4000])
    sys.exit(0 if r.get('status') == 'success' else 1)
