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


# ═══════════════ 8 · lo que ve la víctima al confirmar ═══════════════
def pantalla_consentimiento(L):
    t = dict(
        es=dict(tit="Consentimiento sin información no es consentimiento",
                ve="LO QUE VE LA VÍCTIMA", deb="LO QUE DEBERÍA VER",
                pregunta="¿Autorizar este dispositivo?",
                code="Código: 7MTU", si="Autorizar", no="Cancelar",
                campos=[("Cliente", "Android · app de televisor"),
                        ("Dirección IP", "203.0.113.47"),
                        ("Ubicación", "a 600 km de tu ubicación habitual"),
                        ("Solicitado", "hace 4 segundos")],
                pie="Sin esos cuatro datos, nadie puede distinguir su televisor del portátil de un desconocido."),
        en=dict(tit="Consent without information is not consent",
                ve="WHAT THE VICTIM SEES", deb="WHAT THEY SHOULD SEE",
                pregunta="Authorise this device?",
                code="Code: 7MTU", si="Authorise", no="Cancel",
                campos=[("Client", "Android · TV app"),
                        ("IP address", "203.0.113.47"),
                        ("Location", "600 km from your usual location"),
                        ("Requested", "4 seconds ago")],
                pie="Without those four facts, nobody can tell their own TV from a stranger's laptop."),
    )[L]
    b = [txt(40, 42, t["tit"], TXT, 15, UI, peso="600")]

    b += [caja(40, 76, 470, 210, ROJO), txt(62, 104, t["ve"], ROJO, 11.5, MONO, peso="600")]
    b.append(f'<rect x="62" y="120" width="426" height="146" rx="8" fill="#0d1526" stroke="{BORDE}"/>')
    b.append(txt(275, 162, t["pregunta"], TXT, 15, UI, "middle", "600"))
    b.append(txt(275, 188, t["code"], DIM, 13, MONO, "middle"))
    b.append(f'<rect x="130" y="212" width="130" height="34" rx="7" fill="#16233d" stroke="{AZUL}" stroke-opacity=".5"/>')
    b.append(txt(195, 234, t["si"], AZUL, 13, UI, "middle", "600"))
    b.append(f'<rect x="290" y="212" width="130" height="34" rx="7" fill="#0d1526" stroke="{BORDE}"/>')
    b.append(txt(355, 234, t["no"], DIM, 13, UI, "middle"))

    b += [caja(560, 76, 550, 210, VERDE), txt(582, 104, t["deb"], VERDE, 11.5, MONO, peso="600")]
    b.append(f'<rect x="582" y="120" width="506" height="146" rx="8" fill="#0d1526" stroke="{BORDE}"/>')
    b.append(txt(602, 146, t["pregunta"], TXT, 14, UI, peso="600"))
    y = 172
    for k, v in t["campos"]:
        b.append(txt(602, y, k, DIM, 11.5, MONO))
        b.append(txt(760, y, v, TXT, 12))
        y += 23
    b.append(txt(575, 320, t["pie"], DIM, 12.5, UI, "middle"))
    return svg(1150, 345, "".join(b))


