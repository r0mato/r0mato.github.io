#!/usr/bin/env python3
"""
Genera los diagramas explicativos de los writeups, en español y en inglés.

Son ilustraciones del mecanismo, NO capturas de evidencia: no imitan la interfaz
de ninguna herramienta ni simulan una prueba que no se hizo.

    python3 -I _admin/diagramas.py
"""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BASE = RAIZ / "assets/img/writeups"

BG, CAJA, BORDE = "#0d1526", "#111a2d", "#22304d"
TXT, DIM = "#dbe4f3", "#8b9bb4"
ROJO, VERDE, AZUL, AMBAR = "#fb7185", "#34d399", "#60a5fa", "#fbbf24"
UI = "Inter, 'DejaVu Sans', sans-serif"
MONO = "ui-monospace, 'JetBrains Mono', 'DejaVu Sans Mono', monospace"


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def txt(x, y, s, color=TXT, tam=13.5, fuente=UI, anclaje="start", peso="400"):
    return (f'<text x="{x}" y="{y}" fill="{color}" font-family="{fuente}" font-size="{tam}" '
            f'font-weight="{peso}" text-anchor="{anclaje}">{esc(s)}</text>')


def caja(x, y, w, h, color=BORDE, relleno=CAJA, r=11, op=".6"):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{relleno}" '
            f'stroke="{color}" stroke-opacity="{op}"/>')


def flecha(x1, y1, x2, y2, color=DIM, ancho=1.8, guion=None):
    d = f' stroke-dasharray="{guion}"' if guion else ""
    return (f'<path d="M{x1} {y1} L{x2} {y2}" stroke="{color}" stroke-width="{ancho}" '
            f'marker-end="url(#f-{color.lstrip("#")})"{d}/>')


def svg(w, h, cuerpo, colores=(DIM, ROJO, VERDE, AZUL, AMBAR)):
    defs = "<defs>" + "".join(
        f'<marker id="f-{c.lstrip("#")}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" '
        f'markerHeight="6" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="{c}"/></marker>'
        for c in colores) + "</defs>"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" '
            f'height="{h}" role="img"><rect width="{w}" height="{h}" fill="{BG}"/>{defs}{cuerpo}</svg>')


def guardar(carpeta, nombre, contenido):
    d = BASE / carpeta
    d.mkdir(parents=True, exist_ok=True)
    (d / nombre).write_text(contenido, encoding="utf-8")
    print("  ", carpeta + "/" + nombre)


