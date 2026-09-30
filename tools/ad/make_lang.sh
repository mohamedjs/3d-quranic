#!/bin/bash
# make_lang.sh <lg: ar|en|ru>  → renders both formats with the new voices and encodes to /mnt/user-data/outputs/ads/
set -e; LG=$1; cd /tmp/ad; V=/root/gv/$LG/raw; mkdir -p /tmp/ad/n3/$LG /mnt/user-data/outputs/ads
[ $LG = ar ] && V=/root/gv/ar_habibi/raw; VA=$V; [ $LG = ar ] && VA=/root/gv/ar_habibi/ad
python3 - <<P
import json
L=json.load(open('/tmp/ad/i18n/lines.json'))['$LG']
json.dump({k: '$VA/ad__${LG}__'+k+'.wav' for k in L}, open('/tmp/ad/n3/$LG/vo.json','w'), indent=1)
P
GREET=$(ls $V/*people-of-the-elephant__zainab-$(python3 -c "import json,sys;L=json.load(open('/root/gv/voice_lines_$LG.json' if '$LG'!='ar' else '/root/gv/voice_lines.json'));print(L[0]['id'].split('-')[-1])").wav)
export VOFILES=/tmp/ad/n3/$LG/vo.json TIMING=/tmp/ad/n3/$LG/timing.json GREET
python3 timing.py
SUF=""; [ $LG != ar ] && SUF="-$LG"
for F in v h; do
  rm -rf /tmp/ad/frames_$F$SUF
  CUES=/tmp/ad/n3/$LG/cues.json python3 render.py $F$SUF video 30 0 end
done
CUES=/tmp/ad/n3/$LG/cues.json MIXOUT=/tmp/ad/n3/$LG/mix.wav python3 mix.py
N=rehla_ma3_alquran_ad; [ $LG != ar ] && N=quran_journey_ad_$LG
ffmpeg -y -loglevel error -framerate 30 -i frames_v$SUF/%05d.jpg -i n3/$LG/mix.wav -c:v libx264 -preset slow -crf 20 -pix_fmt yuv420p -c:a aac -b:a 160k -movflags +faststart -shortest /mnt/user-data/outputs/ads/${N}_9x16.mp4
ffmpeg -y -loglevel error -framerate 30 -i frames_h$SUF/%05d.jpg -i n3/$LG/mix.wav -c:v libx264 -preset slow -crf 20 -pix_fmt yuv420p -c:a aac -b:a 160k -movflags +faststart -shortest /mnt/user-data/outputs/ads/${N}_16x9.mp4
echo MADE $LG
