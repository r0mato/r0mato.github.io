---
title:       "Inyección de comandos en un helper privilegiado de macOS: el payload es el nombre de la carpeta"
summary:     "Un servicio con permisos de root comprobaba quién le llamaba resolviendo su ruta y metiéndola entre comillas dentro de una orden de shell. Bastó con crear una carpeta cuyo nombre contenía la inyección. Una lista negra de cuatro caracteres no fue suficiente."
date:        2026-10-23 08:30:00 +0100
lang:        es
ref:         inyeccion-nombre-carpeta-helper
image:       /assets/img/og/inyeccion-nombre-carpeta-helper-es.png

severity:    high
cvss:        "7.8"
cvss_vector: "CVSS:3.1/AV:L/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H"
cwe:         "CWE-78 · CWE-807"
vuln_class:  "Inyección"
target_type: "Servicio privilegiado (macOS)"
platform:    "YesWeHack"
status:      "Reportado"
tags:        [escalada-de-privilegios, macos, xpc, inyeccion-de-comandos, root, lista-negra]

takeaways:
  - "Una lista negra de caracteres es el control equivocado. Si tienes que enumerar lo que prohíbes, ya has perdido."
  - "El sistema de ficheros es una entrada de usuario: el nombre de una carpeta puede llevar una inyección dentro."
  - "Identificar a quien te llama por su PID es una carrera perdida de antemano; en macOS existe un mecanismo criptográfico para eso y el producto ya lo usaba en otro sitio."
  - "Si el propio código del fabricante documenta la frontera que su fallo cruza, cítalo. Nada convence más que su propio comentario."
---

En macOS, una aplicación que necesita tocar la configuración del sistema instala un
**ayudante privilegiado**: un proceso aparte que corre como root de forma permanente y al
que la aplicación le pide favores. Toda su seguridad se reduce a una pregunta: cómo
comprueba quién le habla.

Este lo hacía así:

1. Pedía el **PID** de quien le hablaba.
2. Con él resolvía la **ruta del ejecutable** en disco.
3. Comprobaba que la ruta no tuviera ciertos caracteres prohibidos.
4. La metía **entre comillas simples** en una orden de shell para verificar la firma.
5. Ejecutaba con `popen()`, que es `/bin/sh -c "…"`.

```c
std::string cmd = "/usr/bin/codesign -d --verbose=4 '" + ruta + "' 2>&1";
std::string salida = ejecutarConSalida(cmd);   // popen() → /bin/sh -c
```

El paso 4 es el fallo: la ruta la elige el atacante, porque elige dónde pone su programa.

## Las comillas y la lista negra

Las comillas simples son la forma más fuerte de decir «esto es texto literal», y además
había una lista negra de cuatro caracteres. Lo que se escapó fue la propia comilla simple:
si la **cierras**, lo que venga después ya no es texto.

```bash
# el programa construye esto:
codesign -d --verbose=4 '<RUTA>' 2>&1

# si la ruta es:   /tmp/p'$(mi-script)'
codesign -d --verbose=4 '/tmp/p'$(mi-script)'' 2>&1
#                        └ cierra ┘└ se ejecuta ┘
```

<figure>
  <img src="{{ '/assets/img/writeups/inyeccion-nombre-carpeta/02-comillas.svg' | relative_url }}"
       alt="Diagrama comparando la orden que el programa espera, con la ruta entre comillas como texto literal, y la que recibe, donde una comilla dentro del nombre cierra el entrecomillado y lo siguiente se ejecuta">
  <figcaption>Arriba, lo que el programa cree que está ejecutando. Abajo, lo que ejecuta de verdad.</figcaption>
</figure>

## El payload es el nombre de la carpeta

La ruta no me la invento: es dónde está mi programa. Así que para inyectar hay que crear
una carpeta cuyo nombre **sea** la inyección.

```bash
mkdir "/tmp/p\$(/bin/sh /tmp/x.sh)"
```

No envío ningún dato malicioso por ningún campo. Creo una carpeta con un nombre raro y
meto mi programa dentro. Cuando el ayudante pregunte dónde vive, la respuesta es el ataque.
Una comilla, un dólar y un paréntesis: nombre perfectamente legal en macOS.

Un detalle que obliga a diseñarlo con cuidado: el nombre **no puede llevar barra**, porque
es el único carácter que un sistema de ficheros no permite. Por eso el payload no puede ser
un comando con rutas, tiene que llamar a un script que esté en otro sitio.

## El resto de la cadena

Antes de llegar a la línea vulnerable, el ayudante verificaba que el programa estuviera
firmado con el identificador del producto. No es una barrera: macOS permite firmar
cualquier binario de forma improvisada, sin certificado de desarrollador, con el
identificador que quieras. Comprueba que el carnet lleve el nombre de la empresa, no que lo
haya emitido ella.

## Qué se alcanza

<figure>
  <img src="{{ '/assets/img/writeups/inyeccion-nombre-carpeta/01-root-desde-cuenta-normal.png' | relative_url }}"
       alt="Terminal de una cuenta sin privilegios (uid 502). El codigo ejecutado responde whoami -> root y uid=0(root), escribe y borra un fichero canario en un directorio solo de root, y lee la base de datos de cuentas del sistema">
  <figcaption>Desde una cuenta normal (<code>uid=502</code>): <code>whoami → root</code>. Escribe un canario en un directorio reservado a root <strong>y lo borra</strong>, y lee el fichero de cuentas del sistema. La lista de grupos va tapada porque incluye uno del producto.</figcaption>
</figure>

Leyendo, nunca modificando: la base de datos local de credenciales y el fichero de cuentas,
legibles solo por root. Y el propio servicio privilegiado del producto, que root puede
reescribir — es decir, el atacante puede reemplazar el ayudante por uno suyo y quedarse
dentro aunque desinstalen la aplicación.

Un detalle que lo empeora: cuando el ayudante rechaza a un llamante que no reconoce,
termina de golpe. La instalación legítima que estuviera en curso falla con un error
genérico. Parece un fallo del instalador, no un ataque.

## El argumento que cierra el reporte

En los scripts del propio instalador había un comentario de sus desarrolladores diciendo,
en esencia, que *de lo contrario un proceso sin privilegios podría pedir una reinstalación
en cualquier momento*. El fabricante había escrito cuál era la frontera que quería
defender; mi reporte demostraba que estaba rota citando su propia frase. Eso convence más
que cualquier opinión mía.

## Impacto

<div class="impact" markdown="1">
Una cuenta de usuario normal de ese Mac —sin contraseña de administrador y sin poder usar
`sudo`— pasa a **ejecutar código como root**. No hace falta engañar a nadie ni esperar a
nada: basta con crear una carpeta con el nombre adecuado y pedirle al ayudante que haga su
trabajo.

Siendo root en la máquina se alcanzan la base de datos local de credenciales y el fichero
de cuentas del sistema, y se puede escribir en directorios reservados al sistema, que es
donde vive el arranque automático.

Lo que lo agrava: el atacante puede **reescribir el propio componente privilegiado**. A
partir de ahí sigue dentro aunque la víctima desinstale la aplicación, porque lo que queda
instalado ya no es del fabricante.

Severidad **alta (CVSS 7.8)**. Local, pero completa: cualquier cuenta del equipo es
administrador del equipo.
</div>
