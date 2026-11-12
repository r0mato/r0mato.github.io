---
title:       "The key was under the doormat: an AES key in a public JavaScript file was worth every account"
summary:     "A multinational's internal portal signed its tokens with a key anyone could read in a JavaScript file served to the internet. With that key you could mint valid credentials without an account, and the API never checked whose data it was returning. Accepted as critical."
date:        2026-11-11 19:50:00 +0100
lang:        en
ref:         clave-aes-bundle-js
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

<div class="plain" markdown="1">
**In plain words:** when you enter a website, the server sends you the program that runs in
your browser. That program is yours: you can read all of it. If the developers put a
password in there thinking "nobody will see it because it is all squashed together", they
were wrong. It is one `Ctrl+U` away.
</div>

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

<div class="plain" markdown="1">
**In plain words:** the application encrypts a piece of text with that key and sends it to
the server. The server decrypts it, sees the result makes sense and concludes: *"if you knew
how to encrypt this, you are my legitimate application"*. And hands you an entry pass.

The problem is obvious the moment you say it out loud: **if the key is in the file I just
downloaded, I also know how to encrypt it.** The server is not checking who you are. It is
checking you hold a secret it handed to everybody.
</div>

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

{% comment %} PENDIENTE DE CAPTURA — quita esta linea y la de cierre cuando exista el fichero
<figure>
  <img src="{{ '/assets/img/writeups/clave-aes-bundle-js/01-token-sin-cuenta.png' | relative_url }}"
       alt="Burp Repeater: request with no cookie or authorisation header, 200 response with an access_token, and the decoded token showing scope read write">
  <figcaption>No account, no cookie, no password. And the decoded token carries <code>scope: "read write"</code>.</figcaption>
</figure>
{% endcomment %}

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

<div class="plain" markdown="1">
**In plain words:** the token I minted does not say **who I am**. And the API, instead of
deducing it from the token, lets me write it in the request body. It is like an unnamed
train ticket where the inspector asks "and what is your name?" and takes your word for it.

This is called **BOLA** (Broken Object Level Authorization), or IDOR, and it is the number
one flaw in modern APIs. The application checks that you got in, but not that what you are
asking for is yours.
</div>

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

## The negative control

| What I tried | What happened | What it rules out |
|---|---|---|
| Signing with a **different** key of the same length | `401`, token rejected | That the endpoint handed tokens to anyone |
| Request **without** the token header | `401` | That the data was public |
| Valid token, asking for **my own** canary user | `200` with my data | That the response was a generic error that looked like success |
| Valid token, asking for **another** user | `200` with **their** data | Nothing: this is the bug |

<div class="plain" markdown="1">
**In plain words:** with a made-up key, I do not get in. With no token, I do not get in. Ask
for mine, I see mine. Ask for someone else's… I see someone else's. The first three tests
are what make the fourth mean something.
</div>

## The fix

1. **Get the key out of the client.** A secret that travels to the browser is not a secret.
   If something has to be signed, sign it server-side.
2. **Bind the token to an identity.** The server must know who you are from the token, and
   **ignore** any user identifier in the request body.
3. **Authorise every object, not just the entrance.** Before returning a conversation,
   check it belongs to whoever is asking. That check lives on the server, always.
4. **Rotate the leaked key**, because from the moment it was published it is in somebody's
   cache.
5. Add a short expiry and replay protection to the signature. The one in place accepted
   timestamps up to a year in the future: a single signature was good for twelve months.

## How to look for this yourself

```bash
# 1 · every bundle the page loads
# 2 · hunt the VERB, not just the secret
grep -rniE 'encrypt|decrypt|sign|hmac|secret|aes|cryptojs' bundles/

# 3 · and when you find a function, look at WHO calls it and WITH WHAT
```

Searching for `secret` alone fills your screen with noise. Searching for the **crypto
function** takes you straight to the key *and* its use, which is what you need to know
whether it is worth anything.

And then, always, the three questions:

1. What does this key open?
2. Is what it opens bound to an identity?
3. Can I ask for something that is not mine?

If the answers are "a pass", "no" and "yes", you have a critical.
