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

Este es el hallazgo del que más orgulloso estoy, y paradójicamente el más fácil de
encontrar: estaba a la vista, en un fichero que el propio servidor le entrega a cualquiera
que abra la página. Es un recordatorio brutal de que **lo que llega al navegador es
público**, aunque esté minificado y parezca ilegible.

<div class="warn" markdown="1">
**Todo está anonimizado.** El programa autorizó la publicación con la condición de no
identificar al producto. He cambiado la empresa, los dominios, las rutas, los nombres de
los campos y, por supuesto, **la clave real no aparece**: las que ves aquí son de ejemplo.
El mecanismo es exacto.
</div>

## El objetivo

Un **portal interno de compras** de una multinacional, accesible desde internet. El tipo
de aplicación donde trabajan cientos de empleados: pedidos, proveedores, facturas,
contratos. Entre sus funciones había un asistente conversacional interno, y ahí es donde
me metí.

## Paso 1: leer el JavaScript, que es gratis

Cuando abres una web, tu navegador se descarga ficheros `.js` con toda la lógica del lado
cliente. Están minificados —comprimidos, sin espacios ni nombres legibles— pero **no
cifrados**. Minificar no es proteger: es ahorrar bytes.

Lo primero que hago en cualquier objetivo es bajarme todos los bundles y buscar palabras
que delaten secretos:

```bash
# descargar los .js que carga la página
grep -oE 'src="[^"]+\.js"' pagina.html | cut -d'"' -f2 | while read u; do
    curl -s "https://portal.ejemplo.tld$u" -o "bundles/$(basename $u)"
done

# y buscar lo que suele estar donde no debe
grep -rniE 'secret|api[_-]?key|password|token|private[_-]?key|encrypt|sign' bundles/
```

En uno de los ficheros apareció esto:

```javascript
// bundle minificado, reformateado para que se lea
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

Una clave AES-256. En un fichero público. Servida a cualquiera que entre en la web.

## Paso 2: la pregunta correcta no es «¿hay una clave?» sino «¿para qué sirve?»

Aquí es donde mucha gente se precipita. Encontrar una cadena que parece una clave **no es
un hallazgo**. Hay claves públicas por diseño: identificadores de Firebase, claves
publicables de pasarelas de pago, tokens de mapas. Reportar una de esas te gana un
«informativo» y algo de vergüenza.

<div class="note" markdown="1">
**La regla que uso:** una clave filtrada no vale nada por sí misma. **Lo que vale es lo que
esa clave abre.** No reportes el secreto: reporta la puerta.
</div>

Así que seguí la función. ¿Quién llama a `encryptUserTime` y qué hace con el resultado?

```javascript
// más abajo, en el mismo bundle
const firma = encryptUserTime({
    username:  "SRM",
    timestamp: Date.now(),
    nonce:     "aleatorio123"
});

fetch("/asistente/auth/v1/app-source/token", {
    method:  "POST",
    headers: { "X-System-Code": "SRM" },
    body:    JSON.stringify({ signature: firma })
});
```

La aplicación cifra un texto con esa clave y se lo manda al servidor. El
servidor lo descifra, ve que el resultado tiene sentido y concluye: *«si has sabido cifrar
esto, eres mi aplicación legítima»*. Y te da un pase de entrada.

El problema es evidente en cuanto lo dices en voz alta: **si la clave está en el fichero
que yo me he descargado, yo también sé cifrarlo.** El servidor no está comprobando quién
eres. Está comprobando que tienes un secreto que le ha dado a todo el mundo.

<figure>
  <img src="{{ '/assets/img/writeups/clave-aes-bundle-js/02-clave-en-el-navegador.svg' | relative_url }}"
       alt="Diagrama: el servidor envía el fichero JavaScript con la clave dentro tanto al navegador legítimo como al atacante, y los dos pueden firmar peticiones válidas">
  <figcaption>El mismo fichero llega a los dos. Y con él, la misma clave.</figcaption>
</figure>

## Paso 3: fabricar un pase, sin tener cuenta

Reproduje la firma fuera del navegador. Sin usuario, sin contraseña, sin cookie:

```python
import json, time, base64, os
from Crypto.Cipher import AES          # la clave sale del bundle público

