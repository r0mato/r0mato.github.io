---
title:       "Toma de cuenta completa con cuatro caracteres: el código de emparejamiento que no era de nadie"
summary:     "El código que escribes para vincular la aplicación con tu televisor no estaba atado a nadie. Cualquiera podía pedir uno, convencerte de que lo teclearas y salir de ahí con una credencial permanente, tu correo y el token de recuperación de contraseña."
date:        2026-10-20 19:15:00 +0100
lang:        es
ref:         ato-codigo-emparejamiento
image:       /assets/img/og/ato-codigo-emparejamiento-es.png

severity:    high
cvss:        "8.8"
cvss_vector: "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:U/C:H/I:H/A:H"
cwe:         "CWE-287 · CWE-640"
vuln_class:  "Autenticación"
target_type: "API de aplicación de escritorio"
platform:    "YesWeHack"
status:      "Reportado"
tags:        [ato, emparejamiento, oauth, recuperacion-de-contrasena, dispositivos]

takeaways:
  - "Un código de emparejamiento que no está atado a quien lo pidió es un cheque al portador."
  - "Si una pantalla te pide confirmar algo, tiene que decirte **qué** estás confirmando. «¿Autorizas este dispositivo?» sin nombre, tipo ni ubicación no es consentimiento informado."
  - "El token de recuperación de contraseña es equivalente a la contraseña. No debería poder leerse desde una credencial de dispositivo."
  - "Si cambiar la contraseña no echa al atacante, el incidente no se ha cerrado: solo lo parece."
---

Aquí no hay una línea de código roto: todo funciona como está programado. Lo que está mal
es el diseño, y la única acción que hace falta de la víctima es teclear cuatro caracteres.

El flujo legítimo es el de media humanidad: el televisor muestra un código corto, tú lo
escribes en el móvil donde ya tienes sesión, y el televisor queda vinculado. Funciona
porque se asume que quien escribe el código está mirando la pantalla donde aparece. Ese
supuesto es el que se rompe.

## 1 · Pedir un código sin tener cuenta

Lo único que hace falta es la clave pública del cliente, que viene dentro del instalador.

```http
GET /v2/devices/pin HTTP/2
Host: api.ejemplo.tld
x-app-key: <clave pública del cliente, extraída del instalador>
```

```json
{ "users_id": null, "pin": "7MTU" }
```

<figure>
  <img src="{{ '/assets/img/writeups/ato-codigo-emparejamiento/01-pin-sin-dueno.png' | relative_url }}"
       alt="Terminal: una peticion curl con solo la cabecera x-app-key, sin sesion, al endpoint de pin de dispositivos. La respuesta es users_id null y pin 7MTU">
  <figcaption>Una petición con la clave pública de la aplicación y nada más. El servidor emite el código: <code>users_id: null</code>, <code>pin: "7MTU"</code>. Van tapados la clave y el host.</figcaption>
</figure>

**`users_id: null`**: un código que no pertenece a nadie, un hueco esperando a que alguien
lo rellene. Lo rellena quien lo teclee.

## 2 · La pantalla no dice qué estás autorizando

Cuando la víctima teclea el código aparece una confirmación, y no decía nada del aparato
que lo había pedido: ni nombre, ni tipo, ni IP, ni ubicación. Solo «¿Autorizar este
dispositivo?» y un botón. No hay forma de distinguir tu televisor del portátil de un
desconocido. No es descuido de la víctima: es que no le dan la información para decidir.

<figure>
  <img src="{{ '/assets/img/writeups/ato-codigo-emparejamiento/02-consentimiento.svg' | relative_url }}"
       alt="Comparación entre la pantalla de confirmación real, que solo muestra la pregunta y el código, y una que incluiría cliente, dirección IP, ubicación y hora de la solicitud">
  <figcaption>A la izquierda, lo que se le pedía autorizar. A la derecha, lo que hacía falta para poder decidir.</figcaption>
</figure>

<figure>
  <img src="{{ '/assets/img/writeups/ato-codigo-emparejamiento/02-pin-ya-de-la-victima.png' | relative_url }}"
       alt="Respuesta del servidor para el mismo codigo 7MTU: el campo users_id ya no es null, ahora contiene el identificador de la victima, tapado">
  <figcaption>El mismo código, <code>7MTU</code>, después de que la víctima teclee cuatro caracteres. El hueco vacío se ha llenado con ella: <code>users_id</code> ya no es <code>null</code>.</figcaption>
</figure>

## 3 · El canje devuelve una credencial permanente

