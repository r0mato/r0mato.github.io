---
title:       "Condición de carrera en un límite de pago: 10 dispositivos activados donde solo cabía 1"
summary:     "El contador que hace cumplir el cupo de dispositivos de cada plan se leía antes de subirlo. Una detrás de otra, la segunda activación recibe un 403. Soltadas en el mismo instante, pasan las diez: diez dispositivos reales, con su credencial válida, en una cuenta que permite uno. Reproducible nueve veces de nueve."
date:        2026-11-05 10:33:00 +0100
lang:        es
ref:         race-cupo-dispositivos
image:       /assets/img/og/race-cupo-dispositivos-es.png

severity:    medium
cvss:        "4.3"
cvss_vector: "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:L/A:N"
cwe:         "CWE-362"
vuln_class:  "Lógica de negocio"
target_type: "API de un servicio por suscripción"
platform:    "YesWeHack"
status:      "Informativo"
tags:        [race-condition, toctou, logica-de-negocio, concurrencia, api, cupo]

takeaways:
  - "Una comprobación correcta y una escritura correcta, separadas por un microsegundo, son un fallo."
  - "«A la vez» no es «muy rápido»: la latencia se paga antes de la carrera soltando solo el último byte."
  - "El contador después de la carrera es la prueba, no el número de 200 que hayas recibido."
  - "Un fallo de cupo no expone datos de nadie, pero rompe justo lo que el producto vende. El impacto es de ingresos, y se cuantifica igual."
---

Hay servicios por suscripción cuyo precio **es** un número de dispositivos. El plan se
llama, literalmente, «7 dispositivos». Cuando instalas la aplicación en un aparato nuevo,
llama al endpoint de alta:

```http
POST /oauth/access_token
Content-Type: application/json

{"x_auth_machineid":"portatil-salon","x_auth_machinename":"portatil-salon",
 "x_auth_mode":"client_auth","x_auth_username":"<correo>","x_auth_password":"<contraseña>","reset":0}
```

Si queda hueco, `200` con un token. Si no, `403`.

<figure>
  <img src="{{ '/assets/img/writeups/race-cupo-dispositivos/01-control-403.png' | relative_url }}"
       alt="Burp Repeater: un alta de dispositivo enviada con la cuenta llena recibe HTTP/2 403 Forbidden. Las cabeceras y el cuerpo del mensaje van tapados con bandas etiquetadas">
  <figcaption>Con la cuenta llena, el alta recibe <code>403</code>. El cuerpo lleva un mensaje de límite alcanzado; va tapado porque su redacción exacta identifica al producto.</figcaption>
</figure>

Esa comprobación existe, funciona y está bien escrita. No tiene ningún fallo. La pregunta
no es cómo saltársela, es otra: **cuánto tiempo pasa entre que el servidor mira el contador
y lo sube.**

```python
usados = db.query("SELECT activateddevices FROM users WHERE id = ?", uid)
limite = db.query("SELECT max_devices FROM plans WHERE id = ?", plan)

if usados >= limite:                 # ── comprobar ──
    return error(403, "límite de dispositivos del plan alcanzado")

token = crear_token_de_dispositivo(uid)              # ── actuar ──
db.execute("UPDATE users SET activateddevices = activateddevices + 1 WHERE id = ?", uid)
return token
```

Con dos peticiones a la vez: la primera lee `0`, la segunda también, porque la primera no
ha llegado al `UPDATE`. Las dos pasan el `if`. Eso es TOCTOU, el hueco entre comprobar y
usar.

<figure>
  <img src="{{ '/assets/img/writeups/race-cupo-dispositivos/01-ventana-carrera.svg' | relative_url }}"
       alt="Dos paneles comparan las mismas dos peticiones: enviadas una detrás de otra, la segunda lee el contador ya actualizado y recibe 403; enviadas a la vez, ambas leen cero dentro de la misma ventana y ambas escriben">
  <figcaption>Misma petición, mismo servidor, mismo límite. Lo único que cambia es el instante en que llegan.</figcaption>
</figure>

## «A la vez» no es «muy rápido»

Aquí fracasa la mayoría de los intentos. Un bucle con diez peticiones seguidas no las manda
a la vez: cada una sale cuando la anterior ha terminado de escribirse en el socket, y entre
la primera y la última hay milisegundos. Para el servidor eso es una eternidad. Obtienes un
`200` y nueve `403`, y concluyes mal.

Lo que hace falta es la sincronización por último byte:

