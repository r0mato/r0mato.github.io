# Capturas que faltan para este writeup

Guarda cada una **con el nombre exacto** en esta misma carpeta. El artículo ya las
referencia: en cuanto estén, aparecen solas.

| Fichero | Qué tiene que verse | Estado |
|---|---|---|
| `01-pkg-expandido.png` | Terminal tras `pkgutil --expand-full`: el árbol de carpetas del paquete y el `postinstall` dentro de `Scripts/` | ⬜ falta |
| `02-escritura-sin-auth.png` | Burp Repeater: el `POST /v2/feedback` **sin cabecera `Authorization`** a la izquierda y el `200 OK` a la derecha | ⬜ falta |
| `03-cadena.svg` | Diagrama de la cadena | ✅ hecho |

## Opcionales, si las tienes y mejoran el artículo

| Fichero | Qué tiene que verse |
|---|---|
| `04-sink-codigo.png` | El `postinstall` abierto en un editor con la línea del `$(( ))` resaltada |
| `05-poc-ejecutado.png` | La salida del PoC: el paso que imprime `EXECUTED` y el `uid` |
| `06-lectura-verbatim.png` | El `GET` que devuelve el valor byte a byte, con el payload visible en la respuesta |

## ANTES DE SUBIR CUALQUIERA — lista de tachado

El programa autorizó publicar **con la condición de no identificar al producto**. Repasa
cada captura y tapa con rectángulo opaco (nunca pixelado fino, que se puede revertir):

- [ ] El **nombre de la empresa** y del producto, en cualquier sitio: título de ventana,
      ruta de ficheros, nombre del `.pkg`, pestaña del navegador, marcadores.
- [ ] Los **dominios reales**. En el artículo son `feedback.vpn-ejemplo.tld`: que la
      captura no diga otra cosa.
- [ ] El **número de versión** del producto — identifica al fabricante por sí solo.
- [ ] Los nombres reales de los campos si difieren de los del texto (`installCount`,
      `install_id`).
- [ ] Tu `click_id` / identificador canario real.
- [ ] Rutas con tu usuario del sistema, si prefieres no mostrarlo.
- [ ] Cualquier token, cookie o cabecera `Authorization` que haya quedado visible.

Flameshot tiene herramienta de rectángulo relleno: `flameshot gui`.

## Cómo publicarlas cuando estén

```bash
cd ~/r0mato.github.io
bundle exec jekyll serve --port 4100     # compruébalas en local primero
git add -A && git commit -m "writeup: capturas del RCE del instalador" && git push
```

Si una ruta está mal escrita, el despliegue **falla y no publica**, y te lo dice en
Actions con el fichero y la línea.
