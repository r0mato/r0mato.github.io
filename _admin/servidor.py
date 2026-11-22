#!/usr/bin/env python3
"""
Panel privado de administración del blog.

Corre SOLO en 127.0.0.1, sin exponer nada a internet. Edita los ficheros reales
del repositorio y publica con git. No guarda credenciales: usa tu clave SSH.

No se lanza a mano: usa ../panel.sh
"""
import base64
import html
import json
import os
import re
import secrets
import subprocess
import sys
import threading
import time
import unicodedata
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

RAIZ = Path(__file__).resolve().parent.parent
UI = Path(__file__).resolve().parent / "ui.html"
PUERTO = int(os.environ.get("PANEL_PUERTO", "8099"))
PUERTO_JEKYLL = int(os.environ.get("JEKYLL_PUERTO", "4100"))
TOKEN = os.environ.get("PANEL_TOKEN") or secrets.token_urlsafe(24)

# Identificadores que nunca deben acabar publicados. Se comprueba antes de cada
# publicación; la lista vive aquí para poder ampliarla sin tocar el resto.
PROHIBIDOS = [
    "cyberghost", "ezviz", "hikvision", "isrm", "scm-aichat", "zhangzhiwei",
    "7c5cfe68", "privateinternetaccess", "decathlon", "ezviz7", "ezvizlife",
    "hicloudcam", "cyberghostvpn", "dktappmobile", "openvpn",
]

CAMPOS_ESCALARES = [
    "title", "summary", "date", "severity", "cvss", "cvss_vector", "cwe",
    "vuln_class", "target_type", "platform", "status", "reward", "fixed",
    "lang", "ref", "permalink",
]


# ─────────────────────────── utilidades de ficheros ───────────────────────────

def correr(args, cwd=RAIZ, timeout=300):
    p = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def slug(texto):
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    t = re.sub(r"[^a-zA-Z0-9]+", "-", t).strip("-").lower()
    return t[:70] or "sin-titulo"


def partir(texto):
    """Separa front matter y cuerpo conservando el front matter tal cual."""
    if not texto.startswith("---"):
        return "", texto
    fin = texto.find("\n---", 3)
    if fin == -1:
        return "", texto
    salto = texto.find("\n", fin + 1)
    return texto[: salto + 1], texto[salto + 1 :]


def desescapar(v):
    """Valor YAML tal cual está en el fichero -> texto real."""
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        cuerpo = v[1:-1]
        if v[0] == '"':
            return cuerpo.replace('\\"', '"').replace("\\\\", "\\")
        return cuerpo.replace("''", "'")
    return v


def escapar(v, comillas):
    """Texto real -> valor YAML listo para escribir, con las comillas dadas."""
    if comillas == '"':
        return '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if comillas == "'":
        return "'" + v.replace("'", "''") + "'"
    return v


def leer_campos(fm):
    """Lee los campos conocidos del front matter sin perder lo demás."""
    datos = {}
    for campo in CAMPOS_ESCALARES:
        m = re.search(rf"^{campo}:\s*(.*?)\s*(?:#.*)?$", fm, re.M)
        if m:
            datos[campo] = desescapar(m.group(1).strip())
    m = re.search(r"^tags:\s*\[(.*?)\]", fm, re.M)
    datos["tags"] = [t.strip() for t in m.group(1).split(",") if t.strip()] if m else []
    m = re.search(r"^takeaways:\s*\n((?:\s+-\s+.*\n)+)", fm, re.M)
    if m:
        datos["takeaways"] = [
            desescapar(re.sub(r"^\s*-\s*", "", l).strip())
            for l in m.group(1).rstrip("\n").split("\n") if l.strip()
        ]
    else:
        datos["takeaways"] = []
    return datos


