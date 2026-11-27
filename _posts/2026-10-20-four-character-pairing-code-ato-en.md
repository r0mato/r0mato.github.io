---
title:       "Full account takeover with four characters: the pairing code that belonged to nobody"
summary:     "The code you type to link the app with your television was not bound to anyone. Anyone could request one, talk you into typing it, and walk away with a permanent credential, your email address and the password recovery token."
date:        2026-10-20 19:15:00 +0100
lang:        en
ref:         ato-codigo-emparejamiento
image:       /assets/img/og/ato-codigo-emparejamiento-en.png
permalink:   /en/writeups/four-character-pairing-code-ato/

severity:    high
cvss:        "8.8"
cvss_vector: "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:U/C:H/I:H/A:H"
cwe:         "CWE-287 · CWE-640"
vuln_class:  "Authentication"
target_type: "Desktop application API"
platform:    "YesWeHack"
status:      "Reported"
tags:        [ato, pairing, oauth, password-recovery, devices]

takeaways:
  - "A pairing code that is not bound to whoever requested it is a bearer cheque."
  - "If a screen asks you to confirm something, it has to tell you **what**. \"Authorise this device?\" with no name, type or location is not informed consent."
  - "The password recovery token is equivalent to the password. It should not be readable from a device credential."
  - "If changing the password does not evict the attacker, the incident is not closed — it only looks closed."
---

I like this one in particular because there is not a single line of broken code. Everything
works exactly as programmed. What is wrong is **the design**: a chain of individually
reasonable decisions that, lined up, hand over the account.

And because the only action required from the victim is **typing four characters** on a
screen the application itself tells them to use.

<div class="warn" markdown="1">
**Everything is anonymised.** Published with the program's permission and without
identifying the product: company, domains and field names have been changed. The mechanism
is exact.
</div>

## The legitimate flow, the one everybody uses

Some applications also run on a television. Since typing a password with a remote control
is torture, nearly all of them use the same pattern:

1. The TV shows a **short code**: four characters.
2. You open the app on your phone, where you are already signed in.
3. You type the code.
4. The TV is linked to your account.

It is the same pattern smart TV apps use the world over. You have done
it twenty times. And it works because it assumes **whoever types the code is looking at the
screen showing it** — that is, that both devices are in the same room.

That assumption is what breaks here.

## Part 1: requesting a code without an account

The first thing I tried was asking the API for one of those codes directly, with no session
and no account. All you need is the application's public key — which, being public, ships
inside the installer and anyone can read it.

```http
GET /v2/devices/pin HTTP/2
Host: api.example.tld
x-app-key: <client public key, extracted from the installer>
```

```json
{ "users_id": null, "pin": "7MTU" }
```

<figure>
  <img src="{{ '/assets/img/writeups/ato-codigo-emparejamiento/01-pin-sin-dueno.png' | relative_url }}"
       alt="Terminal: a curl request carrying only the x-app-key header, with no session, to the device pin endpoint. The response is users_id null and pin 7MTU">
  <figcaption>A request with the app's public key and nothing else. The server issues the code: <code>users_id: null</code>, <code>pin: "7MTU"</code>. The key and the host are covered.</figcaption>
</figure>

Note the detail that decides everything: **`users_id: null`**.

The server just handed me a code **that belongs to nobody**. It is an
empty slot waiting for someone to fill it. And it is filled by whoever types it.

A code like that should not exist without being bound, from the first second, to the
session of the device that asked for it.

## Part 2: the screen that does not say what you are authorising

This is the part the report explains most carefully, because it decides whether this is
exploitable in the real world or only in a lab.

When the victim types the code into their app, a confirmation appears. And that
confirmation **said nothing about the device that requested it**: no name, no type, no IP
address, no approximate location.

The victim sees something like *"Authorise this device?"* and a button.
There is no human way to tell their own television apart from a stranger's laptop on the
other side of the country. It is not that the victim is careless: **they are not being given
the information to decide**.

That is why a consent screen that does not describe what you are authorising is not a
protection. It is a formality.

<figure>
  <img src="{{ '/assets/img/writeups/ato-codigo-emparejamiento/02-consentimiento-en.svg' | relative_url }}"
       alt="Comparison between the real confirmation screen, showing only the question and the code, and one that would include client, IP address, location and request time">
  <figcaption>On the left, what they were asked to authorise. On the right, what it takes to actually decide.</figcaption>
</figure>

An attacker only needs a believable excuse for someone to type four characters: tech
support, an "account verification", a prize draw, a colleague. The usual repertoire.