# ═══════════════ 1 · shell=True frente a lista de argumentos ═══════════════
def shell_true(L):
    t = dict(
        es=dict(tit="La misma orden, dos formas de ejecutarla",
                a="Lista de argumentos", a2="shell=False",
                b="Una frase entera", b2="shell=True",
                dato="8.8.8.8; touch /tmp/x",
                ra="el programa `ping` recibe un argumento raro, falla y ya está",
                rb="la shell ve el «;» y ejecuta DOS órdenes",
                ea="Los datos siguen siendo datos", eb="Los datos se han vuelto código",
                pie="Si una parte de esa frase viene de la red, quien la escribe es el servidor."),
        en=dict(tit="The same order, two ways of running it",
                a="Argument list", a2="shell=False",
                b="One whole sentence", b2="shell=True",
                dato="8.8.8.8; touch /tmp/x",
                ra="the `ping` program gets an odd argument, fails, and that is that",
                rb="the shell sees the «;» and runs TWO orders",
                ea="Data stays data", eb="Data has become code",
                pie="If part of that sentence comes from the network, the server is writing it."),
    )[L]
    b = [txt(40, 42, t["tit"], TXT, 15, UI, peso="600")]
    b.append(txt(40, 76, t["dato"], AMBAR, 13, MONO))
    b.append(flecha(250, 71, 300, 71, AMBAR))

    b += [caja(330, 56, 370, 230, VERDE), txt(350, 84, t["a"], VERDE, 14, UI, peso="600"),
          txt(350, 104, t["a2"], DIM, 11.5, MONO)]
    b.append(f'<rect x="350" y="120" width="330" height="54" rx="7" fill="#0d1526" stroke="{BORDE}"/>')
    b += [txt(364, 142, '["ping", "-c1", dato]', TXT, 12.5, MONO),
          txt(364, 161, "→ /usr/bin/ping", DIM, 11.5, MONO)]
    for i, linea in enumerate(_envolver(t["ra"], 44)):
        b.append(txt(350, 200 + i * 18, linea, DIM, 12))
    b.append(txt(350, 266, t["ea"], VERDE, 12.5, UI, peso="600"))

    b += [caja(740, 56, 370, 230, ROJO), txt(760, 84, t["b"], ROJO, 14, UI, peso="600"),
          txt(760, 104, t["b2"], DIM, 11.5, MONO)]
    b.append(f'<rect x="760" y="120" width="330" height="54" rx="7" fill="#2a1220" stroke="{ROJO}" stroke-opacity=".5"/>')
    b += [txt(774, 142, 'f"ping -c1 {dato}"', TXT, 12.5, MONO),
          txt(774, 161, "→ /bin/sh -c  …", ROJO, 11.5, MONO)]
    for i, linea in enumerate(_envolver(t["rb"], 44)):
        b.append(txt(760, 200 + i * 18, linea, DIM, 12))
    b.append(txt(760, 266, t["eb"], ROJO, 12.5, UI, peso="600"))

    b.append(txt(575, 320, t["pie"], DIM, 12.5, UI, "middle"))
    return svg(1150, 345, "".join(b))


# ═══════════════ 2 · dónde corta el navegador una URL ═══════════════
def anatomia_url(L):
    t = dict(
        es=dict(tit="Dónde corta el navegador, y dónde mira la comprobación",
                host="SERVIDOR DE DESTINO", ruta="RUTA (dentro de ese servidor)",
                chk="la comprobación busca «.marca.com» en todo el texto → lo encuentra",
                nav="el navegador solo mira hasta la primera barra → va al atacante",
                pie="Una URL no es texto: es una estructura. Compararla como texto es el fallo."),
        en=dict(tit="Where the browser cuts, and where the check looks",
                host="DESTINATION SERVER", ruta="PATH (inside that server)",
                chk="the check looks for «.brand.com» anywhere in the text → it finds it",
                nav="the browser only reads up to the first slash → it goes to the attacker",
                pie="A URL is not text: it is a structure. Comparing it as text is the bug."),
    )[L]
    marca = ".marca.com" if L == "es" else ".brand.com"
    atac = "atacante.com" if L == "es" else "attacker.com"
    b = [txt(40, 40, t["tit"], TXT, 15, UI, peso="600")]

    b.append(caja(40, 72, 1070, 86, BORDE, "#0d1526"))
    x = 70
    b.append(txt(x, 122, "https://", DIM, 20, MONO))
    x += 96
    b.append(f'<rect x="{x-8}" y="92" width="150" height="40" rx="6" fill="#2a1220" stroke="{ROJO}" stroke-opacity=".6"/>')
    b.append(txt(x, 122, atac, ROJO, 20, MONO, peso="600"))
    x += 150
    b.append(txt(x, 122, "/", AMBAR, 22, MONO, peso="700"))
    x += 16
    b.append(f'<rect x="{x-8}" y="92" width="130" height="40" rx="6" fill="#16233d" stroke="{AZUL}" stroke-opacity=".5"/>')
    b.append(txt(x, 122, marca, AZUL, 20, MONO))

    b.append(f'<path d="M152 150 L310 150" stroke="{ROJO}" stroke-width="2"/>')
    b.append(txt(152, 174, t["host"], ROJO, 11, MONO, peso="600"))
    b.append(f'<path d="M316 150 L458 150" stroke="{AZUL}" stroke-width="2"/>')
    b.append(txt(316, 174, t["ruta"], AZUL, 11, MONO, peso="600"))

    b.append(caja(40, 200, 1070, 48, BORDE, CAJA))
    b.append(txt(62, 229, "✓", VERDE, 15, UI, peso="700"))
    b.append(txt(88, 229, t["chk"], DIM, 13))
    b.append(caja(40, 258, 1070, 48, ROJO, "#2a1220"))
    b.append(txt(62, 287, "✗", ROJO, 15, UI, peso="700"))
    b.append(txt(88, 287, t["nav"], TXT, 13))

    b.append(txt(575, 340, t["pie"], DIM, 12.5, UI, "middle"))
    return svg(1150, 365, "".join(b))