def escribir_campos(fm, datos):
    """Reescribe solo los campos tocados. Comentarios y orden se conservan."""
    for campo in CAMPOS_ESCALARES:
        if campo not in datos:
            continue
        valor = str(datos[campo])
        # Se conserva el sangrado, el entrecomillado y el comentario originales:
        # guardar sin cambiar nada tiene que dejar el fichero idéntico byte a byte.
        m = re.search(rf"^({campo}:[ \t]*)(.*?)([ \t]*#.*)?$", fm, re.M)
        if not m:
            if valor:
                fm = fm.rstrip("\n")[:-3].rstrip("\n") + f'\n{campo}:{" " * max(1, 13 - len(campo) - 1)}"{valor}"\n---\n'
            continue
        prefijo, antiguo, comentario = m.group(1), m.group(2).strip(), m.group(3) or ""
        comillas = antiguo[0] if len(antiguo) >= 2 and antiguo[0] == antiguo[-1] and antiguo[0] in "\"'" else ""
        if not comillas and re.search(r'^[\[{>|&*!%@`-]|: |#|["\']', valor):
            comillas = '"'          # necesita comillas aunque antes no las llevara
        nuevo = prefijo + escapar(valor, comillas) + comentario
        fm = fm[: m.start()] + nuevo + fm[m.end() :]

    if "tags" in datos:
        linea = "tags:        [" + ", ".join(datos["tags"]) + "]"
        if re.search(r"^tags:\s*\[", fm, re.M):
            fm = re.sub(r"^tags:\s*\[.*?\]", lambda _m: linea, fm, count=1, flags=re.M)
        else:
            fm = fm.rstrip("\n")[:-3].rstrip("\n") + "\n" + linea + "\n---\n"

    if "takeaways" in datos:
        bloque = "takeaways:\n" + "".join(
            "  - " + escapar(t, '"') + "\n" for t in datos["takeaways"]
        )
        if re.search(r"^takeaways:\s*\n(?:\s+-\s+.*\n)+", fm, re.M):
            fm = re.sub(r"^takeaways:\s*\n(?:\s+-\s+.*\n)+", lambda _m: bloque, fm, count=1, flags=re.M)
        elif datos["takeaways"]:
            fm = fm.rstrip("\n")[:-3].rstrip("\n") + "\n\n" + bloque + "---\n"
    return fm


def listar_writeups():
    salida = []
    for carpeta, publicado in (("_posts", True), ("_drafts", False)):
        d = RAIZ / carpeta
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.md"), reverse=True):
            fm, _ = partir(f.read_text(encoding="utf-8"))
            c = leer_campos(fm)
            salida.append({
                "fichero": f"{carpeta}/{f.name}",
                "titulo": c.get("title", f.stem),
                "idioma": c.get("lang", "es"),
                "severidad": c.get("severity", ""),
                "fecha": c.get("date", "")[:10],
                "ref": c.get("ref", ""),
                "publicado": publicado,
                "url": url_publica(carpeta, f.name, c),
            })
    return salida


def url_publica(carpeta, nombre, campos):
    if campos.get("permalink"):
        return campos["permalink"]
    base = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", nombre[:-3])
    return f"/writeups/{base}/"


def ruta_segura(rel):
    """Impide salirse del repositorio."""
    p = (RAIZ / rel).resolve()
    if not str(p).startswith(str(RAIZ) + os.sep):
        raise ValueError("ruta fuera del repositorio")
    return p


# ─────────────────────────────── acciones ────────────────────────────────────

def accion_publicar(mensaje):
    pasos = []

    def paso(nombre, args, fatal=True):
        cod, out = correr(args)
        pasos.append({"paso": nombre, "ok": cod == 0, "salida": out.strip()[-4000:]})
        return cod == 0 or not fatal

    # 1 · ningún identificador real en lo que se publica
    encontrados = []
    for t in PROHIBIDOS:
        cod, out = correr(["grep", "-ril", t, "_posts"])
        if cod == 0 and out.strip():
            encontrados.append(f"{t}: {out.strip().splitlines()[0]}")
    pasos.append({
        "paso": "Sin identificadores reales",
        "ok": not encontrados,
        "salida": "\n".join(encontrados) or "limpio",
    })
    if encontrados:
        return {"ok": False, "pasos": pasos}

    # 2 · compila y no hay enlaces ni imágenes rotas
    gem = os.environ.get("GEM_BIN", str(Path.home() / ".local/share/gem/ruby/3.3.0/bin"))
    os.environ["PATH"] = gem + os.pathsep + os.environ.get("PATH", "")
    # Se compila en un destino aparte: `_site` lo está usando la vista previa en vivo
    # y dos compilaciones a la vez se pisan.
    import tempfile
    with tempfile.TemporaryDirectory(prefix="panel-build-") as tmp:
        if not paso("Compila el sitio", [
            "bundle", "exec", "jekyll", "build", "--quiet", "--destination", tmp,
        ]):
            return {"ok": False, "pasos": pasos}
        if not paso("Enlaces e imágenes", [
            "bundle", "exec", "htmlproofer", tmp,
            "--disable-external", "--allow-hash-href", "--no-enforce-https",
        ]):
            return {"ok": False, "pasos": pasos}

    # 3 · git
    paso("git add", ["git", "add", "-A"])
    cod, out = correr(["git", "diff", "--cached", "--stat"])
    if not out.strip():
        pasos.append({"paso": "Nada que publicar", "ok": True, "salida": "sin cambios"})
        return {"ok": True, "pasos": pasos}
    if not paso("git commit", ["git", "commit", "-q", "-m", mensaje or "actualización desde el panel"]):
        return {"ok": False, "pasos": pasos}
    if not paso("git push", ["git", "push", "-q", "origin", "main"]):
        return {"ok": False, "pasos": pasos}
    return {"ok": True, "pasos": pasos}


