#!/usr/bin/env bash
# Rebuild PLAN.docx and PLAN.pdf from PLAN.md (requires pandoc + Chrome/Edge).
set -euo pipefail
cd "$(dirname "$0")/.."
pandoc PLAN.md -o PLAN.docx
TMP="$(mktemp -d)"
pandoc PLAN.md -s --metadata title="Kế hoạch triển khai — Auto Pipeline Video AI" --embed-resources -c tools/plan.css -o "$TMP/plan.html"
for B in "/c/Program Files/Google/Chrome/Application/chrome.exe" "/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" "/c/Program Files/Microsoft/Edge/Application/msedge.exe"; do [ -x "$B" ] && BROWSER="$B" && break; done
"$BROWSER" --headless --disable-gpu --no-pdf-header-footer --print-to-pdf="$(cygpath -w "$PWD/PLAN.pdf")" "file:///$(cygpath -m "$TMP/plan.html")"
# Official plans kept next to PLAN.md (same build: .md -> .docx + .pdf)
for DOC in docs/KE_HOACH_V3_CHINH_THUC; do
  [ -f "$DOC.md" ] || continue
  pandoc "$DOC.md" -o "$DOC.docx"
  pandoc "$DOC.md" -s --metadata title="Kế hoạch v3 chính thức — Auto Pipeline Video AI" --embed-resources -c tools/plan.css -o "$TMP/doc.html"
  "$BROWSER" --headless --disable-gpu --no-pdf-header-footer --print-to-pdf="$(cygpath -w "$PWD/$DOC.pdf")" "file:///$(cygpath -m "$TMP/doc.html")"
done
rm -rf "$TMP"
echo "Built PLAN.docx, PLAN.pdf and the official plan documents"