# ═══════════════ 3 · la clave que viaja al navegador ═══════════════
def clave_bundle(L):
    t = dict(
        es=dict(tit="Un secreto que viaja al navegador deja de ser un secreto",
                s="SERVIDOR", n="TU NAVEGADOR", a="EL ATACANTE",
                e1="envía el fichero .js", e2="con la clave dentro",
                f1="firma la petición", f2="con la clave",
                g1="se descarga el MISMO fichero", g2="y lee la MISMA clave",
                h="firma igual de válida, sin cuenta",
                pie="La clave no distingue a la aplicación del atacante: los dos la tienen."),
        en=dict(tit="A secret that travels to the browser stops being a secret",
                s="SERVER", n="YOUR BROWSER", a="THE ATTACKER",
                e1="sends the .js file", e2="with the key inside",
                f1="signs the request", f2="with the key",
                g1="downloads the SAME file", g2="and reads the SAME key",
                h="an equally valid signature, with no account",
                pie="The key cannot tell the app from the attacker: both of them have it."),
    )[L]
    b = [txt(40, 40, t["tit"], TXT, 15, UI, peso="600")]
    b += [caja(40, 76, 230, 80, AZUL), txt(155, 112, t["s"], AZUL, 13.5, UI, "middle", "600"),
          txt(155, 134, "secret_key = …", DIM, 11.5, MONO, "middle")]
    b += [caja(460, 76, 250, 80, VERDE), txt(585, 112, t["n"], VERDE, 13.5, UI, "middle", "600"),
          txt(585, 134, t["f1"] + " " + t["f2"], DIM, 11.5, UI, "middle")]
    b += [caja(460, 220, 250, 80, ROJO), txt(585, 256, t["a"], ROJO, 13.5, UI, "middle", "600"),
          txt(585, 278, t["h"], DIM, 11.5, UI, "middle")]

    b.append(flecha(270, 108, 455, 108, VERDE))
    b.append(txt(362, 98, t["e1"], VERDE, 11.5, MONO, "middle"))
    b.append(txt(362, 128, t["e2"], DIM, 11, MONO, "middle"))
    b.append(flecha(270, 140, 455, 252, ROJO))
    b.append(txt(58, 236, t["g1"], ROJO, 11.5, MONO))
    b.append(txt(58, 254, t["g2"], DIM, 11, MONO))

    b += [caja(790, 118, 320, 140, BORDE, CAJA)]
    b.append(txt(810, 148, "POST /auth/token", TXT, 12.5, MONO))
    b.append(txt(810, 172, '{"signature": "…"}', DIM, 12, MONO))
    b.append(f'<path d="M810 190 L1090 190" stroke="{BORDE}"/>')
    b.append(txt(810, 214, "200 OK", VERDE, 12.5, MONO, peso="600"))
    b.append(txt(810, 236, 'scope: "read write"', VERDE, 12, MONO))
    b.append(flecha(712, 150, 785, 165, VERDE))
    b.append(flecha(712, 250, 785, 215, ROJO))

    b.append(txt(575, 335, t["pie"], DIM, 12.5, UI, "middle"))
    return svg(1150, 360, "".join(b))


