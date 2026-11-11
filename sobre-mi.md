---
layout: page
permalink: /sobre-mi/
lang: es
alt_url: /en/about/
title: "Sobre mí"
eyebrow: "Perfil"
lede: "Investigador de seguridad ofensiva centrado en aplicaciones web y APIs."
description: "Quién hay detrás de r0mato: perfil, trayectoria y forma de trabajar en bug bounty y seguridad ofensiva."
image: /assets/img/brand/r0mato-perfil.jpg
---

<div class="about-top">
  <img class="about-photo" src="{{ '/assets/img/brand/r0mato-perfil.jpg' | relative_url }}"
       alt="Retrato de r0mato" width="640" height="640">
  <div class="about-intro">
    <p class="about-name">{{ site.author.name }}</p>
    <p class="about-role">{{ site.author.role }}</p>
    <p class="about-where">{{ site.author.location }} · Web · API</p>
  </div>
  <img class="about-logo" src="{{ '/assets/img/brand/r0mato-logo.jpg' | relative_url }}"
       alt="Logo de r0mato: una rana vestida de general" width="300" height="300">
</div>

## Quién soy

Me llamo Curro y firmo como **r0mato**. Soy investigador de seguridad ofensiva: mi trabajo
consiste en encontrar, demostrar y documentar fallos explotables en aplicaciones reales
antes de que lo haga alguien con otras intenciones.

Estoy cursando un **máster en ciberseguridad** y compagino la formación con programas
públicos y privados de bug bounty. Lo que me define no es el volumen de reportes: es la
**tasa de validez**. Cada caso que envío lleva prueba de concepto reproducible y su control
negativo documentado, porque un reporte que el equipo receptor no puede reproducir en dos
minutos no vale nada — ni para ellos ni para mí.

## Cómo llegué aquí

Empecé como casi todo el mundo: rompiendo cosas por curiosidad y leyendo writeups ajenos
hasta entender *por qué* funcionaban, no solo qué payload se había usado. Ese salto —de
copiar un payload a entender la suposición equivocada que lo hace posible— es el que separa
tirar herramientas de hacer investigación.

Con el tiempo construí un método propio y bastante obsesivo con los falsos positivos:
reconocimiento pasivo antes de tocar nada, una hipótesis declarada por escrito antes de
cada prueba, **una sola variable por disparo** y un control negativo obligatorio que repite
la petición sin la condición de ataque. Si el comportamiento es idéntico, no había
vulnerabilidad: había una coincidencia. Esa regla me ha matado muchos hallazgos — y es
exactamente por eso que los que sobreviven son sólidos.

## Dónde estoy

Hoy concentro la actividad en **YesWeHack** y en programas privados. Los números están en la
portada y los mantengo actualizados: me parece más honesto que cualquier adjetivo.

## Áreas de trabajo

- **Aplicaciones web** — control de acceso (IDOR, escalada horizontal y vertical), lógica
  de negocio, inyección, XSS con impacto demostrado, deserialización.
- **APIs** — REST y GraphQL: autorización por objeto, deltas entre versiones de la API,
  operaciones no documentadas, *mass assignment*, abuso de *batching*.
- **Autenticación y sesión** — OAuth/OIDC, SAML, recuperación de contraseña, bypass de MFA,
  tokens firmados (JWT), gestión y fijación de sesión.
- **Condiciones de carrera** — operaciones que leen y escriben estado: saldos, cupones,
  cuotas, invitaciones.

## Herramientas

Burp Suite como motor HTTP, análisis estático de bundles JavaScript y source maps,
y utilidades propias para reconocimiento, correlación de versiones con CVE y medición de
condiciones de carrera con precisión de paquete único.

## Y la rana

El general anfibio que ves ahí arriba es mi logo desde hace años y mucha gente me conoce
antes por él que por el nick. No tiene más historia que esa: me hizo gracia, se quedó, y
ahora es parte de la marca.

## Ética y divulgación

Trabajo exclusivamente dentro de alcances autorizados y bajo divulgación coordinada. Nada
se publica en este sitio sin que el fallo esté corregido y sin el permiso del programa; los
dominios, identificadores y datos sensibles van anonimizados o sustituidos por valores de
laboratorio propios, y nunca uso datos de usuarios reales como prueba.

Si representas a una empresa y quieres que retire o ajuste cualquier contenido publicado
aquí, escríbeme y lo atiendo el mismo día.
