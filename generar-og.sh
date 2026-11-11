#!/usr/bin/env bash
# Regenera la tarjeta de previsualizacion social (assets/img/brand/og.png).
#
# Es la imagen que sale al compartir un enlace del sitio en LinkedIn, X o Slack.
# Vuelve a lanzarlo si cambias tu foto, el logo o el texto de abajo.
#
#   ./generar-og.sh
#
# Necesita ImageMagick:  sudo apt install imagemagick
set -euo pipefail
cd /home/r0mato/r0mato.github.io

F_BOLD=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf
F_REG=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf
F_MONO=/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf
OUT=assets/img/brand/og.png
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# 1 · Fondo: azul muy oscuro + halo radial azul arriba a la izquierda
convert -size 1200x630 xc:'#0a1020' "$TMP/bg.png"
convert -size 1000x1000 radial-gradient:'#1b3a7a'-'#0a1020' "$TMP/glow.png"
convert "$TMP/bg.png" "$TMP/glow.png" -geometry +-340+-430 -compose screen -composite "$TMP/base.png"

# 2 · Retrato y logo, mismo tamano y mismas esquinas redondeadas
convert -size 220x220 xc:black -fill white -draw 'roundrectangle 0,0,219,219,24,24' "$TMP/mask.png"   # blanco = opaco
for n in r0mato-perfil r0mato-logo; do
  convert "assets/img/brand/$n.jpg" -resize 220x220^ -gravity center -extent 220x220 "$TMP/$n.png"
  convert "$TMP/$n.png" "$TMP/mask.png" -alpha off -compose copyopacity -composite "$TMP/${n}_r.png"
done

# 3 · Texto
convert "$TMP/base.png" \
  -font "$F_MONO" -pointsize 23 -fill '#6b9cff' \
  -annotate +80+128 'OFFENSIVE  SECURITY  RESEARCH' \
  -font "$F_BOLD" -pointsize 104 -fill '#ffffff' \
  -annotate +80+250 'r0mato' \
  -font "$F_REG" -pointsize 34 -fill '#a8b6cd' \
  -annotate +80+305 'Francisco Javier Alcaide Deus' \
  -fill '#22304d' -draw 'rectangle 80,355 760,357' \
  -font "$F_REG" -pointsize 30 -fill '#dbe4f3' \
  -annotate +80+412 'Writeups de vulnerabilidades reales' \
  -font "$F_REG" -pointsize 27 -fill '#7a8aa3' \
  -annotate +80+456 'Web y API · control negativo e impacto real' \
  -font "$F_MONO" -pointsize 22 -fill '#7a8aa3' \
  -annotate +80+556 'r0mato.github.io' \
  "$TMP/card.png"

# 4 · Logo a la derecha + franja de acento abajo
convert "$TMP/card.png" \
  "$TMP/r0mato-perfil_r.png" -geometry +850+105 -composite \
  "$TMP/r0mato-logo_r.png"   -geometry +850+355 -composite \
  -fill '#1d4ed8' -draw 'rectangle 0,624 1200,630' \
  -strip "$OUT"

echo
echo "  Tarjeta regenerada: $OUT"
identify "$OUT"
echo
echo "  Para publicarla:  git add -A && git commit -m 'tarjeta social nueva' && git push"