# ═══════════════ 4 · chatbot frente a agente ═══════════════
def agente_ia(L):
    t = dict(
        es=dict(tit="La diferencia entre un chatbot y un agente",
                c="CHATBOT", a="AGENTE",
                ct="Texto entra, texto sale.", ct2="No puede tocar nada.",
                at="Texto entra, y el modelo", at2="DECIDE qué herramienta usar.",
                h1="buscar en la base de datos", h2="llamar a una API",
                h3="run_ipython_cell", h4="enviar un correo",
                peligro="ejecuta código en el servidor",
                pie="El fallo no está en lo que el modelo dice: está en lo que le han dejado hacer."),
        en=dict(tit="The difference between a chatbot and an agent",
                c="CHATBOT", a="AGENT",
                ct="Text in, text out.", ct2="It cannot touch anything.",
                at="Text in, and the model", at2="DECIDES which tool to use.",
                h1="search the database", h2="call an API",
                h3="run_ipython_cell", h4="send an email",
                peligro="runs code on the server",
                pie="The bug is not in what the model says: it is in what it was allowed to do."),
    )[L]
    b = [txt(40, 40, t["tit"], TXT, 15, UI, peso="600")]
    b += [caja(40, 72, 420, 150, VERDE), txt(60, 102, t["c"], VERDE, 14, UI, peso="600"),
          txt(60, 132, t["ct"], TXT, 13), txt(60, 154, t["ct2"], DIM, 12.5)]
    b.append(f'<rect x="60" y="172" width="380" height="32" rx="6" fill="#0d1526" stroke="{BORDE}"/>')
    b.append(txt(76, 193, "usuario → modelo → respuesta" if L == "es" else "user → model → answer", DIM, 12, MONO))

    b += [caja(500, 72, 610, 275, ROJO), txt(520, 102, t["a"], ROJO, 14, UI, peso="600"),
          txt(520, 132, t["at"], TXT, 13), txt(520, 154, t["at2"], TXT, 13)]
    for i, (h, peligrosa) in enumerate([(t["h1"], 0), (t["h2"], 0), (t["h3"], 1), (t["h4"], 0)]):
        y = 178 + i * 40
        col = ROJO if peligrosa else BORDE
        relleno = "#2a1220" if peligrosa else "#0d1526"
        b.append(f'<rect x="520" y="{y}" width="570" height="32" rx="6" fill="{relleno}" stroke="{col}" stroke-opacity=".6"/>')
        b.append(txt(538, y + 21, h, ROJO if peligrosa else DIM, 12.5, MONO, peso="600" if peligrosa else "400"))
        if peligrosa:
            b.append(txt(1074, y + 21, "← " + t["peligro"], ROJO, 11.5, UI, "end"))
    b.append(txt(575, 378, t["pie"], DIM, 12.5, UI, "middle"))
    return svg(1150, 400, "".join(b))


# ═══════════════ 5 · la cadena de los cuatro caracteres ═══════════════
def cadena_pin(L):
    pasos = dict(
        es=[("Sin cuenta", "pide un código con la clave pública", AMBAR),
            ("Código de nadie", "users_id: null", ROJO),
            ("La víctima teclea 4 caracteres", "sin saber a quién autoriza", AZUL),
            ("Credencial permanente", "sin cabecera, sin cookie, sin firma", ROJO),
            ("Correo + token de recuperación", "leídos con esa credencial", ROJO),
            ("Contraseña cambiada", "sin conocer la anterior", ROJO)],
        en=[("No account", "requests a code with the public key", AMBAR),
            ("Nobody's code", "users_id: null", ROJO),
            ("Victim types 4 characters", "without knowing who they authorise", AZUL),
            ("Permanent credential", "no header, no cookie, no signature", ROJO),
            ("Email + recovery token", "read with that credential", ROJO),
            ("Password changed", "without knowing the old one", ROJO)],
    )[L]
    tit = ("Seis peticiones y un tecleo de la víctima" if L == "es"
           else "Six requests and four characters typed by the victim")
    pie = ("Cambiar la contraseña NO echa al atacante: la credencial del paso 4 sobrevive."
           if L == "es" else
           "Changing the password does NOT evict the attacker: the step-4 credential survives.")
    b = [txt(40, 40, tit, TXT, 15, UI, peso="600")]
    y = 72
    for i, (t1, t2, col) in enumerate(pasos):
        b.append(caja(40, y, 1070, 54, col))
        b.append(f'<circle cx="72" cy="{y+27}" r="13" fill="{col}" fill-opacity=".18" stroke="{col}" stroke-opacity=".5"/>')
        b.append(txt(72, y + 32, str(i + 1), col, 12.5, MONO, "middle", "600"))
        b.append(txt(102, y + 24, t1, TXT, 13.5, UI, peso="600"))
        b.append(txt(102, y + 43, t2, DIM, 12, MONO))
        if i < len(pasos) - 1:
            b.append(flecha(575, y + 54, 575, y + 68, DIM, 1.5))
        y += 68
    b.append(txt(575, y + 18, pie, DIM, 12.5, UI, "middle"))
    return svg(1150, y + 42, "".join(b))


