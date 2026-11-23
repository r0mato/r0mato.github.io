#!/usr/bin/env python3
"""Una tarjeta social por writeup, con su titular y su severidad.

Genera `assets/img/og/<ref>-<idioma>.png` para cada entrada de `_posts/` y
escribe `image:` en su frontmatter para que jekyll-seo-tag la use en vez de la
tarjeta general del sitio.

Lo normal es llamarlo desde `./generar-og-writeups.sh`.
"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
POSTS = RAIZ / "_posts"
DESTINO = RAIZ / "assets/img/og"
LOGO = RAIZ / "assets/img/brand/r0mato-logo.jpg"

F_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
F_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
F_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

# mismos tonos que las insignias del sitio en modo oscuro, para que la tarjeta
# y la pagina se reconozcan como lo mismo
COLOR = {
    "critical": "#fb7185",
    "high": "#fb923c",
    "medium": "#fbbf24",
    "low": "#38bdf8",
}
ETIQUETA = {
    "critical": ("CRÍTICO", "CRITICAL"),
    "high": ("ALTA", "HIGH"),
    "medium": ("MEDIA", "MEDIUM"),
    "low": ("BAJA", "LOW"),
}
PIE = {
    "es": "Writeup  ·  r0mato.github.io",
    "en": "Writeup  ·  r0mato.github.io",
}


def campo(fm: str, clave: str) -> str:
    m = re.search(rf'^{clave}:\s*"?(.*?)"?\s*$', fm, re.M)
    return m[1].strip() if m else ""


def partir(texto: str):
    """Separa frontmatter y cuerpo sin tocar el formato de ninguno."""
    m = re.match(r"^(---\n)(.*?\n)(---\n)(.*)$", texto, re.S)
    if not m:
        raise ValueError("sin frontmatter")
    return m[1], m[2], m[3], m[4]


def tarjeta(destino: Path, titulo: str, sev: str, cvss: str, lang: str) -> None:
    color = COLOR.get(sev, "#94a3b8")
    etiqueta = ETIQUETA.get(sev, ("", ""))[0 if lang == "es" else 1]
    cabecera = f"{etiqueta}  ·  CVSS {cvss}" if cvss else etiqueta

    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        # fondo: azul muy oscuro con un halo arriba a la izquierda. El halo se
        # genera mas grande que el lienzo a proposito: a su tamano justo se le
        # veia el borde cuadrado cruzando la tarjeta
        subprocess.run(["convert", "-size", "1200x630", "xc:#0a1020", str(t / "bg.png")], check=True)
        subprocess.run(["convert", "-size", "2000x2000",
                        "radial-gradient:#1b3a7a-#0a1020", str(t / "glow.png")], check=True)
        subprocess.run(["convert", str(t / "bg.png"), str(t / "glow.png"),
                        "-geometry", "+-620+-900", "-compose", "screen", "-composite",
                        str(t / "base.png")], check=True)

        # el titular manda: se deja que ImageMagick lo ajuste a la caja, porque
        # los titulos van de 40 a 95 caracteres y un cuerpo fijo parte unos y
        # deja a otros perdidos en medio del hueco
        subprocess.run(["convert", "-background", "none", "-fill", "#ffffff",
                        "-font", F_BOLD, "-size", "1010x264", "-gravity", "northwest",
                        f"caption:{titulo}", str(t / "titulo.png")], check=True)

        # centrado vertical en la banda libre: un titular de dos lineas y otro
        # de cuatro tienen que verse igual de asentados
        alto = int(subprocess.run(["identify", "-format", "%h", str(t / "titulo.png")],
                                  capture_output=True, text=True, check=True).stdout)
        arriba = 160 + max(0, (264 - alto) // 2)

        # logo recortado con las mismas esquinas que la tarjeta general
        subprocess.run(["convert", "-size", "132x132", "xc:black", "-fill", "white",
                        "-draw", "roundrectangle 0,0,131,131,18,18", str(t / "mask.png")], check=True)
        subprocess.run(["convert", str(LOGO), "-resize", "132x132^", "-gravity", "center",
                        "-extent", "132x132", str(t / "logo.png")], check=True)
        subprocess.run(["convert", str(t / "logo.png"), str(t / "mask.png"), "-alpha", "off",
                        "-compose", "copyopacity", "-composite", str(t / "logo_r.png")], check=True)

        subprocess.run([
            "convert", str(t / "base.png"),
            # franja de severidad arriba a la izquierda
            "-fill", color, "-draw", "roundrectangle 80,74 86,116,3,3",
            "-font", F_MONO, "-pointsize", "26", "-fill", color,
            "-annotate", "+108+105", cabecera,
            # titular
            str(t / "titulo.png"), "-geometry", f"+80+{arriba}", "-composite",
            # regla y pie
            "-fill", "#22304d", "-draw", "rectangle 80,470 820,472",
            "-font", F_MONO, "-pointsize", "24", "-fill", "#8ea3c4",
            "-annotate", "+80+516", "r0mato",
            "-font", F_REG, "-pointsize", "24", "-fill", "#6a7c99",
            "-annotate", "+80+556", PIE[lang],
            # logo abajo a la derecha, donde no le quita sitio al titular
            str(t / "logo_r.png"), "-geometry", "+988+424", "-composite",
            "-fill", color, "-draw", "rectangle 0,624 1200,630",
            "-strip", str(destino),
        ], check=True)


def main() -> int:
    if not shutil.which("convert"):
        print("Falta ImageMagick:  sudo apt install imagemagick", file=sys.stderr)
        return 1

    DESTINO.mkdir(parents=True, exist_ok=True)
    hechas, vistas = 0, set()

    for post in sorted(POSTS.glob("*.md")):
        texto = post.read_text(encoding="utf-8")
        try:
            abre, fm, cierra, cuerpo = partir(texto)
        except ValueError:
            print(f"  · {post.name}: sin frontmatter, se salta")
            continue

        ref = campo(fm, "ref")
        lang = campo(fm, "lang") or "es"
        titulo = campo(fm, "title").replace('\\"', '"')
        if not (ref and titulo):
            print(f"  · {post.name}: sin ref o sin title, se salta")
            continue

        nombre = f"{ref}-{lang}.png"
        ruta = DESTINO / nombre
        tarjeta(ruta, titulo, campo(fm, "severity"), campo(fm, "cvss"), lang)
        vistas.add(nombre)

        # que seo-tag use esta y no la general
        rel = f"/assets/img/og/{nombre}"
        if re.search(r"^image:", fm, re.M):
            fm_nuevo = re.sub(r"^image:.*$", f"image:       {rel}", fm, count=1, flags=re.M)
        else:  # debajo de ref:, que es donde vive la identidad del writeup
            fm_nuevo = re.sub(r"^(ref:.*\n)", rf"\1image:       {rel}\n", fm, count=1, flags=re.M)
        if fm_nuevo != fm:
            post.write_text(abre + fm_nuevo + cierra + cuerpo, encoding="utf-8")

        hechas += 1
        print(f"  {nombre:52} {ruta.stat().st_size // 1024:>4} KB")

    for viejo in DESTINO.glob("*.png"):     # tarjetas de writeups que ya no existen
        if viejo.name not in vistas:
            viejo.unlink()
            print(f"  (borrada la huerfana {viejo.name})")

    print(f"\n  {hechas} tarjetas en assets/img/og/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
