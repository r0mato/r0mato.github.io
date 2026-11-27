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

Reproducible nueve veces de nueve, y con el servidor admitiendo por escrito que está por
encima de su propio límite: diez dispositivos activos en una cuenta que permite uno. Todo
lo que hace falta es enviar las peticiones **en el mismo instante** en vez de una detrás
de otra.

<div class="warn" markdown="1">
**Todo está anonimizado.** Publicado con el consentimiento del programa y sin identificar
al producto: fabricante, dominios, rutas, nombres de campo y mensajes de error están
cambiados. El mecanismo, la secuencia y las cifras son exactos.
</div>

## El cupo de dispositivos, que es literalmente el producto

Hay un montón de servicios por suscripción cuyo precio **es** un número de dispositivos.
No pagas por más funciones ni por más velocidad: pagas por poder usarlo en tres aparatos
en vez de en uno. El plan se llama, literalmente, «7 dispositivos».

Cuando instalas la aplicación en un aparato nuevo, esta llama a un endpoint de alta:

```http
POST /oauth/access_token
Content-Type: application/json

{"x_auth_machineid":"portatil-salon","x_auth_machinename":"portatil-salon",
 "x_auth_mode":"client_auth","x_auth_username":"<correo>","x_auth_password":"<contraseña>","reset":0}
```

Si queda hueco, responde `200` con un token de dispositivo. Si no:

```
403 Forbidden
```

Ese `403` es el producto haciendo su trabajo. La comprobación **existe, funciona y está
bien escrita**. No voy a encontrar ningún fallo en ella, porque no lo tiene.

<figure>
  <img src="{{ '/assets/img/writeups/race-cupo-dispositivos/01-control-403.png' | relative_url }}"
       alt="Burp Repeater: un alta de dispositivo enviada con la cuenta llena recibe HTTP/2 403 Forbidden. Las cabeceras y el cuerpo del mensaje van tapados con bandas etiquetadas">
  <figcaption>Con la cuenta llena, el alta recibe <code>403</code>. El cuerpo lleva un mensaje de límite alcanzado; va tapado porque su redacción exacta identifica al producto.</figcaption>
</figure>

## La pregunta que abre el caso

No es «¿puedo saltarme la comprobación?». Es otra, bastante más barata:

> **¿Cuánto tiempo pasa entre que el servidor mira el contador y lo sube?**

Porque el código, en el 99 % de los sitios donde he visto esto, tiene esta forma:

```python
usados = db.query("SELECT activateddevices FROM users WHERE id = ?", uid)
limite = db.query("SELECT max_devices FROM plans WHERE id = ?", plan)

if usados >= limite:                 # ── comprobar ──
    return error(403, "límite de dispositivos del plan alcanzado")

token = crear_token_de_dispositivo(uid)              # ── actuar ──
db.execute("UPDATE users SET activateddevices = activateddevices + 1 WHERE id = ?", uid)
return token
```

Léelo otra vez pensando en **dos peticiones a la vez**. La primera lee `0`. La segunda
lee… también `0`, porque la primera todavía no ha llegado al `UPDATE`. Las dos pasan el
`if`. Las dos crean un token. Las dos suman uno.

Eso tiene nombre desde hace décadas: **TOCTOU**, *time of check to time of use*. El
hueco entre comprobar y usar.

<figure>
  <img src="{{ '/assets/img/writeups/race-cupo-dispositivos/01-ventana-carrera.svg' | relative_url }}"
       alt="Dos paneles comparan las mismas dos peticiones: enviadas una detrás de otra, la segunda lee el contador ya actualizado y recibe 403; enviadas a la vez, ambas leen cero dentro de la misma ventana y ambas escriben">
  <figcaption>Misma petición, mismo servidor, mismo límite. Lo único que cambia es el instante en que llegan.</figcaption>
</figure>

## «A la vez» no es «muy rápido»

Aquí es donde la mayoría de los intentos de explotar una carrera fracasan, y donde está
la técnica que de verdad merece la pena aprender.

Si abres un bucle y mandas diez peticiones seguidas, **no van a la vez**. Cada una sale
cuando la anterior ha terminado de escribirse en el socket, y entre la primera y la última
hay milisegundos de red. Para un servidor, milisegundos son una eternidad: el `UPDATE` de
la primera ya está hecho cuando llega la segunda. Obtienes un `200` y nueve `403`, y
concluyes que no hay fallo. Conclusión equivocada.

