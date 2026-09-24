#!/usr/bin/env bash
# Rebuild PLAN.docx and PLAN.pdf from PLAN.md (requires pandoc + Chrome/Edge/Chromium).
# Windows (Git Bash): Chrome/Edge in Program Files. Linux/cloud: chromium on PATH or /opt/pw-browsers/chromium;
# PANDOC / BROWSER environment variables override the lookup.
set -euo pipefail
cd "$(dirname "$0")/.."
PANDOC="${PANDOC:-pandoc}"
command -v "$PANDOC" >/dev/null 2>&1 || PANDOC="$(python3 -c 'import pypandoc; print(pypandoc.get_pandoc_path())' 2>/dev/null || true)"
[ -n "$PANDOC" ] && command -v "$PANDOC" >/dev/null 2>&1 || { echo "pandoc not found (install pandoc or: pip install pypandoc_binary)"; exit 1; }
if [ -z "${BROWSER:-}" ]; then
  for B in "/c/Program Files/Google/Chrome/Application/chrome.exe" "/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" \
           "/c/Program Files/Microsoft/Edge/Application/msedge.exe" "$(command -v chromium 2>/dev/null)" "$(command -v google-chrome 2>/dev/null)" \
           "/opt/pw-browsers/chromium"; do [ -n "$B" ] && [ -x "$B" ] && BROWSER="$B" && break; done
fi
[ -n "${BROWSER:-}" ] || { echo "no Chrome/Edge/Chromium found (set BROWSER=...)"; exit 1; }
if command -v cygpath >/dev/null 2>&1; then winpath() { cygpath -w "$1"; }; urlpath() { cygpath -m "$1"; }
else winpath() { echo "$1"; }; urlpath() { echo "$1"; }; fi
EXTRA=""; [ "$(id -u 2>/dev/null || echo 1)" = "0" ] && EXTRA="--no-sandbox"
pdf() { "$BROWSER" --headless --disable-gpu $EXTRA --no-pdf-header-footer --print-to-pdf="$(winpath "$PWD/$1")" "file:///$(urlpath "$2" | sed 's#^/##')" >/dev/null 2>&1; }
"$PANDOC" PLAN.md -o PLAN.docx
TMP="$(mktemp -d)"
"$PANDOC" PLAN.md -s --metadata title="Kế hoạch triển khai — Auto Pipeline Video AI" --embed-resources -c tools/plan.css -o "$TMP/plan.html"
pdf PLAN.pdf "$TMP/plan.html"
# Official plans kept next to PLAN.md (same build: .md -> .docx + .pdf)
for DOC in docs/KE_HOACH_V3_CHINH_THUC; do
  [ -f "$DOC.md" ] || continue
  "$PANDOC" "$DOC.md" -o "$DOC.docx"
  "$PANDOC" "$DOC.md" -s --metadata title="Kế hoạch v3 chính thức — Auto Pipeline Video AI" --embed-resources -c tools/plan.css -o "$TMP/doc.html"
  pdf "$DOC.pdf" "$TMP/doc.html"
done
rm -rf "$TMP"
echo "Built PLAN.docx, PLAN.pdf and the official plan documents"
