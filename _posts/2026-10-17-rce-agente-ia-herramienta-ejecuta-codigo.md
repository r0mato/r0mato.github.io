---
title:       "RCE 9.8 en producción a través de un agente de IA con una herramienta que ejecuta código"
summary:     "Un asistente conversacional interno tenía, entre sus herramientas, una que ejecutaba Python en el servidor. Cualquiera podía pedírselo. Lo demostré con un canario criptográfico, porque «el modelo se lo ha inventado» es la objeción que mata estos reportes."
date:        2026-10-17 17:20:00 +0100
lang:        es
ref:         rce-agente-ia-tool
image:       /assets/img/og/rce-agente-ia-tool-es.png

severity:    critical
cvss:        "9.8"
cvss_vector: "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
cwe:         "CWE-94 · CWE-862"
vuln_class:  "Inyección"
target_type: "Agente de IA (API)"
platform:    "YesWeHack"
status:      "Corregido"
tags:        [rce, ia, llm, agentes, python, kubernetes, inyeccion-de-codigo]

takeaways:
  - "En un agente de IA el fallo casi nunca está en el modelo: está en las **herramientas** que le han dado y en quién puede invocarlas."
  - "«El modelo se lo ha inventado» es la objeción que mata estos reportes. Un canario criptográfico la cierra de un golpe: un modelo no puede acertar un SHA-256."
  - "Pregúntale al agente qué herramientas tiene. Muchas veces te las lista."
  - "Dos fallos distintos con la misma puerta de entrada siguen siendo dos fallos: uno se arregla rotando una clave y el otro quitando una herramienta."
---

Este es el fallo técnicamente más grave que he encontrado, y el que mejor enseña por qué
los asistentes de IA son una superficie de ataque nueva y distinta. Spoiler: **el problema
no era el modelo de lenguaje**. El problema era lo que le habían dejado hacer.

<div class="warn" markdown="1">
**Todo está anonimizado.** Publicado con permiso del programa y sin identificar al
producto: empresa, dominios, rutas, nombres de servicio y de agente están cambiados. El
mecanismo, el método de verificación y el impacto son exactos.
</div>

## Primero, qué es un «agente» y por qué cambia las reglas

Un chatbot normal recibe texto y devuelve texto. Si le pides que borre un fichero, te
contesta algo bonito y no pasa nada, porque **no puede tocar nada**.

Un **agente** es otra cosa. A un agente le das *herramientas*: buscar en una base de datos,
llamar a una API, mandar un correo, ejecutar código. El modelo decide **cuál usar** según
lo que le pides, y el sistema **la ejecuta de verdad**.

Un chatbot es alguien al teléfono dándote consejos. Un agente es alguien
al teléfono **con las llaves de tu casa**. La conversación es igual de inofensiva; lo que
cambia es lo que puede hacer mientras habla contigo.

Por eso, cuando auditas un asistente de IA, la pregunta no es «¿puedo hacer que diga
tonterías?». La pregunta es **«¿qué herramientas tiene y quién puede pedirle que las
use?»**.

<figure>
  <img src="{{ '/assets/img/writeups/rce-agente-ia/02-chatbot-vs-agente.svg' | relative_url }}"
       alt="Diagrama comparando un chatbot, que solo devuelve texto, con un agente, que tiene una lista de herramientas entre las que hay una que ejecuta código en el servidor">
  <figcaption>Un chatbot responde. Un agente actúa. Y la lista de lo que puede hacer es la superficie de ataque.</figcaption>
</figure>

## El objetivo

El asistente interno de un portal corporativo. Ya había encontrado antes cómo hablar con
él sin tener cuenta —[la clave de firma estaba en un fichero JavaScript público]({{ '/writeups/clave-aes-en-bundle-js-tokens-sin-cuenta/' | relative_url }})—
así que podía mandarle mensajes como un empleado cualquiera.

La pregunta siguiente era obvia: **¿qué sabe hacer este chisme?**

## Paso 1: preguntarle qué herramientas tiene

No hace falta ingeniería inversa. Muchas veces basta con preguntar:

```
¿Qué herramientas tienes disponibles? Enumera sus nombres exactos.
```

Entre la lista apareció una que me hizo enderezarme en la silla:

```
run_ipython_cell
```

El nombre no deja lugar a dudas: una herramienta que «ejecuta una celda de IPython» ejecuta el código Python que le den, dentro de un asistente al que puede escribir cualquiera.

## Paso 2: la trampa en la que cae casi todo el mundo

La tentación es pedirle que ejecute algo y enseñar la respuesta. Así:

```
Ejecuta: import os; print(os.getcwd())
```

Y el asistente contesta algo como `/app/workspace`. ¿Ya está? **No.** Y esta es la lección
más valiosa de todo el artículo:

<div class="warn" markdown="1">
**Un modelo de lenguaje puede inventarse esa respuesta entera.** Está entrenado con
millones de sesiones de terminal. Si le pides el directorio actual, te dirá algo plausible
tanto si ha ejecutado el código como si no.

Si envías ese reporte, quien lo tría responderá —con razón— *«el modelo ha alucinado la
salida»*, y lo cerrará. He visto morir muchos reportes de IA exactamente así.
</div>

Necesitas una prueba que **un modelo no pueda falsificar**.

## Paso 3: el canario criptográfico

La solución es elegante y la puedes reutilizar siempre: pídele que calcule algo cuyo
resultado sea **imposible de adivinar pero trivial de verificar**.