Lo que hace falta es que las diez lleguen dentro de la **misma ventana**, y para eso se
usa la sincronización por último byte:

1. Se abren diez conexiones TLS, una por petición.
2. Por cada una se envía la petición entera **menos su último byte**. El servidor recibe
   casi todo, pero no puede empezar a procesar nada: le falta el final.
3. Se espera a que las diez estén en ese estado — ahí es donde se paga toda la latencia.
4. Se sueltan los diez bytes finales juntos.

Los diez servidores… perdón, los diez hilos del mismo servidor arrancan a la vez.

<figure>
  <img src="{{ '/assets/img/writeups/race-cupo-dispositivos/02-ultimo-byte.svg' | relative_url }}"
       alt="Arriba, tres conexiones enviadas una tras otra llegan separadas en el tiempo; abajo, tres conexiones envían la petición completa menos su último byte y después sueltan los tres bytes finales a la vez, llegando dentro de la misma ventana">
  <figcaption>La latencia se paga <strong>antes</strong> de que empiece la carrera, no durante.</figcaption>
</figure>

En Python eso es más corto de lo que parece. Lo esencial cabe en una función:

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
llegado todos. Cuando se abre, los diez `sendall` del byte final salen prácticamente
pegados.

<div class="note" markdown="1">
**Por qué no publico el script completo.** El que mandé al programa tiene unas 250 líneas
porque hace el alta en serie, la carrera, la verificación y la limpieza de todo lo que
crea. Lo que vale la pena aprender es la función de
arriba; el resto es fontanería atada a un producto concreto.
</div>

## Lo que devolvió el servidor

<figure>
  <img src="{{ '/assets/img/writeups/race-cupo-dispositivos/02-seis-en-paralelo.png' | relative_url }}"
       alt="Historial de Burp con seis peticiones POST al mismo endpoint, todas con la marca de tiempo 12:29:04: dos responden 200 y cuatro responden 403">
  <figcaption>Seis altas soltadas en el mismo instante: las seis marcan <code>12:29:04</code> y dos salen con <code>200</code>, en una cuenta de un dispositivo. Se han recortado las columnas intermedias y tapado el host.</figcaption>
</figure>

Nueve tandas, dos hosts de la API y dos planes distintos. Las dos más claras:

| Plan | Ya en uso | En paralelo | Aceptadas | El servidor informa |
|---|---|---|---|---|
| 7 dispositivos | 3 | 10 | **10** | `activateddevices=13`, `max_devices=7` |
| 1 dispositivo | 0 | 10 | **10** | `activateddevices=10`, `max_devices=1` |

Me interesa subrayar la última columna, porque no es una deducción mía: es el propio
servidor, en su respuesta a `GET /users/me`, diciendo que tiene **diez dispositivos
activos en un plan que permite uno**. No hace falta interpretar nada.

Y no son sesiones ni conexiones simultáneas. Cada una de las diez es un alta persistente:

- cuenta en `activateddevices`,
- tiene su propio token de larga duración, con un identificador distinto,
- y pidiendo `GET /certificate` devuelve `200` con su propia credencial de cliente.

Es decir: exactamente lo que `max_devices` existe para limitar.

<figure>
  <img src="{{ '/assets/img/writeups/race-cupo-dispositivos/03-contador-2-de-1.png' | relative_url }}"
       alt="Respuesta del servidor con dos campos recuadrados en rojo: activateddevices con valor 2 y max_devices con valor 1">
  <figcaption>No es una deducción mía: lo dice el servidor. <code>activateddevices: 2</code> sobre <code>max_devices: 1</code>.</figcaption>
</figure>

## Hasta dónde llegué, y dónde paré

Diez peticiones en paralelo, no más. Cada dispositivo creado lo revoqué, también cuando el
script se interrumpía, y cada cuenta terminó con el mismo número de dispositivos que tenía
al empezar. Solo usé cuentas de prueba mías. No llegué a conectar ninguno de los
dispositivos extra al servicio: con que el servidor me entregue la credencial ya está
demostrado que el alta es real, y conectarse no añade nada al reporte.

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