# ═══════════════ 9 · el canario criptográfico ═══════════════
def canario(L):
    t = dict(
        es=dict(tit="Por qué un hash cierra la objeción de «el modelo se lo ha inventado»",
                a="1 · EN MI MÁQUINA", b="2 · AL AGENTE", c="3 · COMPARAR",
                a1="cadena inventada ahora mismo", a2="sha256(...) = 0e407c15…",
                b1="«usa run_ipython_cell y pega", b2="la salida literal»",
                b3="observation: 0e407c15…",
                si="IDÉNTICOS → ha ejecutado el código",
                no="Sin la herramienta, el modelo inventa un hash y falla",
                pie="Un modelo no puede calcular el SHA-256 de una cadena que acabas de inventar."),
        en=dict(tit="Why a hash closes the \"the model made it up\" objection",
                a="1 · ON MY MACHINE", b="2 · TO THE AGENT", c="3 · COMPARE",
                a1="a string invented just now", a2="sha256(...) = 0e407c15…",
                b1="\"use run_ipython_cell and paste", b2="the literal output\"",
                b3="observation: 0e407c15…",
                si="IDENTICAL → it really ran the code",
                no="Without the tool, the model invents a hash and gets it wrong",
                pie="A model cannot compute the SHA-256 of a string you have just invented."),
    )[L]
    b = [txt(40, 42, t["tit"], TXT, 15, UI, peso="600")]
    b += [caja(40, 76, 320, 110, VERDE), txt(62, 104, t["a"], VERDE, 11.5, MONO, peso="600"),
          txt(62, 132, t["a1"], DIM, 12), txt(62, 160, t["a2"], VERDE, 12.5, MONO, peso="600")]
    b.append(flecha(362, 130, 412, 130, DIM))
    b += [caja(415, 76, 360, 110, AZUL), txt(437, 104, t["b"], AZUL, 11.5, MONO, peso="600"),
          txt(437, 128, t["b1"], DIM, 12), txt(437, 146, t["b2"], DIM, 12),
          txt(437, 172, t["b3"], AZUL, 12.5, MONO, peso="600")]
    b.append(flecha(777, 130, 827, 130, DIM))
    b += [caja(830, 76, 280, 110, VERDE, "#0c2520"),
          txt(852, 104, t["c"], VERDE, 11.5, MONO, peso="600")]
    for i, linea in enumerate(_envolver(t["si"], 30)):
        b.append(txt(852, 134 + i * 19, linea, VERDE, 12.5, UI, peso="600"))
    b.append(caja(40, 210, 1070, 46, ROJO, "#2a1220"))
    b.append(txt(62, 239, "✗", ROJO, 14, UI, peso="700"))
    b.append(txt(88, 239, t["no"], TXT, 13))
    b.append(txt(575, 290, t["pie"], DIM, 12.5, UI, "middle"))
    return svg(1150, 315, "".join(b))


# ═══════════════ 10 · la cadena del ticket de sesión ═══════════════
def cadena_sso(L):
    t = dict(
        es=dict(tit="Un clic, y la sesión cambia de dueño",
                p1="La víctima abre un enlace", p1b="dominio visible: el del fabricante",
                p2="El SSO ve su sesión abierta", p2b="no pide contraseña: emite el ticket",
                p3="Redirección al dominio del atacante", p3b="el ticket viaja en la URL",
                p4="El atacante lo lee en su propio log", p4b="sin tocar a la víctima otra vez",
                p5="Canjea el ticket desde cero", p5b="sin cookie, sin contraseña → sesión completa",
                pie="El fallo no es la redirección: es que la redirección se lleva una credencial."),
        en=dict(tit="One click, and the session changes hands",
                p1="The victim opens a link", p1b="visible domain: the vendor's",
                p2="The SSO sees their open session", p2b="no password asked: it issues the ticket",
                p3="Redirect to the attacker's domain", p3b="the ticket travels in the URL",
                p4="The attacker reads it in their own log", p4b="without touching the victim again",
                p5="Redeems the ticket from scratch", p5b="no cookie, no password → full session",
                pie="The bug is not the redirect: it is that the redirect carries a credential."),
    )[L]
    cols = [AZUL, AZUL, AMBAR, ROJO, ROJO]
    b = [txt(40, 42, t["tit"], TXT, 15, UI, peso="600")]
    x = 40
    ancho = 200
    for i in range(5):
        col = cols[i]
        b.append(caja(x, 76, ancho, 132, col))
        b.append(f'<circle cx="{x+22}" cy="{98}" r="12" fill="{col}" fill-opacity=".18" stroke="{col}" stroke-opacity=".5"/>')
        b.append(txt(x + 22, 103, str(i + 1), col, 12, MONO, "middle", "600"))
        for j, linea in enumerate(_envolver(t[f"p{i+1}"], 22)):
            b.append(txt(x + 16, 134 + j * 17, linea, TXT, 12.5, UI, peso="600"))
        for j, linea in enumerate(_envolver(t[f"p{i+1}b"], 29)):
            b.append(txt(x + 16, 176 + j * 14, linea, DIM, 10, MONO))
        if i < 4:
            b.append(flecha(x + ancho, 142, x + ancho + 18, 142, DIM, 1.6))
        x += ancho + 18
    b.append(txt(575, 246, t["pie"], DIM, 12.5, UI, "middle"))
    return svg(1150, 272, "".join(b))


