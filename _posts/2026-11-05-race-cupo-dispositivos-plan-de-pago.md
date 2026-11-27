---
title:       "Condición de carrera en un límite de pago: 10 dispositivos activados donde solo cabía 1"
summary:     "El contador que hace cumplir el cupo de dispositivos de cada plan se leía antes de subirlo. Una detrás de otra, la segunda activación recibe un 403. Soltadas en el mismo instante, pasan las diez: diez dispositivos reales, con su credencial válida, en una cuenta que permite uno. El programa lo cerró como informativo, y esa parte también la cuento."
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
  - "El mejor control negativo de una carrera es el mismo ataque contra un endpoint que sí es atómico. Si allí entra uno solo, no era la red."
  - "Un hallazgo técnicamente real puede cerrarse como informativo. Si el impacto es ingresos y no datos, el triador tiene argumentos y conviene saberlo antes de escribir."
---

Este es el writeup de un fallo que **no me pagaron**, y lo publico precisamente por eso.
Es reproducible nueve veces de nueve, el servidor admite por escrito que está por encima
de su propio límite, y aun así el programa lo cerró como informativo. Entender por qué es
tan útil como entender la carrera.

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
POST /api/oauth/access_token
Content-Type: application/json

{"device_id":"portatil-salon","device_name":"portatil-salon",
 "auth_mode":"client_auth","username":"<correo>","password":"<contraseña>","reset":0}
```

Si queda hueco, responde `200` con un token de dispositivo. Si no:

```
403   límite de dispositivos del plan alcanzado
```

Ese `403` es el producto haciendo su trabajo. La comprobación **existe, funciona y está
bien escrita**. No voy a encontrar ningún fallo en ella, porque no lo tiene.

## La pregunta que abre el caso

No es «¿puedo saltarme la comprobación?». Es otra, bastante más barata:

> **¿Cuánto tiempo pasa entre que el servidor mira el contador y lo sube?**

Porque el código, en el 99 % de los sitios donde he visto esto, tiene esta forma:

```python
usados = db.query("SELECT active_devices FROM users WHERE id = ?", uid)
limite = db.query("SELECT max_devices FROM plans WHERE id = ?", plan)

if usados >= limite:                 # ── comprobar ──
    return error(403, "límite de dispositivos del plan alcanzado")

token = crear_token_de_dispositivo(uid)              # ── actuar ──
db.execute("UPDATE users SET active_devices = active_devices + 1 WHERE id = ?", uid)
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
porque hace el alta en serie, el control negativo, la carrera, la verificación, un segundo
control y la limpieza de todo lo que crea. Lo que vale la pena aprender es la función de
arriba; el resto es fontanería atada a un producto concreto.
</div>

## Lo que devolvió el servidor

Nueve tandas, dos hosts de la API y dos planes distintos. Las dos más claras:

| Plan | Ya en uso | En paralelo | Aceptadas | El servidor informa |
|---|---|---|---|---|
| 7 dispositivos | 3 | 10 | **10** | `active_devices=13`, `max_devices=7` |
| 1 dispositivo | 0 | 10 | **10** | `active_devices=10`, `max_devices=1` |

Me interesa subrayar la última columna, porque no es una deducción mía: es el propio
servidor, en su respuesta a `GET /api/users/me`, diciendo que tiene **diez dispositivos
activos en un plan que permite uno**. No hace falta interpretar nada.

Y no son sesiones ni conexiones simultáneas. Cada una de las diez es un alta persistente:

- cuenta en `active_devices`,
- tiene su propio token de larga duración, con un identificador distinto,
- y pidiendo `GET /api/certificate` devuelve `200` con su propia credencial de cliente.

Es decir: exactamente lo que `max_devices` existe para limitar.

## El control negativo, que aquí es el 80 % del trabajo

Una carrera es la clase de fallo donde más fácil es engañarse. Si mandas diez peticiones y
pasan dos, siempre te queda la duda de si el servidor estaba simplemente lento, o si el
cupo no era el que creías. Tres controles:

**Uno — en serie, con la cuenta llena.** Alta normal, de una en una, con `1/1`
dispositivos:

```
403   límite de dispositivos del plan alcanzado
```

El cupo **se respeta**. Lo que falla no es la regla.

**Dos — en serie, ya por encima del límite.** Con la cuenta en `13/7` después de la
carrera, mando una más, normal:

