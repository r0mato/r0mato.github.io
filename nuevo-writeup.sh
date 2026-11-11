#!/usr/bin/env bash
# Crea el esqueleto de un writeup nuevo: fichero en _posts/ + carpeta de imágenes.
# Uso:  ./nuevo-writeup.sh "Título del writeup"
set -euo pipefail
cd "$(dirname "$0")"

[ $# -ge 1 ] || { echo "Uso: ./nuevo-writeup.sh \"Título del writeup\""; exit 1; }

TITULO="$*"
FECHA="$(date +%F)"
HORA="$(date +%H:%M:%S)"

SLUG="$(printf '%s' "$TITULO" | iconv -f UTF-8 -t ASCII//TRANSLIT 2>/dev/null || printf '%s' "$TITULO")"
SLUG="$(printf '%s' "$SLUG" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//' | cut -c1-70)"

POST="_posts/${FECHA}-${SLUG}.md"
IMGDIR="assets/img/writeups/${SLUG}"

[ -e "$POST" ] && { echo "Ya existe $POST"; exit 1; }

mkdir -p "$IMGDIR"

# Copia la plantilla ajustando título, fecha y ruta de imágenes
sed -e "s|^title:.*|title:       \"${TITULO}\"|" \
    -e "s|^date:.*|date:        ${FECHA} ${HORA} +0100|" \
    -e "s|writeups/CARPETA|writeups/${SLUG}|g" \
    plantilla-writeup.md > "$POST"

# Elimina el bloque de comentarios de cabecera de la plantilla
sed -i '/^#  *PLANTILLA DE WRITEUP/d; /^#  Copia este fichero/d; /^#  (o más fácil/d; /^# ═/d' "$POST"

printf '\n  Writeup creado\n  ──────────────\n'
printf '  Artículo : %s\n' "$POST"
printf '  Imágenes : %s/   <- mete aquí los .png\n\n' "$IMGDIR"
printf '  Siguiente paso:\n'
printf '    1. edita %s\n' "$POST"
printf '    2. git add -A && git commit -m "writeup: %s" && git push\n' "$TITULO"
printf '    3. en ~1 minuto estará publicado en /writeups/%s/\n\n' "$SLUG"
