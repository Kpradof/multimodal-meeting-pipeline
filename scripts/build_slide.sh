#!/bin/bash
# Rasterise a slide to PNG for LinkedIn. The HTML is the source; never edit the PNG.
#
#   scripts/build_slide.sh full        both flows in one image
#   scripts/build_slide.sh audit       the notes auditor
#   scripts/build_slide.sh pipeline    the ingest pipeline (light)
#   scripts/build_slide.sh             both
set -e
cd "$(dirname "$0")/.."
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

render() {
  local name=$1 height=$2
  "$CHROME" --headless --disable-gpu --hide-scrollbars \
    --force-device-scale-factor=2 --window-size=1600,"$height" \
    --virtual-time-budget=6000 \
    --screenshot="$(pwd)/docs/slide-$name.png" \
    "file://$(pwd)/docs/slide-$name.html" 2>/dev/null
  echo "written: docs/slide-$name.png  ($(sips -g pixelWidth -g pixelHeight "docs/slide-$name.png" | tail -2 | tr -d ' \n'))"
}

case "${1:-all}" in
  full)     render full 872 ;;
  audit)    render audit 772 ;;
  pipeline) render pipeline 782 ;;
  *)        render full 872; render audit 772; render pipeline 782 ;;
esac
