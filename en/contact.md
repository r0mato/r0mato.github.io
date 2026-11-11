---
layout: page
permalink: /en/contact/
lang: en
alt_url: /contacto/
title: "Contact"
eyebrow: "Let's talk"
lede: "Bug bounty programs, one-off attack surface reviews or a technical question."
description: "Contact for bug bounty programs, one-off penetration testing and technical questions."
---

Email is the fastest way. I usually reply within 24 hours.

If you are sending something sensitive and want an encrypted reply, say so in your first
message and I will share my public key.

<ul class="contact-list">
  <li>
    <a href="mailto:{{ site.author.email }}">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><rect x="2.5" y="4.5" width="19" height="15" rx="2.5"/><path d="M3 7l9 6 9-6"/></svg>
      <span>{{ site.author.email }}</span>
    </a>
  </li>
  <li>
    <a href="https://yeswehack.com/hunters/{{ site.author.yeswehack }}" rel="me noopener">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 2l8 4v6c0 5-3.5 8.5-8 10-4.5-1.5-8-5-8-10V6z"/></svg>
      <span>YesWeHack · {{ site.author.yeswehack }}</span>
    </a>
  </li>
  {% if site.author.linkedin != "" %}
  <li>
    <a href="https://www.linkedin.com/in/{{ site.author.linkedin }}" rel="me noopener">
      <svg viewBox="0 0 24 24" fill="currentColor"><path d="M4.98 3.5A2.5 2.5 0 1 0 5 8.5a2.5 2.5 0 0 0-.02-5zM3 9h4v12H3zM9 9h3.8v1.7h.05A4.2 4.2 0 0 1 16.6 8.7c3.2 0 4.4 2 4.4 5.2V21h-4v-6c0-1.5-.5-2.5-1.9-2.5-1.1 0-1.8.75-2.1 1.5-.1.25-.1.6-.1 1V21H9z"/></svg>
      <span>LinkedIn</span>
    </a>
  </li>
  {% endif %}
</ul>