# ═══════════════ 6 · el enlace simbólico ═══════════════
def symlink(L):
    t = dict(
        es=dict(tit="Root escribe donde tú le digas",
                u="TÚ (usuario normal)", r="EL PROCESO ROOT",
                plant="plantas un enlace en la ruta predecible",
                ruta="~/.cliente/logs/log-<hora>.log", destino="/etc/profile.d/x.sh",
                esc="root escribe aquí...", esc2="...pero el enlace apunta allí",
                res="fichero de root, escribible por cualquiera",
                pie="La carpeta es tuya, así que la protección del kernel para /tmp no se aplica."),
        en=dict(tit="Root writes wherever you tell it to",
                u="YOU (ordinary user)", r="THE ROOT PROCESS",
                plant="you plant a link at the predictable path",
                ruta="~/.client/logs/log-<time>.log", destino="/etc/profile.d/x.sh",
                esc="root writes here...", esc2="...but the link points there",
                res="a root-owned file, writable by anyone",
                pie="The folder is yours, so the kernel's /tmp protection does not apply."),
    )[L]
    b = [txt(40, 40, t["tit"], TXT, 15, UI, peso="600")]
    b += [caja(40, 76, 290, 70, AMBAR), txt(185, 108, t["u"], AMBAR, 13.5, UI, "middle", "600"),
          txt(185, 130, t["plant"], DIM, 11.5, UI, "middle")]
    b += [caja(820, 76, 290, 70, AZUL), txt(965, 108, t["r"], AZUL, 13.5, UI, "middle", "600"),
          txt(965, 130, "touch + chmod 666", DIM, 11.5, MONO, "middle")]

    b.append(caja(400, 170, 350, 56, BORDE, "#0d1526"))
    b.append(txt(575, 194, t["ruta"], TXT, 12.5, MONO, "middle"))
    b.append(txt(575, 214, "→ enlace simbólico" if L == "es" else "→ symbolic link", AMBAR, 11.5, MONO, "middle"))

    b.append(flecha(185, 146, 420, 180, AMBAR))
    b.append(flecha(900, 146, 730, 180, AZUL))
    b.append(txt(898, 172, t["esc"], DIM, 11.5, UI, "middle"))

    b.append(flecha(575, 226, 575, 266, ROJO, 2))
    b.append(txt(595, 252, t["esc2"], ROJO, 11.5, UI))
    b.append(caja(370, 266, 410, 60, ROJO, "#2a1220"))
    b.append(txt(575, 292, t["destino"], ROJO, 13, MONO, "middle", "600"))
    b.append(txt(575, 313, t["res"], DIM, 11.5, UI, "middle"))

    b.append(txt(575, 360, t["pie"], DIM, 12.5, UI, "middle"))
    return svg(1150, 385, "".join(b))