<figure>
  <img src="{{ '/assets/img/writeups/ato-codigo-emparejamiento/02-pin-ya-de-la-victima.png' | relative_url }}"
       alt="Server response for the same 7MTU code: the users_id field is no longer null, it now holds the victim identifier, redacted">
  <figcaption>The same code, <code>7MTU</code>, after the victim types four characters. The empty slot has been filled with them: <code>users_id</code> is no longer <code>null</code>.</figcaption>
</figure>

## Part 3: the redeemed code returns a permanent credential

Before the victim confirmed, I tried to redeem the code. It failed: `"user not valid"`.
That failed attempt matters, and I explain why below.

After the victim confirmed, I repeated **exactly the same request**:

```http
POST /v2/devices/pin/accesstoken HTTP/2
Host: api.example.tld
x-app-key: <public key>

{"pin":"7MTU"}
```

And the server handed over a full device credential — a token and its secret — **with no
authentication header, no cookie and no signature of any kind**.

The server does not check who collects the prize. It checks that
somebody said "yes" to that code, and then gives it **to whoever asks**. It is a bearer
cheque: no name on it, cashed by whoever holds it.

And that credential is **permanent**: it identifies "a device on this account" and keeps
working indefinitely.

<figure>
  <img src="{{ '/assets/img/writeups/ato-codigo-emparejamiento/03-credencial-permanente.png' | relative_url }}"
       alt="Redemption response: an object with token, tokenSecret, creation date and the OAuth consumer, with deviceType android and active 1. Sensitive values are covered">
  <figcaption>What redemption returns: a <code>token</code> and its <code>tokenSecret</code>, with <code>active: 1</code> and no expiry. A complete device credential, handed to whoever asked for the code.</figcaption>
</figure>

## Part 4: from device credential to password

With that credential I signed a read of the account profile:

```http
GET /users/me HTTP/2
Host: api.example.tld
Authorization: <signature using the device token and secret>
```

And in the response, along with the victim's email, there was a field that should not have
been there: **the password recovery token**.

The recovery token is that code you get by email when you click "I
forgot my password". It is, to all intents and purposes, **equivalent to the password**:
whoever holds it can change it.

And here it could be **read** from a device credential. A paired device should not be able
to read the mechanism that recovers the account. Those are two completely different levels
of trust.

I verified it with the control that gives it meaning: **before** requesting a recovery, that
field came back empty. After triggering one from the public form — with only an email
address, no credentials — the same read returned the real token.

From there the chain closes itself:

```http
POST /api/recover/puk          ← redeem the token that was read
→ set-cookie: full session, valid for one year
```

And following that session to the password setup screen, the form arrived with the hidden
"current password" field **already filled in** with the same token.

The last obstacle to changing a password is usually *"type the current
one"*. Here the page filled it in by itself, because it considers that whoever arrives with
the recovery token has already proven who they are. **You never need to know the original
password.**

## The full chain

```
No account of any kind
 → request a code with the client's public key       ← nobody owns it
 → the victim types 4 characters                     ← their only action
 → redeem the code: permanent device credential      ← no authentication
 → read the profile signing with that credential     ← email + recovery token
 → redeem the token: full one-year session
 → change the password without knowing the old one
```

**Six HTTP requests and four characters typed by the victim.**

<figure>
  <img src="{{ '/assets/img/writeups/ato-codigo-emparejamiento/01-cadena-en.svg' | relative_url }}"
       alt="Diagram of the six steps of the chain, from requesting a code with no account to changing the password without knowing the old one">
  <figcaption>Each step is reasonable on its own. Lined up, they hand over the account.</figcaption>
</figure>

## The detail that makes it worse: changing the password does not help

This is the part that interested me most when writing the impact section.

When someone suspects their account has been broken into, they do what everyone
recommends: **change the password**. Here that **does not evict the attacker**, because
what they hold is not the password: it is the device credential from step 3. And that
credential **survives the password change**.

The victim does everything any security guide would tell them, believes
the incident is closed, and the attacker is still inside. Worse: with that credential they
can repeat the whole chain and change the password again whenever they feel like it.

The only real cleanup is **deleting the specific device** from the list of linked devices —
something nobody thinks of, because nobody connects "someone got into my account" with "I
have one television too many on the list".

## Impact

<div class="impact" markdown="1">
**Impact.** Full account takeover by an attacker who **never had an account on the
service**, with a single action from the victim: typing four characters on a screen that
does not tell them what they are authorising. The attacker obtains the email address, a
permanent device credential and the ability to change the password. The legitimate owner is
locked out of an account whose password they never changed, and the standard advice —
change it again — does not expel the attacker.
</div>