# ═══════════════ 11 · qué se intercepta en el MITM ═══════════════
def mitm(L):
    t = dict(
        es=dict(tit="Solo se envenena una petición; el resto pasa de largo",
                v="CLIENTE DE LA VÍCTIMA", p="PROXY DEL ATACANTE", r="SERVIDOR REAL",
                ok="se reenvía tal cual", mal="respuesta sustituida",
                lista=[("POST /login", 0), ("GET /servers", 0),
                       ("GET /servers/<id>/configs", 1), ("GET /certs.zip", 0)],
                pie="La aplicación no nota nada raro: todo funciona salvo el campo que importa."),
        en=dict(tit="Only one request is poisoned; the rest passes straight through",
                v="VICTIM'S CLIENT", p="ATTACKER'S PROXY", r="REAL SERVER",
                ok="forwarded unchanged", mal="response replaced",
                lista=[("POST /login", 0), ("GET /servers", 0),
                       ("GET /servers/<id>/configs", 1), ("GET /certs.zip", 0)],
                pie="The app notices nothing: everything works except the one field that matters."),
    )[L]
    b = [txt(40, 42, t["tit"], TXT, 15, UI, peso="600")]
    b += [caja(40, 80, 230, 64, AZUL), txt(155, 110, t["v"], AZUL, 12.5, UI, "middle", "600"),
          txt(155, 130, "sudo cliente --connect", DIM, 10.5, MONO, "middle")]
    b += [caja(460, 80, 230, 64, ROJO), txt(575, 110, t["p"], ROJO, 12.5, UI, "middle", "600"),
          txt(575, 130, "CA propia + /etc/hosts" if L == "es" else "own CA + /etc/hosts",
              DIM, 10.5, MONO, "middle")]
    b += [caja(880, 80, 230, 64, VERDE), txt(995, 110, t["r"], VERDE, 12.5, UI, "middle", "600")]
    b.append(flecha(270, 112, 455, 112, AZUL))
    b.append(flecha(690, 112, 875, 112, VERDE))

    y = 176
    for ruta, envenenada in t["lista"]:
        col = ROJO if envenenada else DIM
        relleno = "#2a1220" if envenenada else CAJA
        b.append(f'<rect x="40" y="{y}" width="1070" height="38" rx="8" fill="{relleno}" '
                 f'stroke="{col}" stroke-opacity="{.7 if envenenada else .35}"/>')
        b.append(txt(62, y + 25, ruta, TXT if envenenada else DIM, 12.5, MONO,
                     peso="600" if envenenada else "400"))
        b.append(txt(1088, y + 25, (t["mal"] if envenenada else t["ok"]), col, 11.5, UI, "end"))
        y += 46
    b.append(txt(575, y + 24, t["pie"], DIM, 12.5, UI, "middle"))
    return svg(1150, y + 48, "".join(b))


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



