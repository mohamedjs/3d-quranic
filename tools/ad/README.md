# Motion-graphics ad (43 s, 9:16 + 16:9)

Code-driven: `index.html` is a deterministic timeline (`render(t)`), rendered frame by frame with Playwright,
then muxed with ffmpeg. Clay style + Remix Icon, the game's own portraits/illustrations/screenshots.

1. Serve a folder containing `index.html`, `ornaments.svg` (public/ui), an `icons.svg` built from Remix Icon
   (book-open, sparkling-2, group, copper-coin, wifi-off, smartphone, play, lightbulb-flash, arrow-up-s),
   `fonts/` (@fontsource tajawal 500/700/800 arabic + latin, aref-ruqaa 700) and `img/` (game shots
   `v_/h_clean_mid.png`, `v_/h_clean_far.png`, illustrations `elephant.webp`, `kaaba.webp`).
2. `vo.py` — narrator lines with OmniVoice (Gradio demo on Colab), Whisper-checked.
3. `timing.py` — scene/cue times from the voice clips (`vo_files.json`: n1…n7 narrator, farmer, player); `mix.py` — voice + SFX only (no music): whooshes on cuts, pops when icons appear, a chime per coin. (`music.py` makes the SFX.)
4. `python3 render.py v video 30 0 end` (and `h`), then
   `ffmpeg -framerate 30 -i frames_v/%05d.jpg -i audio/mix.wav -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k -shortest out.mp4`
Narrator for the final cut: ElevenLabs Voice Library «Haytham – Energetic, Warm and Cheerful» (Egyptian), made on the website (free tier can't use library voices through the API).

## v2 — real footage
`clips.py` cuts four pieces from the iPhone recording (`Downloads/ad.mp4`): level picker, the walk that collects
coins up to «فتحت القصة! 🎉» (1.4× speed), arriving at grandma Zainab's house with her own greeting, and the title
screen. It crops the status bar and home band, inpaints the AssistiveTouch dot (OpenCV), upscales to 640 px and
sharpens → `clips/<name>/%04d.jpg` at 30 fps. `index.html` shows them in clay phone frames (`phone()`), and the
scene order follows the game: logo → pick a level → walk & collect → villagers → categories → Quran → play.
