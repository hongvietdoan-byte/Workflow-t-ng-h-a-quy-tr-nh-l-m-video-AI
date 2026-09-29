#!/bin/bash
# clean.sh vNN : giu *_result.json + *_numbers.json (bo loi chep), xoa media / khung / to anh / wav / log
cd "$(dirname "$0")"
v=$1
for d in ${v}_seg*_L*/; do
  d=${d%/}; [ -f "$d/listen.json" ] && [ ! -f "${d}_numbers.json" ] && py strip_listen.py "$d" "${d}_numbers.json"
done
rm -rf ${v}_seg*_L*/ ${v}_seg*_frames/ ${v}_seg*.webm ${v}_seg*.mp4 ${v}_seg*.mkv ${v}_*.jpg ${v}_*_lst.txt ${v}_*.log ${v}_scan*
echo "con lai cua $v:"; ls ${v}_* 2>/dev/null