CLAVE = bytes.fromhex("a1b2c3d4e5f60718293a4b5c6d7e8f90")   # ejemplo
iv    = os.urandom(16)

texto = json.dumps({
    "username":  "SRM",
    "timestamp": int(time.time() * 1000),
    "nonce":     "bbtest1234567",
}).encode()

relleno = 16 - len(texto) % 16
cifrado = AES.new(CLAVE, AES.MODE_CBC, iv).encrypt(texto + bytes([relleno]) * relleno)

firma = base64.b64encode(iv + cifrado).decode()
```

Y con eso, al endpoint:

```http
POST /asistente/auth/v1/app-source/token HTTP/2
Host: portal.ejemplo.tld
Content-Type: application/json
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

Un token válido. Con permisos de **lectura y escritura**.

## Paso 4: el segundo fallo, que es el que de verdad duele

Tener un token no es tener los datos de alguien. Lo normal sería que ese pase sirviera solo
para lo tuyo. Así que probé a pedir datos de **otra persona**:

```http
POST /asistente/chat/v1/get_conversation HTTP/2
Host: portal.ejemplo.tld
X-Authorization: <mi token fabricado>

{"user":"empleado.objetivo"}
```

Y llegaron. Las conversaciones de ese empleado, por cientos.

El token que fabriqué no dice **quién soy**. Y la API, en vez de
deducirlo del token, me deja escribirlo yo en el cuerpo de la petición. Es como un billete
de tren sin nombre donde el revisor te pregunta «¿y tú cómo te llamas?» y se fía de la
respuesta.

A esto se le llama **BOLA** (*Broken Object Level Authorization*) o IDOR, y es el fallo
número uno de las APIs modernas. La aplicación comprueba que has entrado, pero no comprueba
que lo que pides sea tuyo.

Esta es la parte importante para quien está aprendiendo: **el hallazgo no es la clave**.
La clave es la puerta. Lo que hace que esto sea crítico es la combinación:

| Pieza | Por sí sola | Combinada |
|---|---|---|
| Clave en el bundle | Preocupante, pero quizá solo firma peticiones anónimas | Permite fabricar pases |
| El token no va atado a un usuario | Malo, pero necesitas un token | Con el pase fabricado, entras como quien quieras |
| La API acepta el usuario en el cuerpo | Mal diseño | **Lees los datos de cualquier empleado** |

Tres decisiones que, por separado, alguien podría defender. Juntas, un crítico.

## Paso 5: hasta dónde llegar — y dónde parar

Aquí hay una decisión ética que no es opcional.

**Podía** haber descargado las conversaciones de cientos de empleados para engordar el
reporte. **No lo hice**, y no deberías hacerlo tú:

- Para demostrar el fallo basta con **enseñar que la puerta se abre**, no con vaciar la
  casa. Un listado que prueba el acceso es suficiente.
- Las operaciones de escritura las probé contra **una conversación mía**, creada por mí,
  con un identificador aleatorio. Nunca contra nada de una persona real.
- Los datos personales que aparecieron en pantalla no se guardaron, no se copiaron y en el
  reporte van tachados.

<div class="note" markdown="1">
**Por qué esto importa más que el bug.** El alcance de casi todos los programas prohíbe
explícitamente acceder a datos de usuarios reales más allá de lo imprescindible. Pasarte de
ahí convierte tu reporte en un incidente, y a ti en el incidente. La diferencia entre un
investigador y un problema es exactamente esta línea.
</div>

También encontré, por el mismo camino, un endpoint que devolvía **sin ninguna
autenticación** la clave de un servicio externo de pago. Esa la reporté tachada, sin usarla
ni una vez: tener la llave no te da derecho a abrir la puerta.
