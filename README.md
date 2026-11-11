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
./nuevo-writeup.sh "Título del writeup"       # crea el artículo (ES+EN) y su carpeta de imágenes
bundle exec jekyll serve --port 4100          # previsualiza en http://127.0.0.1:4100
git add -A && git commit -m "writeup: …" && git push

./cambiar-foto.sh perfil ~/foto.png           # sustituye tu retrato (o `logo`)
./generar-og.sh                               # rehace la tarjeta de previsualización social
```

El push dispara `.github/workflows/pages.yml`, que compila con el Jekyll del `Gemfile`,
comprueba enlaces e imágenes con html-proofer y, solo si todo pasa, publica.

## Estructura

```
.github/workflows/pages.yml   compila, comprueba y publica en cada push
Gemfile / Gemfile.lock        versiones exactas de Jekyll y plugins
_config.yml                   configuración, perfil, métricas de portada
_data/ui.yml                  TODOS los textos de interfaz, en español e inglés
index.html  writeups.html     portada y archivo en español
sobre-mi.md  contacto.md      páginas en español
en/                           las mismas cuatro páginas en inglés
_posts/                       writeups; `lang:` marca el idioma, `ref:` empareja
_drafts/                      writeups sin publicar (no salen en el sitio)
_layouts/                     default · page · writeup
_includes/                    head · header · footer · home · archive · severity · writeup-card
assets/css/main.scss          TODO el diseño (tokens de color en :root)
assets/js/site.js             tema, filtros, índice lateral, copiar código, lightbox
assets/img/brand/             retrato, logo y favicon
assets/img/writeups/<slug>/   imágenes de cada writeup (compartidas por los dos idiomas)
plantilla-writeup.md          plantilla base
nuevo-writeup.sh              generador de esqueleto (ES + EN)
cambiar-foto.sh               sustituye retrato o logo con el recorte correcto
generar-og.sh                 rehace assets/img/brand/og.png
```

## Licencia

Contenido de los writeups: © r0mato. El código del tema puedes reutilizarlo libremente.
