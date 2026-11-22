#!/usr/bin/env bash
# Abre el panel privado del blog.
#
#   ./panel.sh
#
# Arranca dos cosas en tu ordenador y nada más:
#   · Jekyll en 127.0.0.1:4100  → la vista previa en vivo
#   · El panel en 127.0.0.1:8099 → la interfaz para editar y publicar
#
# Ninguno de los dos escucha fuera de tu máquina. Ctrl+C cierra los dos.
set -euo pipefail
cd "$(dirname "$0")"

PUERTO_PANEL="${PANEL_PUERTO:-8099}"
PUERTO_JEKYLL="${JEKYLL_PUERTO:-4100}"
export PATH="$HOME/.local/share/gem/ruby/3.3.0/bin:$PATH"
export PANEL_PUERTO PUERTO_JEKYLL JEKYLL_PUERTO="$PUERTO_JEKYLL"

command -v bundle >/dev/null || { echo "Falta bundler. Instálalo con: gem install --user-install bundler"; exit 1; }
[ -d vendor/bundle ] || { echo "Instalando dependencias (solo la primera vez)…"; bundle install; }

limpiar() {
  echo
  echo "  Cerrando…"
  [ -n "${PID_JEKYLL:-}" ] && kill "$PID_JEKYLL" 2>/dev/null || true
  [ -n "${PID_PANEL:-}" ] && kill "$PID_PANEL" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap limpiar EXIT INT TERM

echo "  Arrancando la vista previa…"
bundle exec jekyll serve --drafts --livereload \
  --port "$PUERTO_JEKYLL" --host 127.0.0.1 \
  > /tmp/panel-jekyll.log 2>&1 &
PID_JEKYLL=$!

for _ in $(seq 1 40); do
  curl -s -o /dev/null "http://127.0.0.1:$PUERTO_JEKYLL/" && break
  sleep 1
done

python3 -I _admin/servidor.py &
PID_PANEL=$!

sleep 1
URL="$(cat /tmp/panel-blog-url.txt 2>/dev/null || true)"
if [ -n "$URL" ]; then
  command -v xdg-open >/dev/null && xdg-open "$URL" >/dev/null 2>&1 || true
fi

wait "$PID_PANEL"
