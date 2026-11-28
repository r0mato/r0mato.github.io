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

There is not one broken line of code here: everything works as written. What is wrong is
the design, and the only thing the victim has to do is type four characters.

The legitimate flow is the one half the world uses: the television shows a short code, you
type it into the phone where you are already signed in, and the television is linked. It
works because it assumes whoever types the code is looking at the screen showing it. That
assumption is what breaks.

## 1 · Request a code with no account

All it takes is the client's public key, which ships inside the installer.

```http
GET /v2/devices/pin HTTP/2
Host: api.example.tld
x-app-key: <client public key, pulled from the installer>
```

```json
{ "users_id": null, "pin": "7MTU" }
```

<figure>
  <img src="{{ '/assets/img/writeups/ato-codigo-emparejamiento/01-pin-sin-dueno.png' | relative_url }}"
       alt="Terminal: a curl request carrying only the x-app-key header, with no session, to the device pin endpoint. The response is users_id null and pin 7MTU">
  <figcaption>A request with the app's public key and nothing else. The server issues the code: <code>users_id: null</code>, <code>pin: "7MTU"</code>. The key and the host are covered.</figcaption>
</figure>

**`users_id: null`**: a code that belongs to nobody, an empty slot waiting for someone to
fill it. Whoever types it fills it.

## 2 · The screen does not say what you are authorising

When the victim types the code a confirmation appears, and it said nothing about the device
that had requested it: no name, no type, no IP, no location. Just "Authorise this device?"
and a button. There is no way to tell your own television from a stranger's laptop. The
victim is not being careless: they are not being given the information to decide.

<figure>
  <img src="{{ '/assets/img/writeups/ato-codigo-emparejamiento/02-consentimiento-en.svg' | relative_url }}"
       alt="Comparison between the real confirmation screen, showing only the question and the code, and one that would include client, IP address, location and request time">
  <figcaption>On the left, what they were asked to authorise. On the right, what it takes to actually decide.</figcaption>
</figure>

<figure>
  <img src="{{ '/assets/img/writeups/ato-codigo-emparejamiento/02-pin-ya-de-la-victima.png' | relative_url }}"
       alt="Server response for the same 7MTU code: the users_id field is no longer null, it now holds the victim identifier, redacted">
  <figcaption>The same code, <code>7MTU</code>, after the victim types four characters. The empty slot has been filled with them: <code>users_id</code> is no longer <code>null</code>.</figcaption>
</figure>

## 3 · Redemption returns a permanent credential

Before the victim confirms, redemption fails with `"user not valid"`. After they confirm,
**exactly the same request**:

```http
POST /v2/devices/pin/accesstoken HTTP/2
Host: api.example.tld
x-app-key: <public key>

{"pin":"7MTU"}
```

And it hands over a token and its secret with no authentication header, no cookie and no
signature. It does not check who collects the prize, only that somebody said yes to that
code.

<figure>
  <img src="{{ '/assets/img/writeups/ato-codigo-emparejamiento/03-credencial-permanente.png' | relative_url }}"
       alt="Redemption response: an object with token, tokenSecret, creation date and the OAuth consumer, with deviceType android and active 1. Sensitive values are covered">
  <figcaption>What redemption returns: a <code>token</code> and its <code>tokenSecret</code>, with <code>active: 1</code> and no expiry. A complete device credential, handed to whoever asked for the code.</figcaption>
</figure>

## 4 · From device credential to password

Signing with it:

```http
GET /users/me HTTP/2
Host: api.example.tld
Authorization: <signed with the device token and secret>
```

Besides the email address, the response carried the **password recovery token**.

<figure>
  <img src="{{ '/assets/img/writeups/ato-codigo-emparejamiento/04-token-de-recuperacion.png' | relative_url }}"
       alt="Profile response read with the device credential: among the fields are user_email, user_name, new_recover_token and temp_recover_token, each with its value covered">
  <figcaption>The profile, read with the device credential. Among the fields sits <code>new_recover_token</code>: the account-recovery mechanism, readable from a paired device. The values are covered; the field names are the finding.</figcaption>
</figure>

That token is equivalent to the password: whoever holds it can change it. A paired device
should not be able to read it; those are two different levels of trust.

I verified it with the control that gives it meaning: before requesting a recovery the
field came back empty; after requesting one from the public form — with just an email
address — the same read returned the real token. And the chain closes itself:

```http
POST /api/recover/puk          ← redeem the token that was read
→ set-cookie: full session, valid for a year
```

Following that session to the change-password screen, the hidden "current password" field
arrived **already filled in** with the same token. You never need to know the original one.

## The chain

```
No account of any kind
 → request a code with the client's public key         ← nobody owns it
 → the victim types 4 characters                       ← their only action
 → redeem the code: permanent device credential        ← no authentication
 → read the profile signing with that credential       ← email + recovery token
 → redeem the token: full one-year session
 → change the password without knowing the old one
```

<figure>
  <img src="{{ '/assets/img/writeups/ato-codigo-emparejamiento/01-cadena-en.svg' | relative_url }}"
       alt="Diagram of the six steps of the chain, from requesting a code with no account to changing the password without knowing the old one">
  <figcaption>Each step is reasonable on its own. Lined up, they hand over the account.</figcaption>
</figure>

Six requests and four characters.

## Changing the password does not expel the attacker

What they hold is not the password, it is the device credential from step 3, and that
survives the change. The victim does what any security guide recommends, believes the
incident is closed, and the attacker can replay the whole chain whenever they like. The only
real cleanup is deleting that device from the list, and nobody thinks to connect "someone
got into my account" with "there is one television too many in here".

## Impact

<div class="impact" markdown="1">
**Impact.** Full account takeover by an attacker who **never had an account on the
service**, with a single action from the victim: typing four characters on a screen that
does not tell them what they are authorising. The attacker obtains the email address, a
permanent device credential and the ability to change the password. The legitimate owner is
locked out of an account whose password they never changed, and the standard advice —
change it again — does not expel the attacker.
</div>
