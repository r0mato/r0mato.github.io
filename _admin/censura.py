#!/usr/bin/env python3
"""Censura de capturas con etiqueta, en vez de un rectangulo negro.

Dos ideas:

1. **Se tapa el VALOR, no la linea.** `Host:` se queda, su valor no. Asi el
   lector ve la forma de la peticion —que va firmada con OAuth, que el cuerpo
   es JSON, que no hay cookie— y solo se pierde lo confidencial.

2. **La banda dice lo que habia.** Un negro liso solo dice "aqui falta algo".
   Una banda que pone `host` o `firma OAuth` informa y ademas parece
   deliberada, no un borron.

Regla que no se negocia: relleno OPACO al 100 %, nunca pixelado ni desenfoque,
que son reversibles. Y la banda se extiende hasta el borde del panel, para que
un valor mas largo de lo que yo calcule no pueda asomar por la derecha.
"""
import subprocess
from pathlib import Path

# tonos del propio sitio, para que la captura no desentone con la pagina
BANDA = "#475569"        # pizarra media: se ve sobre fondo claro y sobre oscuro
BORDE = "#94a3b8"        # borde claro: separa dos bandas seguidas sin abrir hueco
TEXTO = "#f1f5f9"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"


class Censura:
    """Acumula las zonas a tapar de una captura y las dibuja de una vez."""

    def __init__(self, origen: Path, recorte=None):
        self.origen = Path(origen)
        self.recorte = recorte          # (x, y, ancho, alto)
        self.zonas = []                 # (x1, y1, x2, y2, etiqueta)

    def tapar(self, x1, y1, x2, y2, etiqueta=""):
        """Zona rectangular. La etiqueta se escribe dentro si cabe."""
        self.zonas.append((x1, y1, x2, y2, etiqueta))
        return self

    def valor(self, x, y_arriba, y_abajo, hasta, etiqueta=""):
        """El valor de una cabecera: desde x hasta el borde del panel.

        `hasta` es el borde derecho del panel de texto. Llegar hasta ahi evita
        que un valor mas largo de lo calculado asome por detras de la banda.

        La banda cubre la linea ENTERA, sin margen. Se probo dejar 2 px arriba
        y abajo para separar bandas contiguas y se vio, al ampliar, que por ese
        hueco asomaban las puntas de las letras. Dos bandas seguidas se separan
        con el borde, que va dibujado sobre la propia banda y no descubre nada.
        """
        return self.tapar(x, y_arriba, hasta, y_abajo, etiqueta)

    def guardar(self, destino: Path):
        destino = Path(destino)
        destino.parent.mkdir(parents=True, exist_ok=True)
        cmd = ["convert", str(self.origen)]
        if self.recorte:
            x, y, w, h = self.recorte
            cmd += ["-crop", f"{w}x{h}+{x}+{y}", "+repage"]

        for x1, y1, x2, y2, etiqueta in self.zonas:
            alto, ancho = y2 - y1, x2 - x1
            r = min(5, alto // 3)
            cmd += ["-fill", BANDA, "-stroke", BORDE, "-strokewidth", "1",
                    "-draw", f"roundrectangle {x1},{y1} {x2},{y2} {r},{r}",
                    "-stroke", "none"]
            # la etiqueta solo si la banda es lo bastante grande para leerla
            cuerpo = min(12, max(8, alto - 7))
            if etiqueta and alto >= 14 and ancho >= len(etiqueta) * cuerpo * 0.62 + 16:
                cmd += ["-fill", TEXTO, "-font", MONO, "-pointsize", str(cuerpo),
                        "-gravity", "NorthWest",
                        "-annotate", f"+{x1 + 9}+{y1 + (alto - cuerpo) // 2 - 1}", etiqueta]
        cmd += ["-gravity", "NorthWest", "-strip", str(destino)]
        subprocess.run(cmd, check=True)
        dim = subprocess.run(["identify", "-format", "%wx%h", str(destino)],
                             capture_output=True, text=True, check=True).stdout
        print(f"  {destino.name:30} {dim:>10}  {len(self.zonas)} zonas")
        return destino