# ═══════ 12 · la ventana entre comprobar y escribir (TOCTOU) ═══════
def ventana_carrera(L):
    t = dict(
        es=dict(tit="La misma comprobación, enviada de dos maneras",
                izq="UNA DETRÁS DE OTRA", der="LAS DOS A LA VEZ",
                a="Petición A", b="Petición B",
                lee0="lee 0", lee1="lee 1", esc="escribe 1", no="403 · cupo lleno",
                vent="ventana", tope="tope del plan: 1 dispositivo",
                vizq="El cupo se respeta: B ve lo que A ya escribió",
                vder="Las dos leen 0 y las dos escriben: 2 donde cabía 1",
                pie="El fallo no está en la comprobación, que es correcta. Está en el hueco que deja detrás."),
        en=dict(tit="The same check, sent two different ways",
                izq="ONE AFTER THE OTHER", der="BOTH AT THE SAME TIME",
                a="Request A", b="Request B",
                lee0="reads 0", lee1="reads 1", esc="writes 1", no="403 · quota full",
                vent="window", tope="plan limit: 1 device",
                vizq="The quota holds: B sees what A already wrote",
                vder="Both read 0 and both write: 2 where 1 fit",
                pie="The bug is not the check, which is correct. It is the gap the check leaves behind."))[L]

    def panel(px, titulo, carrera):
        o = [caja(px, 74, 410, 232, BORDE, "#0b1220", 12, ".5"),
             txt(px + 205, 98, titulo, AMBAR if carrera else DIM, 11.5, MONO, "middle", "600")]
        ya, yb = 142, 196
        if carrera:   # el hueco de A abarca la lectura de B
            o.insert(1, f'<rect x="{px + 118}" y="120" width="140" height="100" rx="8" '
                        f'fill="{AMBAR}" fill-opacity=".10" stroke="{AMBAR}" stroke-opacity=".45" '
                        f'stroke-dasharray="4 3"/>')
            o.append(txt(px + 188, 136, t["vent"], AMBAR, 10.5, MONO, "middle"))
        for y, etiqueta in ((ya, t["a"]), (yb, t["b"])):
            o.append(txt(px + 16, y + 4, etiqueta, DIM, 11.5, MONO))
            o.append(f'<path d="M{px + 100} {y} L{px + 392} {y}" stroke="{BORDE}" stroke-width="1.5"/>')

        def evento(x, y, s, color):
            an = 8 + len(s) * 6.6
            return [caja(x, y - 13, an, 26, color, "#141f36", 7, ".85"),
                    txt(x + an / 2, y + 4, s, color, 11, MONO, "middle", "600")]

        if carrera:
            o += evento(px + 118, ya, t["lee0"], AZUL) + evento(px + 252, ya, t["esc"], VERDE)
            o += evento(px + 150, yb, t["lee0"], AZUL) + evento(px + 290, yb, t["esc"], VERDE)
        else:
            o += evento(px + 118, ya, t["lee0"], AZUL) + evento(px + 206, ya, t["esc"], VERDE)
            o += evento(px + 252, yb, t["lee1"], AZUL) + evento(px + 318, yb, t["no"], ROJO)
        col = ROJO if carrera else VERDE
        o.append(caja(px + 16, 250, 378, 42, col, "#141f36", 9, ".5"))
        for i, linea in enumerate(_envolver(t["vder"] if carrera else t["vizq"], 50)[:2]):
            o.append(txt(px + 205, 268 + i * 15, linea, col, 11.5, UI, "middle"))
        return "".join(o)

    c = [txt(470, 42, t["tit"], TXT, 16, UI, "middle", "650"),
         panel(30, t["izq"], False), panel(500, t["der"], True),
         txt(470, 336, t["tope"], DIM, 11.5, MONO, "middle"),
         txt(470, 362, t["pie"], DIM, 12.5, UI, "middle")]
    return svg(940, 384, "".join(c))


