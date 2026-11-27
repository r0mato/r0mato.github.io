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

This is the finding I am proudest of and, paradoxically, the easiest to find: it was in
plain sight, in a file the server hands to anyone who opens the page. It is a brutal
reminder that **whatever reaches the browser is public**, even if it is minified and looks
unreadable.

<div class="warn" markdown="1">
**Everything is anonymised.** The program authorised publication on condition the product
is not identifiable. I have changed the company, the domains, the paths, the field names
and, of course, **the real key does not appear**: the ones you see here are examples. The
mechanism is exact.
</div>

## The target

A multinational's **internal procurement portal**, reachable from the internet. The kind of
application where hundreds of employees work: orders, suppliers, invoices, contracts. Among
its features was an internal conversational assistant, and that is where I went.

## Step 1: read the JavaScript, which is free

When you open a website, your browser downloads `.js` files with all the client-side logic.
They are minified — compressed, no spaces, no readable names — but **not encrypted**.
Minifying is not protecting: it is saving bytes.

The first thing I do on any target is download every bundle and search for words that give
secrets away:

```bash
# download the .js files the page loads
grep -oE 'src="[^"]+\.js"' page.html | cut -d'"' -f2 | while read u; do
    curl -s "https://portal.example.tld$u" -o "bundles/$(basename $u)"
done

# and look for what is usually where it should not be
grep -rniE 'secret|api[_-]?key|password|token|private[_-]?key|encrypt|sign' bundles/
```

In one of the files, this showed up:

```javascript
// minified bundle, reformatted for readability
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

An AES-256 key. In a public file. Served to anyone who visits the site.

## Step 2: the right question is not "is there a key?" but "what is it for?"

This is where many people get ahead of themselves. Finding a string that looks like a key
**is not a finding**. There are keys that are public by design: Firebase identifiers,
publishable payment keys, map tokens. Reporting one of those earns you an "informative" and
some embarrassment.

<div class="note" markdown="1">
**The rule I use:** a leaked key is worth nothing on its own. **What is worth something is
what that key opens.** Do not report the secret: report the door.
</div>

So I followed the function. Who calls `encryptUserTime` and what do they do with the
result?

```javascript
// further down, in the same bundle
const signature = encryptUserTime({
    username:  "SRM",
    timestamp: Date.now(),
    nonce:     "random123"
});

fetch("/assistant/auth/v1/app-source/token", {
    method:  "POST",
    headers: { "X-System-Code": "SRM" },
    body:    JSON.stringify({ signature: signature })
});
```

The application encrypts a piece of text with that key and sends it to
the server. The server decrypts it, sees the result makes sense and concludes: *"if you knew
how to encrypt this, you are my legitimate application"*. And hands you an entry pass.

The problem is obvious the moment you say it out loud: **if the key is in the file I just
downloaded, I also know how to encrypt it.** The server is not checking who you are. It is
checking you hold a secret it handed to everybody.

<figure>
  <img src="{{ '/assets/img/writeups/clave-aes-bundle-js/02-clave-en-el-navegador-en.svg' | relative_url }}"
       alt="Diagram: the server sends the JavaScript file with the key inside to both the legitimate browser and the attacker, and both can sign valid requests">
  <figcaption>The same file reaches both. And with it, the same key.</figcaption>
</figure>

## Step 3: minting a pass without an account

I reproduced the signature outside the browser. No user, no password, no cookie:

```python
import json, time, base64, os
from Crypto.Cipher import AES          # the key comes from the public bundle

KEY = bytes.fromhex("a1b2c3d4e5f60718293a4b5c6d7e8f90")   # example
iv  = os.urandom(16)

text = json.dumps({
    "username":  "SRM",
    "timestamp": int(time.time() * 1000),
    "nonce":     "bbtest1234567",
}).encode()

pad = 16 - len(text) % 16
ct  = AES.new(KEY, AES.MODE_CBC, iv).encrypt(text + bytes([pad]) * pad)

signature = base64.b64encode(iv + ct).decode()
```

And with that, straight to the endpoint:

```http
POST /assistant/auth/v1/app-source/token HTTP/2
Host: portal.example.tld
Content-Type: application/json
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

A valid token. With **read and write** permissions.

## Step 4: the second bug, the one that actually hurts

Holding a token is not holding someone's data. Normally that pass would only work for your
own. So I tried asking for **somebody else's**:

```http
POST /assistant/chat/v1/get_conversation HTTP/2
Host: portal.example.tld
X-Authorization: <my minted token>

{"user":"target.employee"}
```

And they arrived. That employee's conversations, by the hundred.

The token I minted does not say **who I am**. And the API, instead of
deducing it from the token, lets me write it in the request body. It is like an unnamed
train ticket where the inspector asks "and what is your name?" and takes your word for it.

This is called **BOLA** (Broken Object Level Authorization), or IDOR, and it is the number
one flaw in modern APIs. The application checks that you got in, but not that what you are
asking for is yours.

Here is the important part for anyone learning: **the finding is not the key**. The key is
the door. What makes this critical is the combination:

| Piece | On its own | Combined |
|---|---|---|
| Key in the bundle | Worrying, but maybe it only signs anonymous requests | Lets you mint passes |
| The token is not bound to a user | Bad, but you need a token | With the minted pass, you enter as whoever you like |
| The API takes the user from the body | Poor design | **You read any employee's data** |

Three decisions that, separately, someone could defend. Together, a critical.

## Step 5: how far to go — and where to stop

There is an ethical decision here, and it is not optional.

I **could** have downloaded hundreds of employees' conversations to fatten the report. **I
did not**, and neither should you:

- To demonstrate the bug it is enough to **show the door opens**, not to empty the house. A
  listing proving access is sufficient.
- I tested write operations against **a conversation of my own**, created by me, with a
  random identifier. Never against anything belonging to a real person.
- The personal data that appeared on screen was not saved, not copied, and is redacted in
  the report.

<div class="note" markdown="1">
**Why this matters more than the bug.** Almost every program's scope explicitly forbids
accessing real user data beyond the strict minimum. Going past that line turns your report
into an incident, and you into the incident. The difference between a researcher and a
problem is exactly this line.
</div>

Along the same path I also found an endpoint that returned, **with no authentication at
all**, the API key of an external paid service. I reported that one redacted, without using
it once: holding the key does not entitle you to open the door.

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
