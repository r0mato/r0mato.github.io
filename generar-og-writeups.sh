#!/usr/bin/env bash
# Regenera UNA tarjeta social por writeup (assets/img/og/<ref>-<idioma>.png).
#
# Es la imagen que sale al pegar el enlace de un writeup concreto en LinkedIn,
# X o Slack. Lleva el titular del caso y su severidad, para que cada artículo
# se vea distinto. La tarjeta general del sitio la hace ./generar-og.sh
#
#   ./generar-og-writeups.sh
#
# Vuelve a lanzarlo cuando cambies el título o la severidad de un writeup,
# o cuando publiques uno nuevo. Necesita ImageMagick y Python 3.
set -euo pipefail
cd /home/r0mato/r0mato.github.io
exec python3 -I _admin/og_writeups.py "$@"
