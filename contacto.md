---
layout: page
permalink: /contacto/
title: "Contacto"
eyebrow: "Hablemos"
lede: "Programas de bug bounty, revisiones puntuales de superficie de ataque o una consulta técnica."
description: "Contacto para programas de bug bounty, pruebas de intrusión puntuales y divulgación de vulnerabilidades."
---

La vía más rápida es el correo. Suelo responder en menos de 24 horas.

Si vas a reportarme algo sensible o quieres que cifre la respuesta, dímelo en el primer
mensaje y te paso mi clave pública.

<ul class="contact-list">
  <li>
    <a href="mailto:{{ site.author.email }}">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><rect x="2.5" y="4.5" width="19" height="15" rx="2.5"/><path d="M3 7l9 6 9-6"/></svg>
      {{ site.author.email }}
    </a>
  </li>
  {% if site.author.github %}
  <li>
    <a href="https://github.com/{{ site.author.github }}" rel="me noopener">
      <svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2a10 10 0 0 0-3.16 19.49c.5.1.68-.22.68-.48v-1.7c-2.78.6-3.37-1.34-3.37-1.34-.45-1.16-1.1-1.47-1.1-1.47-.9-.62.07-.6.07-.6 1 .07 1.53 1.03 1.53 1.03.9 1.52 2.34 1.08 2.9.83.1-.65.35-1.08.63-1.33-2.22-.25-4.56-1.11-4.56-4.95 0-1.1.39-2 1.03-2.7-.1-.26-.45-1.28.1-2.65 0 0 .84-.27 2.75 1.02a9.6 9.6 0 0 1 5 0c1.9-1.3 2.74-1.02 2.74-1.02.55 1.37.2 2.39.1 2.65.64.7 1.03 1.6 1.03 2.7 0 3.85-2.35 4.7-4.58 4.94.36.31.68.92.68 1.86v2.75c0 .27.18.58.69.48A10 10 0 0 0 12 2z"/></svg>
      github.com/{{ site.author.github }}
    </a>
  </li>
  {% endif %}
  {% if site.author.linkedin %}
  <li>
    <a href="https://www.linkedin.com/in/{{ site.author.linkedin }}" rel="me noopener">
      <svg viewBox="0 0 24 24" fill="currentColor"><path d="M4.98 3.5A2.5 2.5 0 1 0 5 8.5a2.5 2.5 0 0 0-.02-5zM3 9h4v12H3zM9 9h3.8v1.7h.05A4.2 4.2 0 0 1 16.6 8.7c3.2 0 4.4 2 4.4 5.2V21h-4v-6c0-1.5-.5-2.5-1.9-2.5-1.1 0-1.8.75-2.1 1.5-.1.25-.1.6-.1 1V21H9z"/></svg>
      LinkedIn
    </a>
  </li>
  {% endif %}
  {% if site.author.twitter %}
  <li>
    <a href="https://x.com/{{ site.author.twitter }}" rel="me noopener">
      <svg viewBox="0 0 24 24" fill="currentColor"><path d="M18.9 2H22l-6.8 7.8L22.8 22h-6.5l-5-6.6L5.5 22H2.4l7.2-8.2L1.6 2h6.6l4.7 6.2zM17.3 20h1.8L7.2 3.8H5.3z"/></svg>
      X / Twitter
    </a>
  </li>
  {% endif %}
  {% if site.author.hackerone %}
  <li><a href="https://hackerone.com/{{ site.author.hackerone }}" rel="me noopener">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 2l8 4v6c0 5-3.5 8.5-8 10-4.5-1.5-8-5-8-10V6z"/></svg>
      HackerOne</a></li>
  {% endif %}
  {% if site.author.yeswehack %}
  <li><a href="https://yeswehack.com/hunters/{{ site.author.yeswehack }}" rel="me noopener">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 2l8 4v6c0 5-3.5 8.5-8 10-4.5-1.5-8-5-8-10V6z"/></svg>
      YesWeHack</a></li>
  {% endif %}
</ul>

## Qué incluir si me escribes como empresa

Para poder darte una respuesta útil en el primer correo:

1. Alcance: dominios, aplicaciones o APIs que quieres cubrir.
2. Tipo de autorización: programa público, privado, VDP o contrato puntual.
3. Si existe un documento de alcance o reglas de intervención, adjúntalo.
4. Ventana temporal y cualquier restricción de ritmo o de horario.

## Divulgación responsable

Si has llegado aquí porque quieres reportarme un fallo en **este mismo sitio**, adelante:
es estático y no procesa datos, pero cualquier cosa que encuentres es bienvenida y la
reconoceré públicamente si quieres.