```
403   límite de dispositivos del plan alcanzado
```

Precioso, porque demuestra que la comprobación sigue viva y sigue leyendo bien el
contador. Solo es ciega durante la ventana.

**Tres — el mismo ataque, contra otro endpoint.** Esto es lo que convierte la sospecha en
certeza. El panel web tiene su propia ruta para dar de alta un dispositivo. Le lancé la
misma carrera, desde la misma máquina, con la misma red y el mismo número de peticiones:

```
5 en paralelo  →  1 aceptada, 4 rechazadas
```

**Exactamente una.** Ese camino sí es atómico. Mismo atacante, misma latencia, mismo
instante: resultado correcto. No era la red ni mi script — era ese endpoint concreto.

<div class="note" markdown="1">
Ese tercer control es el que yo buscaría siempre en una carrera: **un sitio donde el mismo
ataque debería fallar y falla**. Sin él, cualquier triador puede decirte «tu medición no
vale» y tendrá razón.
</div>

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

## Por qué lo cerraron como informativo

El programa lo cerró como **informativo, sin recompensa**, con un razonamiento que
entiendo: para ese triador, el abuso del cupo de dispositivos no es un problema de
seguridad. No se expone ningún dato, no se toca ninguna cuenta ajena, y el perjudicado es
el modelo de negocio, no un usuario.

No estoy de acuerdo en la clasificación, pero sí reconozco que el argumento es coherente.
Y hay una lección ahí que vale más que el dinero del reporte:

<div class="note" markdown="1">
**Un hallazgo puede ser técnicamente impecable y aun así no pagarse.** Nueve de nueve
reproducciones, tres controles negativos y el propio servidor confesando el estado
inconsistente no cambian que el impacto es económico. Si vas a invertir una tarde en una
carrera contra un límite de plan, mira antes la política del programa: muchas excluyen
explícitamente el abuso de cuotas y de funciones de pago.
</div>

Lo que sí es innegociable es el lado del ingeniero: una cuenta en un estado que su propio
esquema de datos considera imposible (`active_devices > max_devices`) es un bug, y de los
que se arrastran. Cada contador que puede desincronizarse así termina apareciendo en
sitios peores — en el de créditos, en el de invitaciones, en el de intentos de un código
de un solo uso.

## El arreglo

Que comprobar y sumar sean **una sola operación**. No hace falta nada exótico: lo hace la
propia base de datos.

```sql
UPDATE users
   SET active_devices = active_devices + 1
 WHERE id = :uid
   AND active_devices < :max_devices;
-- si affected_rows == 0  ->  403 y NO se crea el token
```

La condición viaja dentro del `UPDATE`, así que la fila se bloquea una sola vez y no queda
hueco entre leer y escribir. La alternativa es tomar un cerrojo por usuario
(`SELECT ... FOR UPDATE`) al principio del alta.

Y, porque este fallo deja rastro, conviene además un trabajo periódico que revoque los
tokens más nuevos de cualquier cuenta donde `active_devices > max_devices`: arreglar el
código no arregla las cuentas que ya quedaron por encima.

## Cómo buscar esto tú mismo

Busca **cualquier contador que el servidor mantenga por ti** y que tenga un tope:

- dispositivos, asientos o licencias de un plan,
- créditos, saldo o puntos que se gastan,
- invitaciones restantes, cupones de un solo uso,
- intentos de un código de verificación,
- unidades de stock al reservar.

El patrón de prueba es siempre el mismo, y es corto:

1. **Aprende el límite en serie.** Consume hasta que el servidor te diga que no. Guarda la
   respuesta exacta: es tu control negativo.
2. **Vuelve al estado inicial** (revoca, cancela, devuelve).
3. **Suelta N a la vez** con sincronización por último byte, no con un bucle.
4. **Pregúntale al servidor cómo se ha quedado.** El contador después de la carrera es la
   prueba, no el número de `200` que recibiste.
5. **Repite el ataque donde no debería funcionar.** Si allí entra uno solo, lo tuyo es
   real.

Y una advertencia que me ahorró tiempo: si la primera tanda te da `2 de 6`, no es que
«casi funcione». Es que funciona, y la ventana es estrecha ese día. Sube el número de
peticiones en paralelo antes de dar nada por muerto.
