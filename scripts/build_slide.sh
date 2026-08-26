#!/bin/bash
# Rasterise docs/slide.html to a PNG for LinkedIn.
# The HTML is the source. Never edit the PNG.
set -e
cd "$(dirname "$0")/.."
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
"$CHROME" --headless --disable-gpu --hide-scrollbars \
  --force-device-scale-factor=2 --window-size=1600,772 \
  --virtual-time-budget=6000 \
  --screenshot="$(pwd)/docs/slide.png" \
  "file://$(pwd)/docs/slide.html"
echo "written: docs/slide.png  ($(sips -g pixelWidth -g pixelHeight docs/slide.png | tail -2 | tr -d ' \n'))"
