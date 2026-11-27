#!/usr/bin/env python3
"""Reparte una linea de terminal muy larga en varias, para que se pueda leer.

El problema que resuelve: la columna de texto del sitio mide 760 px. Una
captura de 1987 px de ancho se muestra al 38 % y el texto queda en tres
pixeles. Da igual lo bien censurada que este: no se lee.

La solucion no es encoger, es **envolver**: se corta la linea en trozos del
ancho de la columna y se apilan, que es exactamente lo que haria la misma
terminal con la ventana mas estrecha. Son los mismos pixeles, en el mismo
orden de lectura.

Solo vale para lineas sueltas o bloques donde cada linea se trata aparte. Un
bloque de varias lineas NO se puede cortar en vertical de una vez: saldrian
primero las mitades izquierdas de todas y luego las derechas.
"""
import subprocess
import tempfile
from pathlib import Path

ANCHO_COLUMNA = 760          # el ancho util del articulo, en pixeles


def envolver(origen, destino, lineas, ancho=ANCHO_COLUMNA, margen=10,
             fondo="#ffffff", sangria=14):
    """`lineas` es una lista de (y, alto): cada una se envuelve por separado.

    Devuelve una imagen apilada cuyo ancho no pasa de `ancho`, asi que en la
    pagina se ve a tamano real y el texto queda nitido.
    """
    origen, destino = Path(origen), Path(destino)
    w = int(subprocess.run(["identify", "-format", "%w", str(origen)],
                           capture_output=True, text=True, check=True).stdout)
    util = ancho - sangria
    piezas = []
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        n = 0
        for y, alto in lineas:
            x = 0
            while x < w:
                corte = min(util, w - x)
                p = t / f"{n:03d}.png"
                subprocess.run(["convert", str(origen),
                                "-crop", f"{corte}x{alto}+{x}+{y}", "+repage",
                                "-background", fondo, "-gravity", "west",
                                "-extent", f"{ancho}x{alto}", str(p)], check=True)
                piezas.append(str(p))
                x += corte
                n += 1
        subprocess.run(["convert", *piezas, "-append",
                        "-bordercolor", fondo, "-border", str(margen),
                        "-strip", str(destino)], check=True)
    dim = subprocess.run(["identify", "-format", "%wx%h", str(destino)],
                         capture_output=True, text=True, check=True).stdout
    ancho_f, alto_f = (int(v) for v in dim.split("x"))
    print(f"  {destino.name:34} {dim:>10}  relación {ancho_f / alto_f:.1f}:1")
    return destino
