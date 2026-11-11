# Guía de publicación

Todo lo que necesitas para poner el blog en marcha y publicar writeups nuevos con imágenes.
No hace falta que instales nada: **GitHub compila el sitio por ti cada vez que haces `push`**.

---

## Chuleta: lo que vas a hacer el 90 % de las veces

Todo se hace desde `~/r0mato.github.io`. Los tres comandos que importan:

```bash
# 1 · escribir un writeup nuevo (crea el fichero en español y en inglés)
./nuevo-writeup.sh "Título del writeup"

# 2 · verlo antes de publicarlo
bundle exec jekyll serve --port 4100        # -> http://127.0.0.1:4100

# 3 · publicarlo
git add -A && git commit -m "writeup: lo que sea" && git push
```

Y dos más, para las fotos:

```bash
./cambiar-foto.sh perfil ~/ruta/foto-nueva.png   # tu cara
./cambiar-foto.sh logo   ~/ruta/logo-nuevo.png   # tu logo
```

**Nada se publica roto.** Cada `push` dispara una comprobación en GitHub: si una imagen
apunta a una ruta que no existe, si un enlace interno está mal o si el front matter tiene
un error de sintaxis, el despliegue **falla y no publica**. El sitio anterior se queda tal
cual estaba. El error exacto, con fichero y línea, aparece en:
**https://github.com/r0mato/r0mato.github.io/actions**

---

## Índice

