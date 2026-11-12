---
title:       "El nombre de una carpeta como arma: inyección de comandos en un ayudante privilegiado de macOS"
summary:     "Un servicio con permisos de root comprobaba quién le llamaba resolviendo su ruta y metiéndola entre comillas dentro de una orden de shell. Bastó con crear una carpeta cuyo nombre contenía la inyección. Una lista negra de cuatro caracteres no fue suficiente."
date:        2026-11-11 20:40:00 +0100
lang:        es
ref:         inyeccion-nombre-carpeta-helper

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

Este fallo tiene mi parte favorita de la seguridad ofensiva: la solución no está en enviar
un dato raro, sino en **crear una carpeta**. El sistema de ficheros, que nadie considera
una entrada de usuario, es la entrada de usuario.

<div class="warn" markdown="1">
**Todo está anonimizado.** Fabricante, identificadores de servicio y rutas del producto
están cambiados. El mecanismo, las comprobaciones que hace el binario y la técnica son
exactos.
</div>

## Qué es un «ayudante privilegiado»

En macOS, una aplicación normal no puede tocar la configuración del sistema. Cuando
necesita hacerlo —configurar red, instalar un servicio, modificar carpetas protegidas— se
instala un **ayudante privilegiado**: un programita separado que corre **como root** de
forma permanente y al que la aplicación le pide favores.

<div class="plain" markdown="1">
**En cristiano:** es un mayordomo con llaves de todo. La aplicación no abre las puertas: se
lo pide al mayordomo. Y como el mayordomo tiene todas las llaves, **lo único que lo separa
del desastre es saber a quién le está obedeciendo**.

De ahí que toda la seguridad de estos componentes se reduzca a una pregunta: ¿cómo
comprueba quién le está hablando?
</div>

## Cómo comprobaba este quién le llamaba

El ayudante hacía esto, en este orden:

1. Pedía el **PID** —el número de proceso— de quien le hablaba.
2. Con ese número, resolvía la **ruta del ejecutable** en el disco.
3. Comprobaba que esa ruta no contuviera ciertos caracteres prohibidos.
4. Metía la ruta **entre comillas simples** dentro de una orden de shell, para verificar la
   firma digital del programa.
5. Ejecutaba esa orden con `popen()`, que es lanzar `/bin/sh -c "…"`.

```c
std::string cmd = "/usr/bin/codesign -d --verbose=4 '" + ruta + "' 2>&1";
std::string salida = ejecutarConSalida(cmd);   // popen() → /bin/sh -c
```

El paso 4 es el fallo. La ruta —algo que **el atacante elige**, porque elige dónde pone su
programa— acaba dentro de una cadena que interpreta la shell.

<div class="plain" markdown="1">
**En cristiano:** el mayordomo, para comprobar tu identidad, escribe tu dirección en un
papel, se lo da al cocinero y le dice «haz lo que ponga aquí». Si tu dirección es
*«Calle Mayor 5; quema la casa»*, el cocinero lee las dos cosas.
</div>

## Las comillas simples: la falsa seguridad

El desarrollador no fue ingenuo del todo. Puso la ruta **entre comillas simples**, que en
una shell es la forma más fuerte de decir «esto es texto literal».

```bash
echo 'esto $(no) se ejecuta'      # sale tal cual
```

Y además añadió una **lista negra de cuatro caracteres**, para que no te colaras.

<div class="plain" markdown="1">
**En cristiano:** una lista negra es la estrategia de *«voy a prohibir lo peligroso»*. El
problema es que para que funcione tienes que haber pensado en **todo** lo peligroso. Y
siempre, siempre, se te escapa algo.

Lo que se escapó aquí fue la propia comilla simple. Si tú **cierras** la comilla, lo que
venga después ya no es texto literal: es código.
</div>

```bash
# el programa construye esto:
codesign -d --verbose=4 '<RUTA>' 2>&1

# si la ruta es:   /tmp/p'$(mi-script)'
# queda:
codesign -d --verbose=4 '/tmp/p'$(mi-script)'' 2>&1
#                        └ cierra ┘└ se ejecuta ┘
```

## La idea: que la inyección sea el nombre de la carpeta

Aquí está lo bonito. La «ruta» no me la invento: es **dónde está mi programa**. Así que
para inyectar, tengo que **crear una carpeta cuyo nombre sea la inyección**:

```bash
mkdir "/tmp/p\$(/bin/sh /tmp/x.sh)"
```

<div class="plain" markdown="1">
**En cristiano:** no estoy enviando un dato malicioso por ningún campo. Estoy creando una
carpeta con un nombre raro y metiendo mi programa dentro. Cuando el mayordomo pregunte
«¿dónde vives?», la respuesta **es** el ataque.

Y es un nombre de carpeta perfectamente legal en macOS: una comilla, un dólar y un
paréntesis. Nada prohibido.
</div>

Un detalle precioso de este caso: el nombre **no puede contener una barra `/`**, porque es
el único carácter que los sistemas de ficheros no permiten en un nombre. Por eso el payload
no puede ser un comando con rutas: tiene que **llamar a un script** que esté en otro sitio.
Las limitaciones del sistema de ficheros te obligan a diseñar el payload con cuidado, y eso
es parte de la gracia.

## El resto de la cadena

Faltaba una comprobación intermedia: el ayudante verificaba que el programa estuviera
**firmado** con el identificador del producto, antes de llegar a la línea vulnerable.

Eso suena a barrera, pero no lo es: macOS permite firmar cualquier binario **de forma
improvisada**, sin certificado de desarrollador, poniéndole el identificador que quieras.
Y eso es exactamente lo que la comprobación miraba.

