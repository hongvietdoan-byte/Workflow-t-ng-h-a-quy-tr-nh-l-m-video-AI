# $1 = md path, $2 = pdf name, $3 = title
S="$TEMP/pdfwork"; mkdir -p "$S"
pandoc "$1" -s --metadata title="$3" -o "$S/x.html" || exit 1
sed -i 's|</head>|<style>body{font-family:Segoe UI,Arial,sans-serif;max-width:900px;margin:16px auto;padding:0 12px;font-size:14px;line-height:1.5}table{border-collapse:collapse;font-size:11px}td,th{border:1px solid #bbb;padding:3px 5px;vertical-align:top}pre,code{white-space:pre-wrap;font-size:11px}</style></head>|' "$S/x.html"
B="/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"; [ -x "$B" ] || B="/c/Program Files/Google/Chrome/Application/chrome.exe"
mkdir -p docs/pdf; "$B" --headless --disable-gpu --no-pdf-header-footer --print-to-pdf="$(cygpath -w "$PWD/docs/pdf/$2")" "file:///$(cygpath -m "$S/x.html")" >/dev/null 2>&1
ls -la "docs/pdf/$2"
