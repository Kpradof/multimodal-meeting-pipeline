#!/bin/bash
# Copy the finished post and slides into one folder, in the order they get used.
# Run after build_post.py or build_slide.sh so the copies stop going stale.
set -e
cd "$(dirname "$0")/.."
D="PARA PUBLICAR"
mkdir -p "$D"
cp out/post_final.txt        "$D/1 - texto del post.txt"
cp docs/slide-full.png       "$D/2 - imagen.png"
cp docs/slide-audit.png      "$D/alterna - solo validador.png"
cp docs/slide-pipeline.png   "$D/alterna - solo pipeline.png"
echo "$D actualizada:"
ls -1 "$D"