def estado_git():
    _, pendientes = correr(["git", "status", "--short"])
    _, ultimo = correr(["git", "log", "-1", "--format=%h %s (%cr)"])
    return {
        "pendientes": [l for l in pendientes.strip().split("\n") if l.strip()],
        "ultimo_commit": ultimo.strip(),
    }


# ──────────────────────────────── servidor ───────────────────────────────────

class Panel(BaseHTTPRequestHandler):
    server_version = "PanelBlog/1.0"

    def log_message(self, *a):
        pass

    # --- seguridad: solo localhost y solo con el token de esta sesión ---
    def _autorizado(self, q):
        host = (self.headers.get("Host") or "").split(":")[0]
        if host not in ("127.0.0.1", "localhost"):
            return False
        origen = self.headers.get("Origin")
        if origen and urlparse(origen).hostname not in ("127.0.0.1", "localhost"):
            return False
        dado = (q.get("t", [None])[0]) or self.headers.get("X-Panel-Token")
        return secrets.compare_digest(dado or "", TOKEN)

    def _json(self, datos, codigo=200):
        cuerpo = json.dumps(datos, ensure_ascii=False).encode()
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def _leer_cuerpo(self):
        n = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(n) if n else b""

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if not self._autorizado(q):
            self.send_error(403, "panel privado")
            return

        if u.path == "/":
            cuerpo = UI.read_text(encoding="utf-8")
            cuerpo = cuerpo.replace("__TOKEN__", TOKEN).replace("__JEKYLL__", str(PUERTO_JEKYLL))
            cuerpo = cuerpo.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)
            return

        if u.path == "/api/writeups":
            return self._json({"writeups": listar_writeups()})

        if u.path == "/api/writeup":
            f = ruta_segura(q["fichero"][0])
            fm, cuerpo = partir(f.read_text(encoding="utf-8"))
            return self._json({"campos": leer_campos(fm), "cuerpo": cuerpo, "crudo_fm": fm})

        if u.path == "/api/fichero":
            f = ruta_segura(q["ruta"][0])
            return self._json({"texto": f.read_text(encoding="utf-8")})

        if u.path == "/api/config":
            texto = (RAIZ / "_config.yml").read_text(encoding="utf-8")
            datos = {}
            for k in ("name", "full_name", "role", "location", "email", "yeswehack", "linkedin"):
                m = re.search(rf"^\s+{k}:\s*\"?(.*?)\"?\s*(?:#.*)?$", texto, re.M)
                datos[k] = m.group(1).strip() if m else ""
            datos["stats"] = re.findall(
                r'-\s+value:\s*"(.*?)"\s*\n\s+label_es:\s*"(.*?)"\s*\n\s+label_en:\s*"(.*?)"', texto)
            m = re.search(r"^headline:\s*\"(.*?)\"", (RAIZ / "index.html").read_text(encoding="utf-8"), re.M)
            return self._json({"config": datos})

        if u.path == "/api/estado":
            return self._json(estado_git())

        self.send_error(404)

    def do_POST(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if not self._autorizado(q):
            self.send_error(403, "panel privado")
            return
        crudo = self._leer_cuerpo()

        try:
            if u.path == "/api/guardar":
                d = json.loads(crudo)
                f = ruta_segura(d["fichero"])
                fm, _ = partir(f.read_text(encoding="utf-8"))
                fm = escribir_campos(fm, d.get("campos", {}))
                f.write_text(fm + d["cuerpo"], encoding="utf-8")
                return self._json({"ok": True})

            if u.path == "/api/fichero":
                d = json.loads(crudo)
                ruta_segura(d["ruta"]).write_text(d["texto"], encoding="utf-8")
                return self._json({"ok": True})

            if u.path == "/api/nuevo":
                d = json.loads(crudo)
                return self._json(crear_writeup(d["titulo"], d.get("idioma", "es"), d.get("borrador", True)))

            if u.path == "/api/subir":
                d = json.loads(crudo)
                carpeta = RAIZ / "assets/img/writeups" / slug(d["carpeta"])
                carpeta.mkdir(parents=True, exist_ok=True)
                nombre = re.sub(r"[^A-Za-z0-9._-]", "-", d["nombre"])
                destino = ruta_segura(carpeta.relative_to(RAIZ) / nombre)
                destino.write_bytes(base64.b64decode(d["datos"].split(",", 1)[-1]))
                rel = destino.relative_to(RAIZ)
                return self._json({"ok": True, "ruta": f"/{rel}", "nombre": nombre})

            if u.path == "/api/config":
                d = json.loads(crudo)
                return self._json(guardar_config(d))

            if u.path == "/api/publicar":
                d = json.loads(crudo)
                return self._json(accion_publicar(d.get("mensaje", "")))

            if u.path == "/api/estado-post":
                d = json.loads(crudo)
                origen = ruta_segura(d["fichero"])
                nombre = origen.name
                if d["publicar"]:
                    if not re.match(r"\d{4}-\d{2}-\d{2}-", nombre):
                        nombre = datetime.now().strftime("%Y-%m-%d-") + nombre
                    destino = RAIZ / "_posts" / nombre
                else:
                    destino = RAIZ / "_drafts" / re.sub(r"^\d{4}-\d{2}-\d{2}-", "", nombre)
                correr(["git", "mv", str(origen.relative_to(RAIZ)), str(destino.relative_to(RAIZ))])
                if origen.exists():
                    origen.rename(destino)
                return self._json({"ok": True, "fichero": str(destino.relative_to(RAIZ))})

        except Exception as e:  # noqa: BLE001 — el panel informa, no se cae
            return self._json({"ok": False, "error": f"{type(e).__name__}: {e}"}, 500)

        self.send_error(404)


def crear_writeup(titulo, idioma, borrador):
    s = slug(titulo)
    plantilla = (RAIZ / "plantilla-writeup.md").read_text(encoding="utf-8")
    ahora = datetime.now()
    fecha = ahora.strftime("%Y-%m-%d %H:%M:%S +0100")
    t = plantilla
    t = re.sub(r"^title:.*$", f'title:       "{titulo}"', t, count=1, flags=re.M)
    t = re.sub(r"^date:.*$", f"date:        {fecha}", t, count=1, flags=re.M)
    t = re.sub(r"^lang:.*$", f"lang:        {idioma}", t, count=1, flags=re.M)
    t = re.sub(r"^ref:.*$", f"ref:         {s}", t, count=1, flags=re.M)
    t = t.replace("writeups/CARPETA", f"writeups/{s}")
    t = re.sub(r"^#.*PLANTILLA DE WRITEUP.*$|^#  Copia este fichero.*$|^#  \(o más fácil.*$|^# ═.*$",
               "", t, flags=re.M)
    if idioma == "en":
        t = re.sub(r"^ref:(.*)$", r"ref:\1\npermalink:   /en/writeups/" + s + "/", t, count=1, flags=re.M)
        nombre = f"{s}-en.md"
    else:
        nombre = f"{s}.md"
    carpeta = "_drafts" if borrador else "_posts"
    if carpeta == "_posts":
        nombre = ahora.strftime("%Y-%m-%d-") + nombre
    destino = RAIZ / carpeta / nombre
    if destino.exists():
        return {"ok": False, "error": "ya existe un writeup con ese título"}
    destino.write_text(t, encoding="utf-8")
    (RAIZ / "assets/img/writeups" / s).mkdir(parents=True, exist_ok=True)
    return {"ok": True, "fichero": f"{carpeta}/{nombre}", "carpeta_img": s}


def guardar_config(d):
    p = RAIZ / "_config.yml"
    texto = p.read_text(encoding="utf-8")
    for k, v in (d.get("autor") or {}).items():
        if k not in ("name", "full_name", "role", "location", "email", "yeswehack", "linkedin"):
            continue
        v = str(v).replace('"', '')
        if re.search(rf"^(\s+){k}:\s*.*$", texto, re.M):
            texto = re.sub(rf"^(\s+){k}:\s*.*$", lambda m, k=k, v=v: f'{m.group(1)}{k}: "{v}"',
                           texto, count=1, flags=re.M)
    stats = d.get("stats")
    if stats:
        bloque = "stats:\n"
        for val, es, en in stats:
            bloque += f'  - value: "{val}"\n    label_es: "{es}"\n    label_en: "{en}"\n'
        texto = re.sub(r"^stats:\n(?:\s+-\s+value:.*\n(?:\s+label_\w+:.*\n)+)+",
                       lambda _m: bloque, texto, count=1, flags=re.M)
    p.write_text(texto, encoding="utf-8")
    return {"ok": True}


def main():
    if not UI.exists():
        print("falta _admin/ui.html", file=sys.stderr)
        sys.exit(1)
    srv = ThreadingHTTPServer(("127.0.0.1", PUERTO), Panel)
    url = f"http://127.0.0.1:{PUERTO}/?t={TOKEN}"
    print("\n  Panel privado listo. Ábrelo en el navegador:\n")
    print(f"      {url}\n")
    print("  Solo escucha en 127.0.0.1. Ctrl+C para cerrarlo.\n")
    with open("/tmp/panel-blog-url.txt", "w") as f:
        f.write(url + "\n")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n  Panel cerrado.")


if __name__ == "__main__":
    main()