1. [Puesta en marcha (solo una vez)](#1-puesta-en-marcha-solo-una-vez)
2. [Publicar un writeup nuevo](#2-publicar-un-writeup-nuevo)
3. [Imágenes: dónde van y cómo se ponen](#3-imágenes-dónde-van-y-cómo-se-ponen)
4. [Elementos que puedes usar dentro del artículo](#4-elementos-que-puedes-usar-dentro-del-artículo)
5. [Los dos idiomas](#4-bis-los-dos-idiomas)
6. [Cambiar tu foto o tu logo](#4-ter-cambiar-tu-foto-o-tu-logo)
7. [Borradores](#5-borradores)
8. [Ver el sitio en local antes de publicar](#6-ver-el-sitio-en-local-antes-de-publicar)
9. [Personalizar textos, colores y datos](#7-personalizar-textos-colores-y-datos)
10. [Checklist antes de cada publicación](#8-checklist-antes-de-cada-publicación)
11. [Si algo sale mal](#si-algo-sale-mal)
12. [Dominio propio (opcional)](#9-dominio-propio-opcional)

---

## 1. Puesta en marcha (solo una vez)

### 1.1 Crear el repositorio

El repositorio **tiene que llamarse exactamente `r0mato.github.io`** (tu usuario + `.github.io`).
Ese nombre es lo que hace que el sitio se publique en la raíz del dominio, sin `/repo/` detrás.

En GitHub: **New repository** → nombre `r0mato.github.io` → **Public** → *sin* README, *sin*
.gitignore, *sin* licencia (ya los tienes aquí) → **Create**.

### 1.2 Subir el sitio

Desde la carpeta del proyecto:

```bash
cd ~/r0mato.github.io

git init -b main
git add -A
git commit -m "Sitio inicial: tema propio + primer writeup"
git remote add origin git@github.com:r0mato/r0mato.github.io.git
git push -u origin main
```

> Si no tienes clave SSH configurada en GitHub, usa la URL HTTPS en su lugar:
> `https://github.com/r0mato/r0mato.github.io.git` (te pedirá usuario y un *personal access token*).

### 1.3 Activar GitHub Pages

En el repositorio: **Settings → Pages → Build and deployment → Source: `GitHub Actions`**.

Con esa opción el sitio lo compila **nuestro propio workflow**
(`.github/workflows/pages.yml`) con el Jekyll del `Gemfile`, el mismo que usas en local.
La alternativa (`Deploy from a branch`) usa una versión antigua y fija de Jekyll que
GitHub controla, y provoca fallos que en local no aparecen.

En uno o dos minutos el sitio estará en **https://r0mato.github.io**.
Cada `push` posterior lo reconstruye solo.

### 1.4 Qué hace el workflow en cada push

1. Instala Ruby y las gemas exactas del `Gemfile.lock` (con caché, así tarda ~40 s).
2. Compila el sitio con `JEKYLL_ENV=production`.
3. Pasa **html-proofer**: si hay una imagen con la ruta mal escrita o un enlace interno
   roto, **falla y no publica**. El sitio anterior sigue en línea intacto.
4. Si todo está bien, despliega.

En un *pull request* ejecuta los pasos 1–3 pero **no** publica: sirve para validar un
writeup antes de fusionarlo.

Si algo falla, la pestaña **Actions** del repositorio muestra el log con el error exacto
(lo más habitual: un `---` mal cerrado o comillas sin cerrar en el front matter, o una
ruta de imagen equivocada).

---

## 2. Publicar un writeup nuevo

### Opción rápida (recomendada)

```bash
cd ~/r0mato.github.io
./nuevo-writeup.sh "ATO por token de reset reutilizable en el flujo de invitación"
```

El script hace cuatro cosas:

- crea la versión en **español**: `_posts/2026-11-20-<slug>.md`,
- crea la versión en **inglés**: `_posts/2026-11-20-<slug>-en.md`, ya con su `permalink`
  bajo `/en/writeups/`,
- pone el mismo `ref:` en las dos, que es lo que las empareja para el botón ES/EN,
- crea la carpeta de imágenes `assets/img/writeups/<slug>/`, **compartida por los dos
  idiomas** (no dupliques capturas).

Si de momento solo quieres la versión española: `./nuevo-writeup.sh --solo-es "Título"`.
El botón de idioma llevará entonces al archivo en inglés en lugar de a una traducción.

### Opción manual

Copia `plantilla-writeup.md` a `_posts/` con este nombre exacto:

```
_posts/AAAA-MM-DD-titulo-en-minusculas-con-guiones.md
```

La fecha del nombre del fichero **es obligatoria** y define el orden. El título del fichero
se convierte en la URL: `https://r0mato.github.io/writeups/titulo-en-minusculas-con-guiones/`.

> **Cuidado con las fechas futuras.** Jekyll **omite silenciosamente** cualquier post cuya
> fecha sea posterior al momento del build: no da error, simplemente no aparece. Si publicas
> un writeup y no sale en el sitio, lo primero que hay que mirar es la fecha —tanto la del
> nombre del fichero como la del campo `date`— y la zona horaria (`+0100`).
> Para forzar que se publique igualmente: `bundle exec jekyll build --future`.

### El front matter (la cabecera entre `---`)

Es lo que pinta la ficha del archivo y la tabla de metadatos del artículo:

| Campo | Qué hace | Obligatorio |
|---|---|---|
| `title` | Título del artículo y de la ficha | **sí** |
| `summary` | Resumen bajo el título y texto de la ficha | **sí** |
| `date` | Fecha y hora de publicación | **sí** |
| `severity` | Pinta la píldora de color: `critical`, `high`, `medium`, `low`, `info` | **sí** |
| `cvss` | Puntuación, p.ej. `"8.6"` | no |
| `cvss_vector` | Vector completo CVSS v3.1 | no |
| `cwe` | p.ej. `"CWE-639"` | no |
| `vuln_class` | Clase; **genera los botones de filtro** del archivo | recomendado |
| `target_type` | p.ej. `"API REST"`, `"App Android"` | no |
| `platform` | `HackerOne`, `YesWeHack`, `Programa privado`… | no |
| `status` | `Corregido`, `Triado`, `Mitigado` | no |
| `fixed` | Tiempo hasta el arreglo, p.ej. `"9 días"` | no |
| `reward` | `"Recompensado"` o el importe. Vacío = no se muestra | no |
| `tags` | Lista; se usa para la búsqueda del archivo | recomendado |
| `takeaways` | Lista; pinta la caja de conclusiones del final | recomendado |
| `disclosure` | Sobrescribe el aviso legal del pie del artículo | no |

Los campos que dejes vacíos o borres **simplemente no se muestran**: nada se rompe.

### Publicarlo

```bash
git add -A
git commit -m "writeup: ATO por token de reset reutilizable"
git push
```

Y ya está. Un minuto después está online.

---

## 3. Imágenes: dónde van y cómo se ponen

### Dónde

Una carpeta por writeup, con el mismo nombre que el artículo:

```
assets/img/writeups/<slug-del-writeup>/01-peticion.png
assets/img/writeups/<slug-del-writeup>/02-control-negativo.png
assets/img/writeups/<slug-del-writeup>/03-diagrama.svg
```

Numéralas por orden de aparición: así sabes cuál es cuál dentro de seis meses.

### Cómo se referencian

**Forma recomendada — con pie de foto:**

```html
<figure>
  <img src="{{ '/assets/img/writeups/mi-writeup/01-peticion.png' | relative_url }}"
       alt="Descripción de lo que se ve, para accesibilidad y SEO">
  <figcaption>Pie de imagen: dile al lector <strong>qué tiene que mirar</strong>.</figcaption>
</figure>
```

**Forma corta — sin pie:**

```markdown
![Descripción de la imagen]({{ '/assets/img/writeups/mi-writeup/01-peticion.png' | relative_url }})
```

> El `| relative_url` no es decorativo: hace que la ruta funcione igual en local y en
> producción. Úsalo siempre.

Las imágenes del artículo se **amplían al hacer clic** (se abre a pantalla completa, se
cierra con clic o con `Esc`). No tienes que hacer nada: funciona solo.

### Flujo práctico para una captura

```bash
# 1. Captura con Flameshot y guárdala directamente en la carpeta del writeup
flameshot gui -p ~/r0mato.github.io/assets/img/writeups/mi-writeup/

# 2. Renómbrala con orden y sentido
cd ~/r0mato.github.io/assets/img/writeups/mi-writeup/
mv Captura_*.png 01-peticion-repeater.png

# 3. Opcional pero recomendable: optimizar el peso
optipng -o5 *.png          # o:  pngquant --quality=70-90 --ext .png --force *.png
```

### Recomendaciones de formato

| Tipo de evidencia | Formato | Notas |
|---|---|---|
| Captura de Burp, navegador, terminal | **PNG** | ancho ideal 1200–1600 px; por debajo de 500 KB |
| Diagrama de flujo de ataque | **SVG** | se ve nítido a cualquier zoom y pesa nada |
| Secuencia o condición de carrera | **GIF** o **MP4** | GIF < 3 MB; para MP4 usa `<video controls>` |
| Foto o pantallazo con muchos colores | **JPG** | calidad 80 |

GitHub no admite ficheros de más de 100 MB, pero mucho antes de eso la página se vuelve
lenta. **Regla práctica: ninguna imagen por encima de 1 MB.**

### Antes de subir una captura: táchala

Esto es lo que diferencia un blog que a las empresas les gusta de uno que les da miedo:

- Tokens, cookies y cabeceras `Authorization`: **recórtalos o tápalos**, no los dejes
  "medio visibles". Un `eyJ...` completo es una credencial.
- Dominios de cliente, si el programa no autoriza nombrarlos: sustitúyelos por
  `api.ejemplo-objetivo.tld`.
- Datos personales de terceros: no deberían ni existir en tu captura. Usa cuentas canario
  tuyas y datos sembrados por ti.
- Direcciones IP internas, nombres de empleados, rutas con tu usuario del sistema.

Para tachar: Flameshot tiene herramienta de rectángulo relleno y de pixelado. **Píxelalo
grueso o tápalo con un rectángulo opaco** — el pixelado fino se puede revertir.

### Imagen de portada para redes (opcional)

Si quieres que al compartir el enlace en LinkedIn o X salga una imagen, añade al front
matter del writeup:

```yaml
image: /assets/img/writeups/mi-writeup/01-peticion.png
```

El plugin `jekyll-seo-tag` ya está activo y la usará como `og:image`.

---

## 4. Elementos que puedes usar dentro del artículo

### Avisos de colores

```html
<div class="note" markdown="1">
Azul. Para contexto, matices y aclaraciones metodológicas.
</div>

<div class="warn" markdown="1">
Naranja. Para advertencias y precondiciones del ataque.
</div>

<div class="impact" markdown="1">
**Impacto.** Rojo. Para el párrafo de impacto de negocio: es el que lee el responsable.
</div>
```

El `markdown="1"` es necesario para que dentro del bloque sigan funcionando las negritas,
los enlaces y el `código`.

### Bloques de código

Indica el lenguaje después de las tres comillas para que coloree bien:

~~~
```http      ← peticiones y respuestas HTTP
```javascript ← fragmentos de bundles
```json
```bash
```python
```
~~~

Todos los bloques tienen botón de **copiar** automático.

### Tablas

```markdown
| Cuenta | Organización | Rol |
|---|---|---|
| canario-a | 4417 | Miembro |
| canario-b | 8831 | Propietario |
```

### Cita destacada

```markdown
> **Hipótesis declarada antes de probar:** …
```

### Índice lateral

Se genera **solo** a partir de tus `##` y `###`. No tienes que escribirlo. Si el artículo
tiene menos de dos encabezados, el índice se oculta.

---

## 4-bis. Los dos idiomas

El sitio está completo en español y en inglés. El botón **ES / EN** de la cabecera lleva
siempre a la página equivalente, no a la portada.

| Español | Inglés | Fichero |
|---|---|---|
| `/` | `/en/` | `index.html` · `en/index.html` |
| `/writeups/` | `/en/writeups/` | `writeups.html` · `en/writeups.html` |
| `/sobre-mi/` | `/en/about/` | `sobre-mi.md` · `en/about.md` |
| `/contacto/` | `/en/contact/` | `contacto.md` · `en/contact.md` |

Cómo funciona, en tres reglas:

1. **Cada página declara su idioma** con `lang: es` o `lang: en` en el front matter.
2. **Las páginas fijas se emparejan con `alt_url:`** (la ruta de su equivalente).
3. **Los writeups se emparejan con `ref:`**: el mismo valor en las dos versiones. El archivo
   de cada idioma solo muestra los writeups de ese idioma, y el botón ES/EN salta entre las
   dos versiones del mismo caso.

Si un writeup solo existe en español, su botón EN lleva al archivo inglés en vez de a una
página rota.

**Los textos de la interfaz** —menú, botones, «min de lectura», «En esta página», el aviso
legal del final de cada writeup— están **todos** en `_data/ui.yml`, en los dos idiomas.
Cambias una palabra ahí y cambia en todo el sitio. No la busques en los layouts.

## 4-ter. Cambiar tu foto o tu logo

Las dos imágenes viven en `assets/img/brand/`:

| Fichero | Qué es | Tamaño |
|---|---|---|
| `r0mato-perfil.jpg` | tu cara, en «Sobre mí» | 640×640 |
| `r0mato-logo.jpg` | tu logo, en «Sobre mí» y en la cabecera | 300×300 |
| `og.png` | la tarjeta al compartir enlaces | 1200×630 |

### La forma fácil

```bash
./cambiar-foto.sh perfil ~/Escritorio/foto-nueva.png
./cambiar-foto.sh logo   ~/Escritorio/logo-nuevo.png
```

Acepta cualquier tamaño y formato: recorta al centro en cuadrado sin deformar, lo deja al
tamaño correcto, lo optimiza y **regenera la tarjeta social**, que lleva las dos imágenes
dentro. Luego `git push` y listo.

### La forma manual

Sustituye el fichero **conservando el mismo nombre** y, si quieres, regenera la tarjeta:

```bash
cp ~/mi-foto.jpg assets/img/brand/r0mato-perfil.jpg
./generar-og.sh
```

Si le pones otro nombre tendrás que cambiar las rutas en `sobre-mi.md`, `en/about.md`,
`_includes/header.html` y `generar-og.sh`. Por eso es más cómodo reusar el nombre.

> **Encuadre.** La foto se muestra en un cuadrado de 132 px junto al logo. Si tu cara
> queda pequeña dentro del marco, la foto se verá «más pequeña» que el logo aunque el
> marco sea idéntico: recorta tú el cuadrado pegado a la cara antes de pasarlo al script.

---

## 5. Borradores

Un writeup que todavía no quieres publicar va en `_drafts/` **sin fecha en el nombre**:

```
_drafts/pendiente-de-permiso-del-programa.md
```

No aparece en el sitio publicado. Para verlo en local: `bundle exec jekyll serve --drafts`.
Cuando lo publiques, muévelo a `_posts/` con la fecha delante del nombre.

---

## 6. Ver el sitio en local antes de publicar

```bash
cd ~/r0mato.github.io
bundle exec jekyll serve --port 4100 --livereload
```

Abre **http://127.0.0.1:4100**. Cada vez que guardes un fichero se recarga solo.

Las dependencias ya están instaladas en `vendor/bundle`. Si alguna vez te falta alguna:

```bash
bundle install
```

> **Usa siempre `bundle exec`.** Es lo que garantiza que compiles con el mismo Jekyll
> (4.4.1) y los mismos plugins que usa GitHub Actions al publicar. Sin `bundle exec`
> podrías estar compilando con otra versión y ver algo distinto a lo que se publica.

### Comprobar enlaces e imágenes antes de publicar

```bash
bundle exec jekyll build
bundle exec htmlproofer ./_site --disable-external --allow-hash-href
```

Esto detecta rutas de imagen mal escritas y enlaces internos rotos — el error más común
al publicar un writeup. **El workflow lo ejecuta solo en cada push**, así que si algo está
roto no llega a publicarse, pero correrlo en local te ahorra el viaje de ida y vuelta.

---

## 7. Personalizar textos, colores y datos

| Qué quieres cambiar | Dónde |
|---|---|
| Tu nombre, bio, correo, redes, usuarios de plataformas | `_config.yml` → bloque `author` |
| Los 4 números grandes de la portada | `_config.yml` → bloque `stats` |
| El mensaje de la franja azul oscura | `_config.yml` → bloque `cta` |
| Titular y texto del hero | `index.html` (primeras 25 líneas) |
| Los 4 pasos de "Cómo trabajo" | `index.html` → sección `.steps` |
| El texto de Sobre mí / Contacto (español) | `sobre-mi.md`, `contacto.md` |
| El texto de About / Contact (inglés) | `en/about.md`, `en/contact.md` |
| **Menú, botones y etiquetas, en los dos idiomas** | `_data/ui.yml` |
| Titular de la portada | `index.html` y `en/index.html` (front matter) |
| Tus fotos | `assets/img/brand/r0mato-perfil.jpg` y `r0mato-logo.jpg` |
| **Colores de toda la marca** | `assets/css/main.scss` → bloque `:root` (arriba del todo) |
| Colores del modo oscuro | `assets/css/main.scss` → `:root[data-theme="dark"]` |
| Aviso legal del final de cada writeup | `_layouts/writeup.html` → `page.disclosure` |
| Enlaces del menú | `_includes/header.html` |

Para cambiar el color principal de todo el sitio basta con tocar una línea:

```css
--accent: #1d4ed8;   /* azul actual */
```

---

## 8. Checklist antes de cada publicación

- [ ] El fallo está **corregido** y el programa **autoriza** la publicación.
- [ ] No aparece el nombre del cliente si el programa no lo permite.
- [ ] Ningún token, cookie o credencial legible en texto ni en imágenes.
- [ ] Ningún dato de usuario real: solo cuentas canario propias.
- [ ] El artículo incluye el **control negativo**. Sin él, el writeup no demuestra nada.
- [ ] `severity` y `cvss` coinciden con lo que aceptó el programa.
- [ ] Todas las imágenes cargan en local antes de hacer `push`.
- [ ] Los `alt` de las imágenes describen lo que se ve.
- [ ] La fecha **no** está en el futuro (si no, el post no se publica y no avisa).
- [ ] Si has escrito las dos versiones, las dos llevan el **mismo `ref:`**.

Si algo de esto se te escapa en una ruta de imagen o un enlace, el workflow lo detecta y
**no publica**: te lo dice en Actions con el fichero y la línea exactos, y el sitio anterior
sigue en línea sin tocar.

---

## Si algo sale mal

**El sitio no se actualiza después de un push.**
Mira https://github.com/r0mato/r0mato.github.io/actions. Si el último run está en rojo, el
despliegue se detuvo a propósito: abre el run y el paso que falló te dice qué y dónde. Lo
más habitual es una ruta de imagen mal escrita o unas comillas sin cerrar en el front
matter. El sitio sigue mostrando la versión anterior, así que no hay prisa.

**Un writeup no aparece.**
Casi siempre es la fecha: Jekyll omite en silencio los posts con fecha futura. Comprueba
la del nombre del fichero y la del campo `date`.

**He cambiado los estilos y no veo el cambio.**
El CSS se sirve con `?v=` y cambia en cada despliegue, así que no debería pasar. Si pasa,
`Ctrl+Shift+R`.

**La he liado y quiero volver atrás.**

```bash
git log --oneline          # busca el commit bueno
git revert <hash>          # deshace ese commit creando otro encima
git push
```

`git revert` no borra historia: crea un commit que deshace el anterior. Es la forma segura.

**Quiero ver qué voy a publicar antes de hacer push.**

```bash
git status      # qué ficheros han cambiado
git diff        # qué ha cambiado exactamente dentro de ellos
```

---

## 9. Dominio propio (opcional)

Si algún día quieres `r0mato.es` en lugar de `r0mato.github.io`:

1. Crea un fichero llamado `CNAME` en la raíz del repositorio con una sola línea:
   `r0mato.es`
2. En tu proveedor de DNS, crea cuatro registros `A` del dominio raíz apuntando a
   `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`,
   y un `CNAME` de `www` hacia `r0mato.github.io`.
3. En **Settings → Pages**, escribe el dominio y marca **Enforce HTTPS**.
4. Cambia `url:` en `_config.yml` al dominio nuevo.
