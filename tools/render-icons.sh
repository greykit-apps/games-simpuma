#!/usr/bin/env bash
# Render the favicons, the touch icon, the share card and the README's
# screenshots (games-meta STANDARD.md §9). icon.svg is the hand-drawn source;
# og.png is the game's own card, drawn by index.html?shot=og on a canvas with
# the painted wordmark and the Pride font; the screenshots are ?shot=title
# and ?shot=city. All go through a headless Chromium (Edge on Windows, Chrome
# elsewhere), and the .ico through Pillow. Run from the repo root; commit
# the outputs.
set -euo pipefail
cd "$(dirname "$0")/.."
CHROME=""
for c in "/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" "/c/Program Files/Google/Chrome/Application/chrome.exe" \
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" "$(command -v google-chrome || true)" "$(command -v chromium || true)"; do
  if [ -n "$c" ] && [ -x "$c" ]; then CHROME="$c"; break; fi
done
[ -n "$CHROME" ] || { echo "render-icons: no headless Chromium found" >&2; exit 1; }
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
# a Windows browser wants Windows paths; elsewhere the paths stay as they are
win() { cygpath -w "$1" 2>/dev/null || printf '%s' "$1"; }
url() { local p; p=$(win "$1"); printf 'file:///%s' "${p//\\//}"; }
here=$(pwd)
shoot() {   # shoot <url> <out.png> <w> <h>
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars --no-sandbox --user-data-dir="$(win "$tmp/prof")" --force-device-scale-factor=1 \
    --window-size="$3,$4" --virtual-time-budget=8000 --screenshot="$(win "$2")" "$1" >/dev/null 2>&1 || true
  [ -s "$2" ] || { echo "render-icons: $2 was not written" >&2; exit 1; }
}
icon() {    # icon <size> <out.png>: icon.svg full-bleed on the plate, as iOS wants it
  cat > "$tmp/i$1.html" <<HTML
<!doctype html><html><head><meta charset="utf-8"><style>html,body{margin:0;padding:0;background:#05070f;overflow:hidden}img{display:block;width:$1px;height:$1px;image-rendering:pixelated}</style></head><body><img src="$(url "$here/icon.svg")"></body></html>
HTML
  shoot "$(url "$tmp/i$1.html")" "$2" "$1" "$1"
}
icon 16 "$here/favicon-16x16.png"
icon 32 "$here/favicon-32x32.png"
icon 48 "$tmp/48.png"
icon 180 "$here/apple-touch-icon.png"
python - "$tmp/48.png" <<'PY'
import sys
from PIL import Image
Image.open(sys.argv[1]).save("favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
PY
shoot "$(url "$here/index.html")?shot=og" "$here/og.png" 1200 630
shoot "$(url "$here/index.html")?hold=never&shot=title" "$here/screenshots/title.png" 1280 800
shoot "$(url "$here/index.html")?shot=city" "$here/screenshots/city.png" 1280 800
echo "rendered favicon-16x16.png favicon-32x32.png favicon.ico apple-touch-icon.png og.png screenshots/title.png screenshots/city.png"
