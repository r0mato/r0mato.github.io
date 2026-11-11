---
layout: page
permalink: /sobre-mi/
title: "Sobre mí"
eyebrow: "Perfil"
lede: "Investigador de seguridad ofensiva centrado en aplicaciones web, APIs y móvil."
description: "Perfil profesional, áreas de trabajo y experiencia en investigación de seguridad ofensiva y bug bounty."
---

Soy **{{ site.author.name }}**, investigador de seguridad ofensiva con base en
{{ site.author.location }}. Mi trabajo consiste en encontrar, demostrar y documentar fallos
explotables en aplicaciones reales antes de que lo haga alguien con otras intenciones.

Cursando un máster en ciberseguridad y activo en programas públicos y privados de bug
bounty. Lo que me diferencia no es el volumen de reportes, sino la **tasa de validez**: cada
caso llega con prueba de concepto reproducible y control negativo documentado.

## Áreas de trabajo

- **Aplicaciones web** — control de acceso (IDOR, escalada horizontal y vertical), lógica
  de negocio, inyección, XSS con impacto demostrado, deserialización.
- **APIs** — REST y GraphQL: autorización por objeto, deltas entre versiones, operaciones
  no documentadas, *mass assignment*, abuso de *batching*.
- **Autenticación y sesión** — OAuth/OIDC, SAML, recuperación de contraseña, bypass de MFA,
  tokens firmados (JWT), gestión y fijación de sesión.
- **Móvil** — Android e iOS: análisis de tráfico en tiempo de ejecución, almacenamiento
  local, *deeplinks* y la API que hay detrás.
- **Condiciones de carrera** — operaciones que leen y escriben estado: saldos, cupones,
  cuotas, invitaciones.

## Herramientas

Burp Suite Professional como motor HTTP, análisis estático de bundles y APKs, instrumentación
dinámica, y utilidades propias para reconocimiento, correlación de versiones con CVE y
medición de condiciones de carrera con precisión de paquete único.

## Ética y divulgación

Trabajo exclusivamente dentro de alcances autorizados y bajo divulgación coordinada. Nada se
publica en este sitio sin que el fallo esté corregido y sin el permiso del programa; los
dominios, identificadores y datos sensibles van anonimizados o sustituidos por valores de
laboratorio propios.

Si representas a una empresa y quieres que retire o ajuste cualquier contenido publicado
aquí, escríbeme y lo atiendo el mismo día.

## Contacto

Para programas, colaboraciones o una revisión puntual de superficie de ataque:
**[{{ site.author.email }}](mailto:{{ site.author.email }})** — o a través de la
[página de contacto]({{ '/contacto/' | relative_url }}).
