#!/usr/bin/env bash
# Crea el esqueleto de un writeup nuevo en los dos idiomas + su carpeta de imágenes.
#
#   ./nuevo-writeup.sh "Título del writeup"            -> crea la versión ES y la EN
#   ./nuevo-writeup.sh --solo-es "Título del writeup"  -> solo la versión en español
#
set -euo pipefail
cd "$(dirname "$0")"

SOLO_ES=0
if [ "${1:-}" = "--solo-es" ]; then SOLO_ES=1; shift; fi
[ $# -ge 1 ] || { echo "Uso: ./nuevo-writeup.sh [--solo-es] \"Título del writeup\""; exit 1; }

TITULO="$*"
FECHA="$(date +%F)"
HORA="$(date +%H:%M:%S)"

SLUG="$(printf '%s' "$TITULO" | iconv -f UTF-8 -t ASCII//TRANSLIT 2>/dev/null || printf '%s' "$TITULO")"
SLUG="$(printf '%s' "$SLUG" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//' | cut -c1-70)"

POST_ES="_posts/${FECHA}-${SLUG}.md"
POST_EN="_posts/${FECHA}-${SLUG}-en.md"
IMGDIR="assets/img/writeups/${SLUG}"

[ -e "$POST_ES" ] && { echo "Ya existe $POST_ES"; exit 1; }

mkdir -p "$IMGDIR"

crear() {   # $1 = destino   $2 = lang   $3 = permalink extra ("" o la ruta /en/...)
  sed -e "s|^title:.*|title:       \"${TITULO}\"|" \
      -e "s|^date:.*|date:        ${FECHA} ${HORA} +0100|" \
      -e "s|^lang:.*|lang:        ${2}|" \
      -e "s|^ref:.*|ref:         ${SLUG}|" \
      -e "s|writeups/CARPETA|writeups/${SLUG}|g" \
      plantilla-writeup.md > "$1"
  if [ -n "$3" ]; then
    # Inserta el permalink de la versión en inglés justo después de ref:
    sed -i "/^ref: /a permalink:   ${3}" "$1"
  fi
  # Quita el bloque de comentarios de cabecera de la plantilla
  sed -i '/^#  *PLANTILLA DE WRITEUP/d; /^#  Copia este fichero/d; /^#  (o más fácil/d; /^# ═/d' "$1"
}

crear "$POST_ES" "es" ""
printf '\n  Writeup creado\n  ──────────────\n'
printf '  Español  : %s\n' "$POST_ES"

if [ "$SOLO_ES" -eq 0 ]; then
  crear "$POST_EN" "en" "/en/writeups/${SLUG}/"
  printf '  Inglés   : %s\n' "$POST_EN"
fi

printf '  Imágenes : %s/   <- mete aquí los .png (las comparten los dos idiomas)\n\n' "$IMGDIR"
printf '  Siguiente paso:\n'
printf '    1. edita los ficheros (el campo ref ya empareja las dos versiones)\n'
printf '    2. bundle exec jekyll serve --port 4100   para verlo\n'
printf '    3. git add -A && git commit -m "writeup: %s" && git push\n\n' "$TITULO"