# ═══════════════ 7 · la comilla que se cierra ═══════════════
def comillas(L):
    t = dict(
        es=dict(tit="Cómo una comilla convierte una ruta en una orden",
                e="LO QUE ESPERA EL PROGRAMA", r="LO QUE RECIBE",
                n1="la ruta es texto literal entre comillas",
                n2="la comilla CIERRA, y lo de dentro se ejecuta",
                lit="texto literal", ejec="se ejecuta",
                pie="La inyección no viaja en ningún campo: es el nombre de una carpeta."),
        en=dict(tit="How one quote turns a path into an order",
                e="WHAT THE PROGRAM EXPECTS", r="WHAT IT GETS",
                n1="the path is literal text inside quotes",
                n2="the quote CLOSES, and what follows runs",
                lit="literal text", ejec="executes",
                pie="The injection travels in no field: it is the name of a folder."),
    )[L]
    b = [txt(40, 40, t["tit"], TXT, 15, UI, peso="600")]

    b += [caja(40, 72, 1070, 110, VERDE), txt(62, 100, t["e"], VERDE, 12, MONO, peso="600")]
    b.append(f'<rect x="62" y="114" width="1026" height="44" rx="7" fill="#0d1526" stroke="{BORDE}"/>')
    b.append(txt(80, 142, "codesign -d '", DIM, 14, MONO))
    b.append(f'<rect x="190" y="124" width="136" height="26" rx="4" fill="#0c2520" stroke="{VERDE}" stroke-opacity=".5"/>')
    b.append(txt(196, 142, "/tmp/mi-app", VERDE, 14, MONO))
    b.append(txt(328, 142, "' 2>&1", DIM, 14, MONO))
    b.append(txt(416, 142, "← " + t["lit"], VERDE, 11.5, UI))

    b += [caja(40, 200, 1070, 130, ROJO), txt(62, 228, t["r"], ROJO, 12, MONO, peso="600")]
    b.append(f'<rect x="62" y="242" width="1026" height="44" rx="7" fill="#2a1220" stroke="{ROJO}" stroke-opacity=".4"/>')
    x = 80
    b.append(txt(x, 270, "codesign -d '", DIM, 14, MONO)); x += 108
    b.append(txt(x, 270, "/tmp/p", TXT, 14, MONO)); x += 58
    b.append(txt(x, 270, "'", AMBAR, 17, MONO, peso="700")); x += 11
    b.append(f'<rect x="{x-3}" y="252" width="150" height="26" rx="4" fill="#2a1220" stroke="{ROJO}"/>')
    b.append(txt(x + 3, 270, "$(sh /tmp/x.sh)", ROJO, 14, MONO, peso="600")); x += 150
    b.append(txt(x, 270, "'", AMBAR, 17, MONO, peso="700")); x += 11
    b.append(txt(x, 270, "' 2>&1", DIM, 14, MONO))
    b.append(txt(80, 308, t["n2"], ROJO, 12.5, UI))
    b.append(txt(840, 308, "↑ " + t["ejec"], ROJO, 11.5, UI))

    b.append(txt(575, 362, t["pie"], DIM, 12.5, UI, "middle"))
    return svg(1150, 385, "".join(b))


def _envolver(texto, ancho):
    palabras, lineas, actual = texto.split(), [], ""
    for p in palabras:
        if len(actual) + len(p) + 1 > ancho:
            lineas.append(actual); actual = p
        else:
            actual = (actual + " " + p).strip()
    if actual:
        lineas.append(actual)
    return lineas


DIAGRAMAS = [
    ("rce-cli-shell-true", "04-shell-true.svg", shell_true),
    ("open-redirect-sso", "02-anatomia-url.svg", anatomia_url),
    ("clave-aes-bundle-js", "02-clave-en-el-navegador.svg", clave_bundle),
    ("rce-agente-ia", "02-chatbot-vs-agente.svg", agente_ia),
    ("ato-codigo-emparejamiento", "01-cadena.svg", cadena_pin),
    ("escalada-symlink", "01-enlace-simbolico.svg", symlink),
    ("inyeccion-nombre-carpeta", "02-comillas.svg", comillas),
]

if __name__ == "__main__":
    print("Diagramas generados:")
    for carpeta, nombre, fn in DIAGRAMAS:
        guardar(carpeta, nombre, fn("es"))
        guardar(carpeta, nombre.replace(".svg", "-en.svg"), fn("en"))