# ═══════ 13 · por que "a la vez" no es "muy rapido" ═══════
def ultimo_byte(L):
    t = dict(
        es=dict(tit="«A la vez» no es «muy rápido»",
                a="Enviadas seguidas", b="Sincronizadas por el último byte",
                pa="Cada una sale cuando termina la anterior. Entre la primera y la última hay"
                   " milisegundos de red: tiempo de sobra para que el contador ya esté subido.",
                pb="Se abren N conexiones y se manda la petición entera MENOS su último byte. El"
                   " servidor no puede procesar nada todavía. Después se sueltan los N bytes finales"
                   " juntos, y la latencia ya está pagada.",
                con="conexión", casi="petición completa menos 1 byte", byte="1 byte",
                llegan="llegan separadas", juntas="llegan dentro de la misma ventana",
                pie="La latencia se paga ANTES de que empiece la carrera, no durante."),
        en=dict(tit="\u201cAt the same time\u201d is not \u201cvery fast\u201d",
                a="Sent back to back", b="Last-byte synchronised",
                pa="Each one leaves when the previous finishes. Between the first and the last there"
                   " are milliseconds of network: plenty of time for the counter to already be up.",
                pb="Open N connections and send the whole request MINUS its final byte. The server"
                   " cannot process anything yet. Then release the N final bytes together, with the"
                   " latency already paid.",
                con="connection", casi="whole request minus 1 byte", byte="1 byte",
                llegan="arrive spread out", juntas="arrive inside the same window",
                pie="The latency is paid BEFORE the race starts, not during it."))[L]

    c = [txt(470, 40, t["tit"], TXT, 16, UI, "middle", "650")]

    # ── arriba: una detrás de otra ──
    c += [caja(30, 62, 880, 122, BORDE, "#0b1220", 12, ".5"),
          txt(52, 88, t["a"], ROJO, 12, MONO, "start", "600")]
    for i in range(3):
        y = 112 + i * 24
        x = 150 + i * 150
        c += [txt(52, y + 4, f'{t["con"]} {i + 1}', DIM, 10.5, MONO),
              f'<rect x="{x}" y="{y - 8}" width="128" height="16" rx="4" fill="{AZUL}" fill-opacity=".30"/>',
              f'<rect x="{x + 128}" y="{y - 8}" width="7" height="16" rx="2" fill="{ROJO}"/>']
    c.append(txt(888, 172, t["llegan"], ROJO, 11, MONO, "end"))
    for i, linea in enumerate(_envolver(t["pa"], 100)[:2]):
        c.append(txt(470, 208 + i * 17, linea, DIM, 12, UI, "middle"))

    # ── abajo: sincronizadas ──
    c += [caja(30, 254, 880, 138, BORDE, "#0b1220", 12, ".5"),
          txt(52, 280, t["b"], VERDE, 12, MONO, "start", "600")]
    for i in range(3):
        y = 304 + i * 24
        c += [txt(52, y + 4, f'{t["con"]} {i + 1}', DIM, 10.5, MONO),
              f'<rect x="150" y="{y - 8}" width="520" height="16" rx="4" fill="{AZUL}" fill-opacity=".30"/>',
              f'<rect x="676" y="{y - 8}" width="7" height="16" rx="2" fill="{VERDE}"/>']
    c += [txt(410, 296, t["casi"], DIM, 10.5, MONO, "middle"),
          f'<path d="M694 290 L694 362" stroke="{VERDE}" stroke-width="1.6" stroke-dasharray="4 3"/>',
          txt(704, 296, t["byte"], VERDE, 10.5, MONO),
          txt(888, 380, t["juntas"], VERDE, 11, MONO, "end")]
    for i, linea in enumerate(_envolver(t["pb"], 100)[:2]):
        c.append(txt(470, 416 + i * 17, linea, DIM, 12, UI, "middle"))

    c.append(txt(470, 468, t["pie"], TXT, 12.5, UI, "middle", "500"))
    return svg(940, 488, "".join(c))


DIAGRAMAS = [
    ("rce-cli-shell-true", "04-shell-true.svg", shell_true),
    ("open-redirect-sso", "02-anatomia-url.svg", anatomia_url),
    ("clave-aes-bundle-js", "02-clave-en-el-navegador.svg", clave_bundle),
    ("rce-agente-ia", "02-chatbot-vs-agente.svg", agente_ia),
    ("ato-codigo-emparejamiento", "01-cadena.svg", cadena_pin),
    ("escalada-symlink", "01-enlace-simbolico.svg", symlink),
    ("inyeccion-nombre-carpeta", "02-comillas.svg", comillas),
    ("ato-codigo-emparejamiento", "02-consentimiento.svg", pantalla_consentimiento),
    ("rce-agente-ia", "03-canario.svg", canario),
    ("open-redirect-sso", "03-cadena.svg", cadena_sso),
    ("rce-cli-shell-true", "05-mitm.svg", mitm),
    ("race-cupo-dispositivos", "01-ventana-carrera.svg", ventana_carrera),
    ("race-cupo-dispositivos", "02-ultimo-byte.svg", ultimo_byte),
]

if __name__ == "__main__":
    print("Diagramas generados:")
    for carpeta, nombre, fn in DIAGRAMAS:
        guardar(carpeta, nombre, fn("es"))
        guardar(carpeta, nombre.replace(".svg", "-en.svg"), fn("en"))