1. Se abren diez conexiones TLS.
2. Se envía cada petición entera **menos su último byte**. El servidor no puede empezar a
   procesar: le falta el final.
3. Se espera a que las diez estén así — ahí se paga toda la latencia.
4. Se sueltan los diez bytes finales juntos.

<figure>
  <img src="{{ '/assets/img/writeups/race-cupo-dispositivos/02-ultimo-byte.svg' | relative_url }}"
       alt="Arriba, tres conexiones enviadas una tras otra llegan separadas en el tiempo; abajo, tres conexiones envían la petición completa menos su último byte y después sueltan los tres bytes finales a la vez, llegando dentro de la misma ventana">
  <figcaption>La latencia se paga <strong>antes</strong> de que empiece la carrera, no durante.</figcaption>
</figure>

```python
import threading

def carrera(peticiones):
    """Suelta el último byte de todas las peticiones en el mismo instante."""
    conexiones = [abrir_tls() for _ in peticiones]

    for conexion, datos in zip(conexiones, peticiones):
        conexion.sendall(datos[:-1])        # todo menos el final

    puerta = threading.Barrier(len(peticiones))
    respuestas = [None] * len(peticiones)

    def soltar(i):
        puerta.wait()                       # nadie pasa hasta que están todos
        conexiones[i].sendall(peticiones[i][-1:])
        respuestas[i] = leer(conexiones[i])

    hilos = [threading.Thread(target=soltar, args=(i,)) for i in range(len(peticiones))]
    for h in hilos: h.start()
    for h in hilos: h.join()
    return respuestas
```

La pieza clave es `threading.Barrier`: ningún hilo pasa de `puerta.wait()` hasta que han
llegado todos.

## Lo que devolvió el servidor

<figure>
  <img src="{{ '/assets/img/writeups/race-cupo-dispositivos/02-seis-en-paralelo.png' | relative_url }}"
       alt="Historial de Burp con seis peticiones POST al mismo endpoint, todas con la marca de tiempo 12:29:04: dos responden 200 y cuatro responden 403">
  <figcaption>Seis altas soltadas en el mismo instante: las seis marcan <code>12:29:04</code> y dos salen con <code>200</code>, en una cuenta de un dispositivo. Se han recortado las columnas intermedias y tapado el host.</figcaption>
</figure>

Nueve tandas, dos hosts de la API y dos planes. Las dos más claras:

| Plan | Ya en uso | En paralelo | Aceptadas | El servidor informa |
|---|---|---|---|---|
| 7 dispositivos | 3 | 10 | **10** | `activateddevices=13`, `max_devices=7` |
| 1 dispositivo | 0 | 10 | **10** | `activateddevices=10`, `max_devices=1` |

La última columna no es una deducción mía: es el propio servidor, en `GET /users/me`,
diciendo que tiene diez dispositivos activos en un plan que permite uno.

Y no son sesiones simultáneas. Cada una de las diez cuenta en `activateddevices`, tiene su
propio token de larga duración con identificador distinto, y pidiendo `GET /certificate`
devuelve `200` con su credencial de cliente.

<figure>
  <img src="{{ '/assets/img/writeups/race-cupo-dispositivos/03-contador-2-de-1.png' | relative_url }}"
       alt="Respuesta del servidor con dos campos recuadrados en rojo: activateddevices con valor 2 y max_devices con valor 1">
  <figcaption>No es una deducción mía: lo dice el servidor. <code>activateddevices: 2</code> sobre <code>max_devices: 1</code>.</figcaption>
</figure>

## Dónde paré

Diez peticiones en paralelo, no más. Revoqué cada dispositivo creado, también cuando el
script se interrumpía, y cada cuenta terminó con los mismos dispositivos que tenía al
empezar. Solo cuentas de prueba mías. No conecté ninguno al servicio: con que el servidor
entregue la credencial ya está demostrado que el alta es real.

## Impacto

<div class="impact" markdown="1">
El número de dispositivos **es** lo que vende la empresa. Cualquier suscriptor puede
activar más de los que ha pagado: 13 en un plan de 7, con una ráfaga de diez peticiones y
menos de un minuto. El límite de un dispositivo de los planes gratuitos y de prueba cae
igual de fácil.

No hay impacto en confidencialidad ni en disponibilidad, y ninguna otra cuenta se ve
afectada. Es un fallo de **ingresos**: elimina la razón para comprar el plan siguiente, y
permite compartir o revender una suscripción entre muchos aparatos.
</div>
