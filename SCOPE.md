# SCOPE — Proyecto propio: blog de writeups (r0mato.github.io)

> Esto NO es un programa de bug bounty. Es un proyecto de desarrollo web sobre
> infraestructura propia del usuario. El fichero existe porque los hooks `scope-guard*`
> exigen alcance declarado antes de cualquier operación de red, incluido `127.0.0.1`.

## Datos
- Tipo: desarrollo de sitio estático (Jekyll / GitHub Pages)
- Propietario del activo: el propio usuario (cuenta GitHub `r0mato`)
- Autorización: implícita y total — activo propio
- Actividad permitida: editar ficheros, compilar el sitio, servirlo en local, abrirlo en el
  navegador, hacer `git push` al repositorio propio
- Actividad NO aplicable aquí: pruebas de intrusión, fuzzing, escaneo

## EN ALCANCE
- `127.0.0.1` / `localhost` — servidor de desarrollo de Jekyll (puerto 4100)
- `r0mato.github.io` — sitio publicado, propiedad del usuario
- `github.com/r0mato/r0mato.github.io` — repositorio propio
- `github.com`, `api.github.com` — operaciones `git push` y API sobre la cuenta propia
- `fonts.googleapis.com`, `fonts.gstatic.com` — CDN de tipografías que carga el sitio
- `www.githubstatus.com` — página pública de estado de GitHub (solo lectura, para
  diagnosticar si un despliegue se queda encolado por una incidencia suya)
- `rubygems.org` — descarga de las gemas declaradas en el Gemfile

## FUERA DE ALCANCE
- Todo lo demás. Cualquier host de un tercero.
- En particular `trytobyahacker.github.io`: se consultó UNA vez como referencia de diseño
  mediante una petición GET pública a la portada. No se prueba, no se escanea, no se toca.