Antes de que la víctima confirme, el canje falla con `"user not valid"`. Después de que
confirme, **exactamente la misma petición**:

```http
POST /v2/devices/pin/accesstoken HTTP/2
Host: api.ejemplo.tld
x-app-key: <clave pública>

{"pin":"7MTU"}
```

Y entrega un token y su secreto sin cabecera de autenticación, sin cookie y sin firma. No
comprueba quién recoge el premio, solo que alguien dijo «sí» a ese código.

<figure>
  <img src="{{ '/assets/img/writeups/ato-codigo-emparejamiento/03-credencial-permanente.png' | relative_url }}"
       alt="Respuesta del canje: un objeto con token, tokenSecret, fecha de creacion y el consumidor OAuth, con deviceType android y active 1. Los valores sensibles van tapados">
  <figcaption>Lo que devuelve el canje: un <code>token</code> y su <code>tokenSecret</code>, con <code>active: 1</code> y sin fecha de caducidad. Una credencial de dispositivo completa, entregada a quien pidió el código.</figcaption>
</figure>

## 4 · De credencial de dispositivo a contraseña

Firmando con ella:

```http
GET /users/me HTTP/2
Host: api.ejemplo.tld
Authorization: <firma con el token y el secreto del dispositivo>
```

Además del correo, en la respuesta venía el **token de recuperación de contraseña**.

<figure>
  <img src="{{ '/assets/img/writeups/ato-codigo-emparejamiento/04-token-de-recuperacion.png' | relative_url }}"
       alt="Respuesta del perfil leida con la credencial del dispositivo: entre los campos aparecen user_email, user_name, new_recover_token y temp_recover_token, todos con su valor tapado">
  <figcaption>El perfil, leído con la credencial del dispositivo. Entre los campos está <code>new_recover_token</code>: el mecanismo para recuperar la cuenta, legible desde un aparato vinculado. Los valores van tapados; los nombres de campo son el hallazgo.</figcaption>
</figure>

Ese token es equivalente a la contraseña: quien lo tiene puede cambiarla. Un aparato
vinculado no debería poder leerlo; son dos niveles de confianza distintos.

Lo comprobé con el control que le da sentido: antes de pedir una recuperación el campo
venía vacío; después de pedirla desde el formulario público —solo con un correo— la misma
lectura devolvía el token real. Y la cadena se cierra sola:

```http
POST /api/recover/puk          ← canjear el token leído
→ set-cookie: sesión completa, válida un año
```

Siguiendo esa sesión hasta la pantalla de cambio de contraseña, el campo oculto de
«contraseña actual» venía **ya relleno** con el mismo token. Nunca hace falta conocer la
original.

## La cadena

```
Sin cuenta de ningún tipo
 → pedir un código con la clave pública del cliente        ← nadie es su dueño
 → la víctima teclea 4 caracteres                          ← única acción suya
 → canjear el código: credencial de dispositivo permanente ← sin autenticación
 → leer el perfil firmando con esa credencial              ← correo + token de recuperación
 → canjear el token: sesión completa de un año
 → cambiar la contraseña sin conocer la anterior
```

<figure>
  <img src="{{ '/assets/img/writeups/ato-codigo-emparejamiento/01-cadena.svg' | relative_url }}"
       alt="Diagrama de los seis pasos de la cadena, desde pedir un código sin cuenta hasta cambiar la contraseña sin conocer la anterior">
  <figcaption>Cada paso es razonable por separado. Puestos en fila, entregan la cuenta.</figcaption>
</figure>

Seis peticiones y cuatro caracteres.

## Cambiar la contraseña no echa al atacante

Lo que él tiene no es la contraseña, es la credencial de dispositivo del paso 3, y esa
sobrevive al cambio. La víctima hace lo que recomienda cualquier guía, cree que ha cerrado
el incidente, y el atacante puede repetir la cadena entera cuando quiera. La única limpieza
real es borrar ese dispositivo de la lista, y a nadie se le ocurre relacionar «me han
entrado» con «tengo un televisor de más».

## Impacto

<div class="impact" markdown="1">
**Impacto.** Toma de control total de la cuenta por un atacante que **nunca tuvo cuenta en
el servicio**, con una sola acción de la víctima: teclear cuatro caracteres en una pantalla
que no le dice qué está autorizando. El atacante obtiene el correo, una credencial
permanente de dispositivo y la capacidad de cambiar la contraseña. El propietario legítimo
queda fuera de una cuenta cuya contraseña él nunca cambió, y el consejo habitual —cambiarla
de nuevo— no expulsa al atacante.
</div>
