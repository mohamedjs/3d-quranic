import sys; sys.path.insert(0, '/var/www/html/old/3d-quranic/blender/v2/characters/')
import build_all
build_all.main([open('/var/www/html/old/3d-quranic/blender/v2/characters/_which.txt').read().strip()], fresh=False)
