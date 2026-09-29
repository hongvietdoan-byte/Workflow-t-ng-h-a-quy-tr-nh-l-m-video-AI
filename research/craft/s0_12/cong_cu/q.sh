#!/bin/bash
# hang doi: moi dong "TAG LANG LS LE [song]" -> proc; chay tuan tu
cd "$(dirname "$0")"
while read -r tag lang ls le song; do
  [ -z "$tag" ] && continue
  py pipe.py proc "$tag" "$lang" "$ls" "$le" $song > "${tag}_proc.log" 2>&1
done < "$1"
echo done > "$1.done"
