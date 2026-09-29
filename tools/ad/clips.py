import cv2, numpy as np, subprocess, os, shutil, glob
SRC = '/tmp/ad/src/ad.mp4'; OUT = '/tmp/www/ad/clips'
JOBS = {'walk': (46.0, 12.6, 1.4), 'house': (61.3, 8.25, 1.0), 'picker': (2.35, 0.9, 0.45), 'title': (0.2, 1.4, 1.0)}
# AssistiveTouch dot + the small speaker pill under it (original 384×832 coords), in the 640-wide crop
k = 640 / 384
mask = np.zeros((int(746 * k) + 2, 640), np.uint8)
cv2.circle(mask, (int(348 * k), int((380 - 44) * k)), int(33 * k), 255, -1)
cv2.rectangle(mask, (int(330 * k), int((402 - 44) * k)), (639, int((460 - 44) * k)), 255, -1)
for name, (ss, d, sp) in JOBS.items():
    tmp = f'/tmp/ad/src/raw_{name}'; shutil.rmtree(tmp, True); os.makedirs(tmp)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', str(ss), '-t', str(d), '-i', SRC, '-vf', f'crop=384:746:0:44,scale=640:-2:flags=lanczos,setpts=PTS/{sp},fps=30', f'{tmp}/%04d.png'], check=True)
    out = f'{OUT}/{name}'; shutil.rmtree(out, True); os.makedirs(out)
    files = sorted(glob.glob(f'{tmp}/*.png'))
    for f in files:
        im = cv2.imread(f); m = mask[:im.shape[0], :im.shape[1]]
        im = cv2.inpaint(im, m, 7, cv2.INPAINT_TELEA)
        bl = cv2.GaussianBlur(im, (0, 0), 1.6); im = cv2.addWeighted(im, 1.55, bl, -0.55, 0)
        cv2.imwrite(f'{out}/{os.path.basename(f)[:-4]}.jpg', im, [cv2.IMWRITE_JPEG_QUALITY, 90])
    print(name, len(files))
