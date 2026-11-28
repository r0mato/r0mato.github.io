---
title:       "Race condition on a paid quota: 10 devices activated where only 1 fit"
summary:     "The counter that enforces each plan's device quota was read before it was incremented. Sent one after another, the second activation gets a 403. Released in the same instant, all ten get through: ten real devices, each with a valid credential, on an account that allows one. Reproduced nine times out of nine."
date:        2026-11-05 10:33:00 +0100
lang:        en
ref:         race-cupo-dispositivos
image:       /assets/img/og/race-cupo-dispositivos-en.png
permalink:   /en/writeups/paid-quota-race-condition/

severity:    medium
cvss:        "4.3"
cvss_vector: "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:L/A:N"
cwe:         "CWE-362"
vuln_class:  "Business logic"
target_type: "Subscription service API"
platform:    "YesWeHack"
status:      "Informational"
tags:        [race-condition, toctou, business-logic, concurrency, api, quota]

takeaways:
  - "A correct check and a correct write, separated by a microsecond, are a bug."
  - "\"At the same time\" is not \"very fast\": pay the latency before the race by releasing only the final byte."
  - "The counter after the race is the proof, not the number of 200s you got back."
  - "A quota bug exposes nobody's data, but it breaks exactly what the product sells. The impact is revenue, and it quantifies just the same."
---

There are subscription services whose price **is** a number of devices. The plan is called,
literally, "7 devices". When you install the app on a new machine it calls the enrolment
endpoint:

```http
POST /oauth/access_token
Content-Type: application/json

{"x_auth_machineid":"living-room-laptop","x_auth_machinename":"living-room-laptop",
 "x_auth_mode":"client_auth","x_auth_username":"<email>","x_auth_password":"<password>","reset":0}
```

If there is room, `200` with a token. If not, `403`.

<figure>
  <img src="{{ '/assets/img/writeups/race-cupo-dispositivos/01-control-403.png' | relative_url }}"
       alt="Burp Repeater: a device enrolment sent with the account full gets HTTP/2 403 Forbidden. The headers and the message body are covered with labelled bars">
  <figcaption>With the account full, the enrolment gets a <code>403</code>. The body carries a limit-reached message; it is covered because its exact wording identifies the product.</figcaption>
</figure>

That check exists, works and is well written. There is nothing wrong with it. The question
is not how to bypass it, it is a different one: **how much time passes between the server
reading the counter and incrementing it.**

```python
used  = db.query("SELECT activateddevices FROM users WHERE id = ?", uid)
limit = db.query("SELECT max_devices FROM plans WHERE id = ?", plan)

if used >= limit:                    # ── check ──
    return error(403, "plan device limit reached")

token = create_device_token(uid)                     # ── use ──
db.execute("UPDATE users SET activateddevices = activateddevices + 1 WHERE id = ?", uid)
return token
```

With two requests at once: the first reads `0`, the second reads `0` too, because the first
has not reached the `UPDATE`. Both pass the `if`. That is TOCTOU, the gap between check and
use.

<figure>
  <img src="{{ '/assets/img/writeups/race-cupo-dispositivos/01-ventana-carrera-en.svg' | relative_url }}"
       alt="Two panels compare the same two requests: sent one after the other, the second reads the already-updated counter and gets a 403; sent at the same time, both read zero inside the same window and both write">
  <figcaption>Same request, same server, same limit. The only thing that changes is when they land.</figcaption>
</figure>

## "At the same time" is not "very fast"

This is where most attempts fail. A loop firing ten requests does not send them at once:
each leaves when the previous one has finished being written to the socket, and between the
first and the last there are milliseconds. To a server that is an eternity. You get one
`200` and nine `403`, and draw the wrong conclusion.

What you need is last-byte synchronisation:

1. Open ten TLS connections.
2. Send each request in full **minus its final byte**. The server cannot start processing:
   the end is missing.
3. Wait until all ten are in that state — that is where all the latency is paid.
4. Release the ten final bytes together.

<figure>
  <img src="{{ '/assets/img/writeups/race-cupo-dispositivos/02-ultimo-byte-en.svg' | relative_url }}"
       alt="Top: three connections sent one after another arrive spread out in time. Bottom: three connections send the whole request minus its final byte and then release the three final bytes together, arriving inside the same window">
  <figcaption>The latency is paid <strong>before</strong> the race starts, not during it.</figcaption>
</figure>

```python
import threading

def race(requests_):
    """Release the final byte of every request at the same instant."""
    conns = [open_tls() for _ in requests_]

    for conn, data in zip(conns, requests_):
        conn.sendall(data[:-1])             # everything but the end

    gate = threading.Barrier(len(requests_))
    responses = [None] * len(requests_)

    def release(i):
        gate.wait()                         # nobody passes until everyone is here
        conns[i].sendall(requests_[i][-1:])
        responses[i] = read(conns[i])

    threads = [threading.Thread(target=release, args=(i,)) for i in range(len(requests_))]
    for t in threads: t.start()
    for t in threads: t.join()
    return responses
```

The key piece is `threading.Barrier`: no thread gets past `gate.wait()` until all of them
have arrived.

## What the server returned

<figure>
  <img src="{{ '/assets/img/writeups/race-cupo-dispositivos/02-seis-en-paralelo.png' | relative_url }}"
       alt="Burp history showing six POST requests to the same endpoint, all stamped 12:29:04: two answer 200 and four answer 403">
  <figcaption>Six enrolments released in the same instant: all six stamped <code>12:29:04</code> and two coming back <code>200</code>, on a one-device account. Intermediate columns cropped out and the host redacted.</figcaption>
</figure>

Nine rounds, two API hosts and two plans. The two clearest:

| Plan | Already used | In parallel | Accepted | What the server reports |
|---|---|---|---|---|
| 7 devices | 3 | 10 | **10** | `activateddevices=13`, `max_devices=7` |
| 1 device | 0 | 10 | **10** | `activateddevices=10`, `max_devices=1` |

That last column is not my inference: it is the server itself, on `GET /users/me`, saying it
has ten active devices on a plan that allows one.

And these are not concurrent sessions. Each of the ten counts in `activateddevices`, has its
own long-lived token with a distinct identifier, and asking `GET /certificate` returns `200`
with its own client credential.

<figure>
  <img src="{{ '/assets/img/writeups/race-cupo-dispositivos/03-contador-2-de-1.png' | relative_url }}"
       alt="Server response with two fields boxed in red: activateddevices with value 2 and max_devices with value 1">
  <figcaption>Not my inference — the server says it. <code>activateddevices: 2</code> against <code>max_devices: 1</code>.</figcaption>
</figure>

## Where I stopped

Ten requests in parallel, no more. I revoked every device created, including when the script
was interrupted, and every account ended with the same device count it started with. Only my
own test accounts. I never connected any of the extra devices to the service: once the server
hands over the credential, the enrolment is proven real.

## Impact

<div class="impact" markdown="1">
The device count **is** what the company sells. Any subscriber can activate more than they
paid for: 13 on a 7-device plan, with one burst of ten requests and under a minute. The
one-device limit of the free and trial plans falls just as easily.

There is no confidentiality or availability impact, and no other account is affected. It
is a **revenue** bug: it removes the reason to buy the next tier up, and it lets one
subscription be shared or resold across many machines.
</div>
