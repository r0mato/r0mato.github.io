# r0mato.github.io

Blog personal de investigación de seguridad ofensiva: writeups de vulnerabilidades
reportadas, corregidas y publicadas bajo divulgación coordinada.

Sitio estático con **Jekyll** y tema propio (sin tema de terceros), desplegado por
**GitHub Pages**.

## Cómo publicar

Lee **[PUBLICAR.md](PUBLICAR.md)** — cubre todo: crear un writeup, el front matter,
imágenes, avisos, borradores, previsualización local y personalización.

Resumen:

```bash
./nuevo-writeup.sh "Título del writeup"   # crea el artículo y su carpeta de imágenes
jekyll serve --port 4100                  # previsualiza en http://127.0.0.1:4100
git add -A && git commit -m "writeup: …" && git push
```

## Estructura

```
_config.yml                   configuración, perfil, métricas de portada
index.html                    portada
writeups.html                 archivo con filtros y búsqueda
metodologia.md sobre-mi.md contacto.md
_posts/                       los writeups publicados
_drafts/                      writeups sin publicar (no salen en el sitio)
_layouts/                     default · page · writeup
_includes/                    head · header · footer · severity · writeup-card
assets/css/main.scss          TODO el diseño (tokens de color en :root)
assets/js/site.js             tema, filtros, índice lateral, copiar código, lightbox
assets/img/writeups/<slug>/   imágenes de cada writeup
plantilla-writeup.md          plantilla base
nuevo-writeup.sh              generador de esqueleto
```

## Licencia

Contenido de los writeups: © r0mato. El código del tema puedes reutilizarlo libremente.
