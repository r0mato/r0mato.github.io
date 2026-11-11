#!/usr/bin/env bash
# Sustituye tu retrato o tu logo por una imagen nueva, con el recorte y el peso
# correctos, y regenera la tarjeta social.
#
#   ./cambiar-foto.sh perfil ~/Escritorio/foto-nueva.png
#   ./cambiar-foto.sh logo   ~/Escritorio/logo-nuevo.png
#
# Acepta PNG, JPG o WEBP de cualquier tamaño: recorta al centro en cuadrado,
# lo deja a 640 px (retrato) o 300 px (logo) y lo guarda como JPG optimizado.
#
# Necesita ImageMagick:  sudo apt install imagemagick
set -euo pipefail
cd "$(dirname "$0")"

uso() {
  echo "Uso: ./cambiar-foto.sh perfil|logo <ruta de la imagen>"
  echo
  echo "  perfil  -> assets/img/brand/r0mato-perfil.jpg   (640x640, la foto de tu cara)"
  echo "  logo    -> assets/img/brand/r0mato-logo.jpg     (300x300, tu logo)"
  exit 1
}

[ $# -eq 2 ] || uso
QUE="$1"; ORIGEN="$2"

[ -f "$ORIGEN" ] || { echo "No existe el fichero: $ORIGEN"; exit 1; }
command -v convert >/dev/null || { echo "Falta ImageMagick: sudo apt install imagemagick"; exit 1; }

case "$QUE" in
  perfil) DESTINO="assets/img/brand/r0mato-perfil.jpg"; LADO=640 ;;
  logo)   DESTINO="assets/img/brand/r0mato-logo.jpg";   LADO=300 ;;
  *) uso ;;
esac

echo "  Original : $(identify -format '%wx%h %b' "$ORIGEN")"

# -resize ^ + -extent recorta al centro para dejarlo cuadrado sin deformar
convert "$ORIGEN" \
  -auto-orient \
  -resize "${LADO}x${LADO}^" \
  -gravity center -extent "${LADO}x${LADO}" \
  -strip -quality 88 \
  "$DESTINO"

echo "  Guardado : $DESTINO  ($(identify -format '%wx%h %b' "$DESTINO"))"

# La tarjeta social lleva las dos imágenes dentro: hay que rehacerla
if [ -x ./generar-og.sh ]; then
  ./generar-og.sh >/dev/null
  echo "  Tarjeta social regenerada: assets/img/brand/og.png"
fi

cat <<'FIN'

  Compruébalo antes de publicar:
    bundle exec jekyll serve --port 4100     ->  http://127.0.0.1:4100/sobre-mi/

  Y cuando te guste:
    git add -A && git commit -m "foto nueva" && git push

  Si la cara queda descentrada, recorta tú el cuadrado a mano (en cualquier
  editor) y vuelve a pasar la imagen ya cuadrada por este script.
FIN