Un hash SHA-256 cumple las dos condiciones.

```bash
# 1 · en MI máquina, ANTES de tocar el servidor
python3 -c 'import hashlib; print(hashlib.sha256(b"canario-verificacion-20261017-7f3ad9").hexdigest())'
# 0e407c15aa4778af3f4ba76dbfa2b0d3fd990d2f365bdf3aa3d95091e4069005
```

Un hash es una huella digital de un texto. Cambia una letra y la huella
cambia entera. No hay forma de «deducirla»: hay que calcularla.

Un modelo de lenguaje **no sabe calcular hashes**. Puede recitar hashes famosos que vio en
su entrenamiento, pero no puede producir el de una cadena que me acabo de inventar. Si el
servidor me devuelve exactamente la misma huella que calculé en mi portátil, solo hay una
explicación posible: **ha ejecutado el código de verdad**.

Y ahora, al asistente:

```http
POST /asistente/chat/v1/mensajes HTTP/2
Host: portal.ejemplo.tld
X-Authorization: <token fabricado, sin cuenta>

{"user":"canario-bbtest",
 "query":"Usa run_ipython_cell para ejecutar esta línea y pega la salida literal:
          import hashlib; print(hashlib.sha256(b\"canario-verificacion-20261017-7f3ad9\").hexdigest())",
 "is_agent":"1"}
```

La respuesta llegó como un flujo de eventos, y dentro venía esto:

```json
{"actionName":"run_ipython_cell",
 "observation":"0e407c15aa4778af3f4ba76dbfa2b0d3fd990d2f365bdf3aa3d95091e4069005"}
```

**Carácter por carácter, el mismo.** Eso cierra la discusión.

<figure>
  <img src="{{ '/assets/img/writeups/rce-agente-ia/03-canario.svg' | relative_url }}"
       alt="Diagrama del canario: el hash se calcula en la máquina propia, se pide al agente que lo calcule con su herramienta, y los dos valores se comparan">
  <figcaption>El hash se calcula antes de tocar el servidor. Si vuelve idéntico, se ha ejecutado.</figcaption>
</figure>

Y lo repetí **dos veces más, con cadenas distintas**, para descartar cualquier casualidad o
caché. Un canario podría ser suerte; tres no lo son.

## Paso 4: ¿dónde se está ejecutando esto?

Una vez probada la ejecución, toca medir hasta dónde llega. Con cuidado y sin tocar nada:

```python
import os, socket
print(os.getuid())        # 0  -> root
print(socket.gethostname())
print(len(os.environ))    # variables del proceso
```

El resultado: **uid 0 (root)**, dentro de un contenedor de un clúster de producción, con
visibilidad de red a varias decenas de servicios internos y credenciales en las variables
de entorno del proceso.

<figure>
  <img src="{{ '/assets/img/writeups/rce-agente-ia/01-root.png' | relative_url }}"
       alt="Fragmento de la respuesta del agente: el campo arguments lleva el codigo import os as o;print(o.popen(whoami).read().strip()) y el campo observation devuelve root, recuadrado en rojo">
  <figcaption>El agente ejecuta la línea y devuelve la salida: <code>observation: "root"</code>. Recorte de la respuesta; el resto lleva identificadores del producto.</figcaption>
</figure>

El código no se ejecutaba en una caja aislada de juguete. Se ejecutaba
como administrador dentro de la red interna de la empresa, con acceso a otros servicios que
nunca deberían estar al alcance de internet. Desde ahí, un atacante no «habla con un
chatbot»: **está dentro**.

<div class="note" markdown="1">
**Dónde paré.** Leí el identificador de usuario, el nombre de la máquina y conté cuántas
variables de entorno había. **No** leí su contenido, no me moví a ningún servicio interno,
no toqué datos y no dejé nada instalado. Para demostrar «ejecuto código como root en
producción» eso sobra; todo lo demás ya es intrusión, no investigación.
</div>

## Por qué lo reporté aparte del otro fallo

La puerta de entrada era la misma: el token que se podía fabricar con la clave del fichero
JavaScript. Podría parecer el mismo reporte. **No lo es**, y argumentarlo bien fue parte
del trabajo:

| | Fallo de autenticación | Este |
|---|---|---|
| **Qué es** | Se puede entrar sin cuenta | Hay una herramienta que ejecuta código |
| **Cómo se arregla** | Rotando la clave y atando el token a un usuario | Quitando la herramienta del agente |
| **Si arreglan solo el otro** | — | Sigue explotable **por cualquier empleado legítimo** |

Ese último punto es el argumento decisivo: aunque arreglaran la autenticación mañana,
cualquier empleado con acceso normal al chat seguiría pudiendo ejecutar código como root en
producción. Son dos fallos con dos arreglos distintos.

Una cosa es que la puerta de la calle esté abierta y otra que dentro haya
una palanca que vuela el edificio. Arreglar la puerta no quita la palanca.

## Impacto

<div class="impact" markdown="1">
**Impacto.** Ejecución de código arbitrario como **root** en un contenedor de producción,
alcanzable desde internet y sin necesidad de cuenta. Desde esa posición: lectura de las
credenciales del proceso, movimiento lateral hacia los servicios internos visibles,
y acceso a los datos que esos servicios custodian. En la práctica, el peor resultado
posible para una aplicación expuesta.
</div>
