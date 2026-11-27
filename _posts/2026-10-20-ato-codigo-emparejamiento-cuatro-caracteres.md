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

Este fallo me gusta especialmente porque no hay ni una línea de código roto. Todo funciona
exactamente como está programado. Lo que está mal es **el diseño**: una cadena de
decisiones razonables por separado que, puestas en fila, entregan la cuenta.

Y porque la única acción que hace falta de la víctima es **teclear cuatro caracteres** en
una pantalla que la propia aplicación le pide que use.

<div class="warn" markdown="1">
**Todo está anonimizado.** Publicado con permiso del programa y sin identificar al
producto: empresa, dominios y nombres de campo están cambiados. El mecanismo es exacto.
</div>

## El flujo legítimo, el que usa todo el mundo

Hay aplicaciones que también funcionan en un televisor. Como escribir una contraseña con
el mando es una tortura, casi todas usan el mismo patrón:

1. El televisor muestra un **código corto**: cuatro caracteres.
2. Tú abres la aplicación en el móvil, donde ya tienes la sesión iniciada.
3. Escribes el código.
4. El televisor queda vinculado a tu cuenta.

Es el mismo patrón que usan las aplicaciones de las *smart TV* de medio
mundo. Lo has hecho veinte veces. Y funciona porque se asume que **quien escribe el código
está mirando la pantalla donde aparece** — es decir, que los dos aparatos están en la misma
habitación.

Ese supuesto es el que se rompe aquí.

## Parte 1: pedir un código sin tener cuenta

Lo primero que probé fue pedir uno de esos códigos directamente a la API, sin sesión y sin
cuenta. Lo único que hace falta es la clave pública de la aplicación — que, por ser
pública, viene dentro del propio instalador y la puede leer cualquiera.

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

Fíjate en el detalle que lo decide todo: **`users_id: null`**.

El servidor me acaba de dar un código **que no pertenece a nadie**. Es un
hueco vacío esperando a que alguien lo rellene. Y lo rellena quien lo teclee.

Un código así no debería existir sin estar atado desde el primer segundo a la sesión del
aparato que lo pidió.

## Parte 2: la pantalla que no dice qué estás autorizando

Aquí viene la parte que el reporte explica con más cuidado, porque es la que decide si esto
es explotable en el mundo real o solo en un laboratorio.

Cuando la víctima teclea el código en su aplicación, aparece una confirmación. Y esa
confirmación **no decía nada del aparato que lo había pedido**: ni nombre, ni tipo, ni
dirección IP, ni ubicación aproximada.

La víctima ve algo parecido a *«¿Autorizar este dispositivo?»* y un botón.
No hay forma humana de distinguir su propio televisor del portátil de un desconocido al
otro lado del país. No es que la víctima sea descuidada: **es que no le están dando la
información para decidir**.

Por eso una pantalla de consentimiento que no describe lo que estás autorizando no es una
protección. Es un trámite.

<figure>
  <img src="{{ '/assets/img/writeups/ato-codigo-emparejamiento/02-consentimiento.svg' | relative_url }}"
       alt="Comparación entre la pantalla de confirmación real, que solo muestra la pregunta y el código, y una que incluiría cliente, dirección IP, ubicación y hora de la solicitud">
  <figcaption>A la izquierda, lo que se le pedía autorizar. A la derecha, lo que hacía falta para poder decidir.</figcaption>
</figure>

Un atacante solo necesita una excusa creíble para que alguien teclee cuatro caracteres:
soporte técnico, una «verificación de cuenta», un sorteo, un compañero de trabajo. El
repertorio de siempre.

## Parte 3: el código canjeado devuelve una credencial permanente

Antes de que la víctima confirme, intenté canjear el código. Fallo: `"user not valid"`.
Ese intento fallido es importante y luego explico por qué.

Después de que la víctima confirme, repetí **exactamente la misma petición**:

```http
POST /v2/devices/pin/accesstoken HTTP/2
Host: api.ejemplo.tld
x-app-key: <clave pública>

{"pin":"7MTU"}
```

Y el servidor entregó una credencial completa de dispositivo —un token y su secreto— **sin
cabecera de autenticación, sin cookie y sin firma de ningún tipo**.

El servidor no comprueba quién recoge el premio. Comprueba que alguien ha
dicho «sí» a ese código, y entonces se lo da **a quien lo pida**. Es un cheque al portador:
no lleva nombre, lo cobra quien lo tenga en la mano.