<div class="plain" markdown="1">
**En cristiano:** el mayordomo mira que lleves un carnet con el nombre de la empresa. Pero
no comprueba que lo haya emitido la empresa — solo que lo ponga. Y cualquiera puede
imprimirse uno.
</div>

{% comment %} PENDIENTE DE CAPTURA — quita esta linea y la de cierre cuando exista el fichero
<figure>
  <img src="{{ '/assets/img/writeups/inyeccion-nombre-carpeta/01-root-conseguido.png' | relative_url }}"
       alt="Terminal del usuario sin privilegios mostrando el fichero canario escrito por root y la lectura de ficheros que solo root puede leer">
  <figcaption>Desde una cuenta sin privilegios: ficheros que solo root puede leer, en pantalla.</figcaption>
</figure>
{% endcomment %}

## Qué se alcanza desde ahí

Con el código ejecutándose como root pude comprobar —leyendo, nunca modificando— que se
alcanzaba:

- **La base de datos local de credenciales** del sistema y el fichero de cuentas, legibles
  solo por root.
- **El propio servicio privilegiado del producto**, que root puede reescribir. Es decir:
  el atacante puede reemplazar el mayordomo por uno suyo.

<div class="plain" markdown="1">
**En cristiano:** una vez eres root en un Mac, el producto que estabas atacando es lo de
menos. Tienes la máquina. Y en este caso, además, tienes la capacidad de modificar el
propio componente privilegiado, con lo que te quedas dentro aunque desinstalen la
aplicación.
</div>

Y un detalle que lo hace peor: cuando el ayudante rechaza a un llamante que no reconoce,
**termina de golpe**. Resultado: la instalación legítima que estuviera en curso falla con
un error genérico de instalación. Parece un fallo del instalador, no un ataque.

## El control negativo

| Qué probé | Qué pasó | Qué descarta |
|---|---|---|
| El mismo programa desde una ruta **normal** | Funciona: ninguna ejecución extra | Que el ayudante ejecutara cosas por su cuenta |
| La ruta con la inyección pero **sin** la firma improvisada | Rechazado antes de llegar | Que la comprobación de firma no existiera |
| Repetirlo entero **otra vez**, con otro canario y otro nombre | Mismo resultado | Que fuera un estado raro de una ejecución concreta |

Repetirlo desde cero con **otro nombre de canario** es lo que convierte «me ha pasado una
vez» en «esto es reproducible». Un triador que no puede reproducir tu fallo, lo cierra.

## El argumento que cierra el reporte

Al leer los scripts del propio instalador del producto, encontré un comentario de sus
desarrolladores que decía, en esencia, que *de lo contrario un proceso sin privilegios
podría pedir una reinstalación en cualquier momento*.

<div class="plain" markdown="1">
**En cristiano:** el fabricante había escrito, en su propio código, cuál era la frontera
que quería defender. Mi reporte demostraba que esa frontera estaba rota, **citando su
propia frase**.

Esto es de lo más eficaz que puedes meter en un reporte: no es tu opinión sobre lo que
debería pasar, es la suya.
</div>

## El arreglo

1. **No construir una orden de shell.** El binario ya tenía dentro una forma segura de
   lanzar programas con una lista de argumentos. Usarla elimina la clase entera:

   ```c
   - std::string cmd = "/usr/bin/codesign -d --verbose=4 '" + ruta + "' 2>&1";
   - ejecutarConSalida(cmd);                 // popen() → /bin/sh -c
   + const char *argv[] = {"/usr/bin/codesign", "-d", "--verbose=4", ruta, NULL};
   + ejecutarConSalidaArgv(argv);            // sin shell: no hay nada que escapar
   ```

2. **Identificar al llamante por su token de auditoría**, no por su PID y su ruta. macOS
   ofrece un mecanismo criptográfico para esto que no se puede suplantar. El producto
   **ya lo usaba** en otra parte del mismo binario: solo había que aplicarlo también aquí.

3. **Borrar la lista negra.** Con argumentos separados no hay nada que filtrar. Y una lista
   negra de metacaracteres es, de todas formas, el control equivocado.

<div class="plain" markdown="1">
**En cristiano:** identificar un proceso por su PID es inseguro por naturaleza, porque los
números de proceso **se reutilizan**: un atacante puede hacer que el suyo muera y que otro
ocupe su número justo en el momento de la comprobación. Por eso existen los tokens de
auditoría, que identifican al proceso de forma que no se puede falsificar.
</div>

## Cómo buscar esto tú mismo

En cualquier servicio privilegiado de macOS:

1. **Encuéntralos:** `ls -la /Library/PrivilegedHelperTools/` y
   `ls /Library/LaunchDaemons/`.
2. **Mira qué funciones importa:** si aparece `popen`, `system` o `exec` + construcción de
   cadenas, enciende la alarma.
   ```bash
   nm -u /Library/PrivilegedHelperTools/com.ejemplo.helper | grep -E 'popen|system|exec'
   ```
3. **Busca cómo identifica al llamante:** si ves `xpc_connection_get_pid` y `proc_pidpath`
   pero **no** `SecCodeCreateWithAuditToken`, la identificación es por PID y es
   suplantable.
4. **Pregúntate qué parte de esa cadena controlas tú.** La ruta de tu propio binario es lo
   primero: y la eliges creando carpetas.

<div class="note" markdown="1">
**Hazlo solo en tu propia máquina.** Esto se investiga en una máquina virtual tuya, con
cuentas tuyas, y se para en cuanto la primitiva está demostrada. Un canario inofensivo
prueba exactamente lo mismo que un ataque real, y no deja a nadie en una situación
comprometida — empezando por ti.
</div>
