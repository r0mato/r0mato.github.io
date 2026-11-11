---
layout: page
permalink: /en/about/
lang: en
alt_url: /sobre-mi/
title: "About"
eyebrow: "Profile"
lede: "Offensive security researcher focused on web applications and APIs."
description: "Who is behind r0mato: profile, background and way of working in bug bounty and offensive security."
image: /assets/img/brand/r0mato-perfil.jpg
---

<div class="about-top">
  <img class="about-photo" src="{{ '/assets/img/brand/r0mato-perfil.jpg' | relative_url }}"
       alt="Portrait of r0mato" width="640" height="640">
  <div class="about-intro">
    <p class="about-name">{{ site.author.name }}</p>
    <p class="about-role">{{ site.author.role }}</p>
    <p class="about-where">Spain · Web · API</p>
  </div>
  <img class="about-logo" src="{{ '/assets/img/brand/r0mato-logo.jpg' | relative_url }}"
       alt="r0mato logo: a frog dressed as a general" width="300" height="300">
</div>

## Who I am

My name is Curro and I go by **r0mato**. I am an offensive security researcher: my job is
to find, prove and document exploitable flaws in real applications before someone with
different intentions does.

I am studying a **master's degree in cybersecurity** while working on public and private
bug bounty programs. What defines me is not report volume — it is the **validity rate**.
Every case I submit carries a reproducible proof of concept and its documented negative
control, because a report the receiving team cannot reproduce in two minutes is worth
nothing, to them or to me.

## How I got here

I started like almost everyone: breaking things out of curiosity and reading other people's
writeups until I understood *why* they worked, not just which payload was used. That jump —
from copying a payload to understanding the wrong assumption that makes it possible — is
what separates running tools from doing research.

Over time I built my own method, fairly obsessive about false positives: passive
reconnaissance before touching anything, a hypothesis written down before each test,
**one variable per shot**, and a mandatory negative control that repeats the request
without the attack condition. If the behaviour is identical, there was no vulnerability —
there was a coincidence. That rule has killed many of my findings, and that is exactly why
the ones that survive hold up.

## Where I work

I currently focus on **YesWeHack** and private programs. The numbers are on the home page
and I keep them up to date: it seems more honest than any adjective.

## Areas

- **Web applications** — access control (IDOR, horizontal and vertical escalation),
  business logic, injection, XSS with demonstrated impact, deserialisation.
- **APIs** — REST and GraphQL: object-level authorisation, deltas between API versions,
  undocumented operations, mass assignment, batching abuse.
- **Authentication and session** — OAuth/OIDC, SAML, password recovery, MFA bypass, signed
  tokens (JWT), session management and fixation.
- **Race conditions** — operations that read and write state: balances, coupons, quotas,
  invitations.

## Tooling

Burp Suite as the HTTP engine, static analysis of JavaScript bundles and source maps, and
my own utilities for reconnaissance, CVE version correlation and single-packet race
condition measurement.

## About the frog

The amphibious general up there has been my logo for years, and plenty of people recognise
it before they recognise the handle. There is no deeper story: it made me laugh, it stuck,
and now it is part of the brand.

## Ethics and disclosure

I work exclusively within authorised scopes and under coordinated disclosure. Nothing is
published on this site before the issue is fixed and without the program's permission;
domains, identifiers and sensitive data are anonymised or replaced with my own lab values,
and I never use real user data as evidence.

If you represent a company and want me to remove or adjust anything published here, write
to me and I will handle it the same day.