Y esa credencial es **permanente**: identifica a «un dispositivo de esta cuenta» y sigue
valiendo indefinidamente.

## Parte 4: de credencial de dispositivo a contraseña

Con esa credencial, firmé una lectura del perfil de la cuenta:

```http
GET /cg/users/me HTTP/2
Host: api.ejemplo.tld
Authorization: <firma con el token y el secreto del dispositivo>
```

Y en la respuesta, además del correo de la víctima, había un campo que no debería haber
estado ahí: **el token de recuperación de contraseña**.

El token de recuperación es ese código que te llega por correo cuando
pulsas «he olvidado mi contraseña». Es, a todos los efectos, **equivalente a la
contraseña**: quien lo tiene, puede cambiarla.

Y aquí se podía **leer** desde una credencial de dispositivo. Un aparato vinculado no
debería poder leer el mecanismo que sirve para recuperar la cuenta. Son dos niveles de
confianza completamente distintos.

Lo verifiqué con el control que le da sentido: **antes** de pedir una recuperación, ese
campo venía vacío. Después de pedirla desde el formulario público —con solo una dirección
de correo, sin credenciales— la misma lectura devolvía el token real.

A partir de ahí la cadena se cierra sola:

```http
POST /api/recover/puk          ← canjear el token leído
→ set-cookie: sesión completa, válida un año
```

Y al seguir esa sesión hasta la pantalla de cambio de contraseña, el formulario traía el
campo oculto de «contraseña actual» **ya relleno** con el mismo token.

El último obstáculo para cambiar una contraseña suele ser *«escribe la
actual»*. Aquí la página lo rellenaba sola, porque considera que quien llega con el token
de recuperación ya ha demostrado quién es. **Nunca hace falta conocer la contraseña
original.**

## La cadena completa

```
Sin cuenta de ningún tipo
 → pedir un código con la clave pública del cliente        ← nadie es su dueño
 → la víctima teclea 4 caracteres                          ← única acción suya
 → canjear el código: credencial de dispositivo permanente ← sin autenticación
 → leer el perfil firmando con esa credencial              ← correo + token de recuperación
 → canjear el token: sesión completa de un año
 → cambiar la contraseña sin conocer la anterior
```

**Seis peticiones HTTP y cuatro caracteres tecleados por la víctima.**

<figure>
  <img src="{{ '/assets/img/writeups/ato-codigo-emparejamiento/01-cadena.svg' | relative_url }}"
       alt="Diagrama de los seis pasos de la cadena, desde pedir un código sin cuenta hasta cambiar la contraseña sin conocer la anterior">
  <figcaption>Cada paso es razonable por separado. Puestos en fila, entregan la cuenta.</figcaption>
</figure>

## El detalle que lo hace peor: cambiar la contraseña no sirve

Esta es la parte que más me interesó al redactar el impacto.

Cuando alguien sospecha que le han entrado en la cuenta, hace lo que todo el mundo
recomienda: **cambiar la contraseña**. Aquí eso **no echa al atacante**, porque lo que él
tiene no es la contraseña: es la credencial de dispositivo del paso 3. Y esa credencial
**sobrevive al cambio de contraseña**.

La víctima hace todo lo que le dirían en cualquier guía de seguridad,
cree que ha cerrado el incidente, y el atacante sigue dentro. Peor aún: con esa credencial
puede repetir la cadena entera y volver a cambiar la contraseña cuando quiera.

La única limpieza real es **borrar el dispositivo concreto** de la lista de dispositivos
vinculados — algo que a nadie se le ocurre, porque nadie relaciona «me han entrado en la
cuenta» con «tengo un televisor de más en la lista».

## Impacto

<div class="impact" markdown="1">
**Impacto.** Toma de control total de la cuenta por un atacante que **nunca tuvo cuenta en
el servicio**, con una sola acción de la víctima: teclear cuatro caracteres en una pantalla
que no le dice qué está autorizando. El atacante obtiene el correo, una credencial
permanente de dispositivo y la capacidad de cambiar la contraseña. El propietario legítimo
queda fuera de una cuenta cuya contraseña él nunca cambió, y el consejo habitual —cambiarla
de nuevo— no expulsa al atacante.
</div>
