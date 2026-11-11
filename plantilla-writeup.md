---
# ═══════════════════════════════════════════════════════════════
#  PLANTILLA DE WRITEUP
#  Copia este fichero a _posts/AAAA-MM-DD-titulo-en-guiones.md
#  (o más fácil:  ./nuevo-writeup.sh "Título del writeup")
# ═══════════════════════════════════════════════════════════════

title:       "Título descriptivo: qué permite hacer el fallo"
summary:     "Dos o tres líneas. Es lo que lee la empresa en la ficha y en la cabecera del artículo. Di el impacto, no la técnica."
date:        2026-01-01 10:00:00 +0100

severity:    medium          # critical | high | medium | low | info
cvss:        "6.5"
cvss_vector: "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N"
cwe:         "CWE-639"
vuln_class:  "Control de acceso"   # Control de acceso | Lógica de negocio | Autenticación | Inyección | SSRF | XSS | Condición de carrera | Móvil …
target_type: "API REST"
platform:    "Programa privado"    # HackerOne | YesWeHack | Intigriti | Bugcrowd | VDP | Programa privado
status:      "Corregido"           # Corregido | Triado | Mitigado | Duplicado
fixed:       "9 días"              # tiempo hasta el fix (opcional)
reward:      ""                    # "Recompensado" o el importe; vacío = no se muestra
tags:        [idor, api, autorizacion]

takeaways:
  - "La lección transferible, no el detalle del objetivo."
  - "Qué buscar la próxima vez para encontrar esto mismo más rápido."

# disclosure: "Texto propio si quieres sobrescribir el aviso legal del final."
---

Párrafo de entrada: qué es el objetivo (sin nombrarlo si no tienes permiso), qué encontraste
y cómo acabó el proceso de divulgación.

## La señal

Qué te hizo mirar ahí. Cita la evidencia: una línea del bundle, una cabecera, un
comportamiento raro.

```javascript
// código o respuesta que contiene la señal
```

> **Hipótesis declarada antes de probar:** …
>
> *Lo que la confirma:* … *Lo que la mata:* …

## Preparación del entorno de prueba

Cuentas canario propias, datos sembrados por ti. Nunca datos de usuarios reales.

## Explotación

```http
GET /ruta/vulnerable HTTP/2
Host: objetivo.tld
```

```http
HTTP/2 200 OK

{ "dato": "sensible" }
```

<figure>
  <img src="{{ '/assets/img/writeups/CARPETA/01-nombre.png' | relative_url }}"
       alt="Describe la imagen para quien no la ve">
  <figcaption>Pie de imagen: qué hay que mirar en ella.</figcaption>
</figure>

<div class="impact" markdown="1">
**Impacto.** En términos de negocio: qué datos, de cuántos usuarios y qué puede hacer un
atacante con ellos.
</div>

## Control negativo

La misma petición **sin** la condición de ataque, y su respuesta. Sin esto no hay reporte.

```http
HTTP/2 403 Forbidden
```

Qué explicaciones alternativas descarta.

## Causa raíz

La suposición del desarrollador que lo hizo posible.

## Remediación

1. Arreglo principal.
2. Defensa en profundidad.
3. Detección.

## Cronología

| Fecha | Hito |
|---|---|
| 2026-01-01 | Reporte enviado |
| 2026-01-02 | Acuse de recibo |
| 2026-01-10 | Corregido y verificado |
