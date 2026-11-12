---
title:       "Cuatro caracteres: cómo un código para emparejar la tele entrega la cuenta entera"
summary:     "El código que escribes para vincular la aplicación con tu televisor no estaba atado a nadie. Cualquiera podía pedir uno, convencerte de que lo teclearas y salir de ahí con una credencial permanente, tu correo y el token de recuperación de contraseña."
date:        2026-11-11 20:20:00 +0100
lang:        es
ref:         ato-codigo-emparejamiento

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

<div class="plain" markdown="1">
**En cristiano:** es el mismo patrón que usan las aplicaciones de las *smart TV* de medio
mundo. Lo has hecho veinte veces. Y funciona porque se asume que **quien escribe el código
está mirando la pantalla donde aparece** — es decir, que los dos aparatos están en la misma
habitación.

Ese supuesto es el que se rompe aquí.
</div>

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

Fíjate en el detalle que lo decide todo: **`users_id: null`**.

<div class="plain" markdown="1">
**En cristiano:** el servidor me acaba de dar un código **que no pertenece a nadie**. Es un
hueco vacío esperando a que alguien lo rellene. Y lo rellena quien lo teclee.

Un código así no debería existir sin estar atado desde el primer segundo a la sesión del
aparato que lo pidió.
</div>

## Parte 2: la pantalla que no dice qué estás autorizando

Aquí viene la parte que el reporte explica con más cuidado, porque es la que decide si esto
es explotable en el mundo real o solo en un laboratorio.

Cuando la víctima teclea el código en su aplicación, aparece una confirmación. Y esa
confirmación **no decía nada del aparato que lo había pedido**: ni nombre, ni tipo, ni
dirección IP, ni ubicación aproximada.

<div class="plain" markdown="1">
**En cristiano:** la víctima ve algo parecido a *«¿Autorizar este dispositivo?»* y un botón.
No hay forma humana de distinguir su propio televisor del portátil de un desconocido al
otro lado del país. No es que la víctima sea descuidada: **es que no le están dando la
información para decidir**.

Por eso una pantalla de consentimiento que no describe lo que estás autorizando no es una
protección. Es un trámite.
</div>

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

<div class="plain" markdown="1">
**En cristiano:** el servidor no comprueba quién recoge el premio. Comprueba que alguien ha
dicho «sí» a ese código, y entonces se lo da **a quien lo pida**. Es un cheque al portador:
no lleva nombre, lo cobra quien lo tenga en la mano.
</div>

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

<div class="plain" markdown="1">
**En cristiano:** el token de recuperación es ese código que te llega por correo cuando
pulsas «he olvidado mi contraseña». Es, a todos los efectos, **equivalente a la
contraseña**: quien lo tiene, puede cambiarla.

Y aquí se podía **leer** desde una credencial de dispositivo. Un aparato vinculado no
debería poder leer el mecanismo que sirve para recuperar la cuenta. Son dos niveles de
confianza completamente distintos.
</div>

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

<div class="plain" markdown="1">
**En cristiano:** el último obstáculo para cambiar una contraseña suele ser *«escribe la
actual»*. Aquí la página lo rellenaba sola, porque considera que quien llega con el token
de recuperación ya ha demostrado quién es. **Nunca hace falta conocer la contraseña
original.**
</div>

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

## El detalle que lo hace peor: cambiar la contraseña no sirve

Esta es la parte que más me interesó al redactar el impacto.

Cuando alguien sospecha que le han entrado en la cuenta, hace lo que todo el mundo
recomienda: **cambiar la contraseña**. Aquí eso **no echa al atacante**, porque lo que él
tiene no es la contraseña: es la credencial de dispositivo del paso 3. Y esa credencial
**sobrevive al cambio de contraseña**.

<div class="plain" markdown="1">
**En cristiano:** la víctima hace todo lo que le dirían en cualquier guía de seguridad,
cree que ha cerrado el incidente, y el atacante sigue dentro. Peor aún: con esa credencial
puede repetir la cadena entera y volver a cambiar la contraseña cuando quiera.

La única limpieza real es **borrar el dispositivo concreto** de la lista de dispositivos
vinculados — algo que a nadie se le ocurre, porque nadie relaciona «me han entrado en la
cuenta» con «tengo un televisor de más en la lista».
</div>

## El control negativo

| Qué probé | Qué pasó | Qué descarta |
|---|---|---|
| Canjear el código **antes** de que la víctima confirme | Rechazado: *user not valid* | Que el endpoint diera credenciales a cualquiera: lo único que cambia el resultado es la confirmación |
| Pedir el código **sin** la clave pública de la aplicación | `401` | Que el endpoint estuviera completamente abierto |
| Leer el perfil **antes** de solicitar recuperación | El campo del token viene **vacío** | Que ese campo llevara siempre un valor: aparece justo cuando se dispara el flujo |

<div class="plain" markdown="1">
**En cristiano:** la primera prueba es la que demuestra que no estoy explotando un fallo
del servidor, sino **el diseño del flujo**. Todo funciona como está programado. El problema
es que lo que está programado entrega la cuenta.
</div>

## Impacto

<div class="impact" markdown="1">
**Impacto.** Toma de control total de la cuenta por un atacante que **nunca tuvo cuenta en
el servicio**, con una sola acción de la víctima: teclear cuatro caracteres en una pantalla
que no le dice qué está autorizando. El atacante obtiene el correo, una credencial
permanente de dispositivo y la capacidad de cambiar la contraseña. El propietario legítimo
queda fuera de una cuenta cuya contraseña él nunca cambió, y el consejo habitual —cambiarla
de nuevo— no expulsa al atacante.
</div>

## El arreglo

1. **Atar el código a quien lo pide.** El canje debe exigir la misma sesión de cliente, o
   un secreto que solo tenga el aparato que originó el código. El código por sí solo no
   puede bastar.
2. **Un solo uso y vida corta**, e invalidarlo en cuanto se borra el dispositivo resultante.
3. **Decirle a la víctima qué está autorizando**: nombre del cliente, tipo de aparato,
   ubicación aproximada y hora. Sin eso, la confirmación no es consentimiento.
4. **Dejar de devolver el token de recuperación** desde cualquier endpoint autenticado solo
   con una credencial de dispositivo. Hacerlo de un solo uso y con caducidad corta.
5. **Revocar las credenciales de dispositivo cuando cambia la contraseña.** Si no, el
   cambio de contraseña es teatro.

## Cómo buscar esto tú mismo

Cualquier producto que se empareje con una tele, una consola, un reloj o un aparato sin
teclado usa este patrón. Las preguntas son siempre las mismas:

1. **¿Puedo pedir un código sin tener cuenta?** Si la respuesta trae un campo de usuario
   vacío o nulo, sigue mirando.
2. **¿Qué hace falta para canjearlo?** Si basta el código, es un cheque al portador.
3. **¿Qué ve la víctima al confirmar?** Si no ve el nombre del aparato, la IP o la
   ubicación, no puede distinguirte de su propio televisor.
4. **¿Qué devuelve la credencial resultante?** Pide el perfil y lee **todos** los campos,
   uno por uno. Los tokens de recuperación aparecen en sitios sorprendentes.
5. **¿Sobrevive al cambio de contraseña?** Cámbiala y repite la petición. Si sigue
   funcionando, tienes una pieza más para el reporte.

El paso 4 es donde suele estar el premio y el que casi nadie hace: la gente mira que la
respuesta sea un `200` y pasa a otra cosa. **Léela entera.**
