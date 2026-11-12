---
title:       "Four characters: how a code for pairing your TV hands over the whole account"
summary:     "The code you type to link the app with your television was not bound to anyone. Anyone could request one, talk you into typing it, and walk away with a permanent credential, your email address and the password recovery token."
date:        2026-11-11 20:20:00 +0100
lang:        en
ref:         ato-codigo-emparejamiento
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

<div class="plain" markdown="1">
**In plain words:** it is the same pattern smart TV apps use the world over. You have done
it twenty times. And it works because it assumes **whoever types the code is looking at the
screen showing it** — that is, that both devices are in the same room.

That assumption is what breaks here.
</div>

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

Note the detail that decides everything: **`users_id: null`**.

<div class="plain" markdown="1">
**In plain words:** the server just handed me a code **that belongs to nobody**. It is an
empty slot waiting for someone to fill it. And it is filled by whoever types it.

A code like that should not exist without being bound, from the first second, to the
session of the device that asked for it.
</div>

## Part 2: the screen that does not say what you are authorising

This is the part the report explains most carefully, because it decides whether this is
exploitable in the real world or only in a lab.

When the victim types the code into their app, a confirmation appears. And that
confirmation **said nothing about the device that requested it**: no name, no type, no IP
address, no approximate location.

<div class="plain" markdown="1">
**In plain words:** the victim sees something like *"Authorise this device?"* and a button.
There is no human way to tell their own television apart from a stranger's laptop on the
other side of the country. It is not that the victim is careless: **they are not being given
the information to decide**.

That is why a consent screen that does not describe what you are authorising is not a
protection. It is a formality.
</div>

An attacker only needs a believable excuse for someone to type four characters: tech
support, an "account verification", a prize draw, a colleague. The usual repertoire.

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

<div class="plain" markdown="1">
**In plain words:** the server does not check who collects the prize. It checks that
somebody said "yes" to that code, and then gives it **to whoever asks**. It is a bearer
cheque: no name on it, cashed by whoever holds it.
</div>

And that credential is **permanent**: it identifies "a device on this account" and keeps
working indefinitely.

## Part 4: from device credential to password

With that credential I signed a read of the account profile:

```http
GET /users/me HTTP/2
Host: api.example.tld
Authorization: <signature using the device token and secret>
```

And in the response, along with the victim's email, there was a field that should not have
been there: **the password recovery token**.

<div class="plain" markdown="1">
**In plain words:** the recovery token is that code you get by email when you click "I
forgot my password". It is, to all intents and purposes, **equivalent to the password**:
whoever holds it can change it.

And here it could be **read** from a device credential. A paired device should not be able
to read the mechanism that recovers the account. Those are two completely different levels
of trust.
</div>

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

<div class="plain" markdown="1">
**In plain words:** the last obstacle to changing a password is usually *"type the current
one"*. Here the page filled it in by itself, because it considers that whoever arrives with
the recovery token has already proven who they are. **You never need to know the original
password.**
</div>

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

## The detail that makes it worse: changing the password does not help

This is the part that interested me most when writing the impact section.

When someone suspects their account has been broken into, they do what everyone
recommends: **change the password**. Here that **does not evict the attacker**, because
what they hold is not the password: it is the device credential from step 3. And that
credential **survives the password change**.

<div class="plain" markdown="1">
**In plain words:** the victim does everything any security guide would tell them, believes
the incident is closed, and the attacker is still inside. Worse: with that credential they
can repeat the whole chain and change the password again whenever they feel like it.

The only real cleanup is **deleting the specific device** from the list of linked devices —
something nobody thinks of, because nobody connects "someone got into my account" with "I
have one television too many on the list".
</div>

## The negative control

| What I tried | What happened | What it rules out |
|---|---|---|
| Redeeming the code **before** the victim confirms | Rejected: *user not valid* | That the endpoint gave credentials to anyone: the only thing changing the outcome is the confirmation |
| Requesting the code **without** the app's public key | `401` | That the endpoint was completely open |
| Reading the profile **before** requesting a recovery | The token field comes back **empty** | That the field always carried a value: it appears exactly when the flow is triggered |

<div class="plain" markdown="1">
**In plain words:** the first test is what proves I am not exploiting a server bug but
**the design of the flow**. Everything works as programmed. The problem is that what is
programmed hands over the account.
</div>

## Impact

<div class="impact" markdown="1">
**Impact.** Full account takeover by an attacker who **never had an account on the
service**, with a single action from the victim: typing four characters on a screen that
does not tell them what they are authorising. The attacker obtains the email address, a
permanent device credential and the ability to change the password. The legitimate owner is
locked out of an account whose password they never changed, and the standard advice —
change it again — does not expel the attacker.
</div>

## The fix

1. **Bind the code to whoever requested it.** Redemption must require the same client
   session, or a secret only the originating device holds. The code alone cannot be enough.
2. **Single use and short lived**, and invalidated as soon as the resulting device is
   deleted.
3. **Tell the victim what they are authorising**: client name, device type, approximate
   location and time. Without that, the confirmation is not consent.
4. **Stop returning the recovery token** from any endpoint authenticated only with a device
   credential. Make it single use with a short expiry.
5. **Revoke device credentials when the password changes.** Otherwise the password change
   is theatre.

## How to look for this yourself

Any product that pairs with a TV, a console, a watch or any keyboard-less device uses this
pattern. The questions are always the same:

1. **Can I request a code without an account?** If the response has an empty or null user
   field, keep digging.
2. **What does redeeming it take?** If the code alone suffices, it is a bearer cheque.
3. **What does the victim see when confirming?** If they cannot see device name, IP or
   location, they cannot tell you apart from their own television.
4. **What does the resulting credential return?** Request the profile and read **every**
   field, one by one. Recovery tokens show up in surprising places.
5. **Does it survive a password change?** Change it and repeat the request. If it still
   works, you have one more piece for the report.

Step 4 is usually where the prize is and the one almost nobody does: people check the
response is a `200` and move on. **Read the whole thing.**
