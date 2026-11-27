---
title:       "Race condition on a paid quota: 10 devices activated where only 1 fit"
summary:     "The counter that enforces each plan's device quota was read before it was incremented. Sent one after another, the second activation gets a 403. Released in the same instant, all ten get through: ten real devices, each with a valid credential, on an account that allows one. Ten real devices on an account that allows one."
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

It reproduces nine times out of nine, with the server stating in writing that it is above
its own limit: ten active devices on an account that allows one. All it takes is sending
the requests **in the same instant** instead of one after another.

<div class="warn" markdown="1">
**Everything is anonymised.** Published with the program's consent and without identifying
the product: vendor, domains, paths, field names and error messages have all been changed.
The mechanism, the sequence and the numbers are exact.
</div>

## The device quota, which is literally the product

Plenty of subscription services price themselves by **a number of devices**. You are not
paying for more features or more speed: you are paying to use it on three machines instead
of one. The plan is called, literally, "7 devices".

When you install the app on a new machine, it calls an enrolment endpoint:

```http
POST /oauth/access_token
Content-Type: application/json

{"x_auth_machineid":"living-room-laptop","x_auth_machinename":"living-room-laptop",
 "x_auth_mode":"client_auth","x_auth_username":"<email>","x_auth_password":"<password>","reset":0}
```

If there is room, it answers `200` with a device token. If there is not:

```
403 Forbidden
```

That `403` is the product doing its job. The check **exists, works and is well written**.
I am not going to find a flaw in it, because it does not have one.

<figure>
  <img src="{{ '/assets/img/writeups/race-cupo-dispositivos/01-control-403.png' | relative_url }}"
       alt="Burp Repeater: a device enrolment sent with the account full gets HTTP/2 403 Forbidden. The headers and the message body are covered with labelled bars">
  <figcaption>With the account full, the enrolment gets a <code>403</code>. The body carries a limit-reached message; it is covered because its exact wording identifies the product.</figcaption>
</figure>

## The question that opens the case

It is not "can I bypass the check?". It is a much cheaper one:

> **How long passes between the server reading the counter and incrementing it?**

Because in 99% of the places I have seen this, the code has this shape:

```python
used  = db.query("SELECT activateddevices FROM users WHERE id = ?", uid)
limit = db.query("SELECT max_devices FROM plans WHERE id = ?", plan)

if used >= limit:                    # ── check ──
    return error(403, "device limit reached for this plan")

token = create_device_token(uid)                     # ── act ──
db.execute("UPDATE users SET activateddevices = activateddevices + 1 WHERE id = ?", uid)
return token
```

Read it again thinking about **two requests at once**. The first reads `0`. The second
reads… also `0`, because the first has not reached the `UPDATE` yet. Both pass the `if`.
Both create a token. Both add one.

That has had a name for decades: **TOCTOU**, *time of check to time of use*. The gap
between checking and using.

<figure>
  <img src="{{ '/assets/img/writeups/race-cupo-dispositivos/01-ventana-carrera-en.svg' | relative_url }}"
       alt="Two panels compare the same two requests: sent one after the other, the second reads the already-updated counter and gets a 403; sent at the same time, both read zero inside the same window and both write">
  <figcaption>Same request, same server, same limit. The only thing that changes is when they land.</figcaption>
</figure>

## "At the same time" is not "very fast"

This is where most attempts at exploiting a race fail, and where the technique actually
worth learning lives.

If you open a loop and fire ten requests back to back, **they do not go at the same time**.
Each one leaves when the previous has finished being written to the socket, and between
the first and the last there are milliseconds of network. To a server, milliseconds are an
eternity: the first request's `UPDATE` is already done when the second arrives. You get
one `200` and nine `403`s, and you conclude there is no bug. Wrong conclusion.

What you need is for all ten to land inside the **same window**, and that is what last-byte
synchronisation is for:

1. Open ten TLS connections, one per request.
2. On each one, send the whole request **minus its final byte**. The server receives
   almost everything but cannot start processing anything: the end is missing.
3. Wait until all ten are in that state — that is where the entire latency is paid.
4. Release the ten final bytes together.

All ten server threads start at once.

<figure>
  <img src="{{ '/assets/img/writeups/race-cupo-dispositivos/02-ultimo-byte-en.svg' | relative_url }}"
       alt="Top: three connections sent one after another arrive spread out in time. Bottom: three connections send the whole request minus its final byte and then release the three final bytes together, arriving inside the same window">
  <figcaption>The latency is paid <strong>before</strong> the race starts, not during it.</figcaption>
</figure>

In Python that is shorter than it sounds. The essential part fits in one function:

```python
import threading

def race(requests):
    """Release the final byte of every request at the same instant."""
    conns = [open_tls() for _ in requests]

    for conn, data in zip(conns, requests):
        conn.sendall(data[:-1])             # everything but the end

    gate = threading.Barrier(len(requests))
    answers = [None] * len(requests)

    def release(i):
        gate.wait()                         # nobody passes until everyone is here
        conns[i].sendall(requests[i][-1:])
        answers[i] = read(conns[i])

    threads = [threading.Thread(target=release, args=(i,)) for i in range(len(requests))]
    for t in threads: t.start()
    for t in threads: t.join()
    return answers
```

The key piece is `threading.Barrier`: no thread gets past `gate.wait()` until they have all
arrived. When it opens, the ten final-byte `sendall` calls go out practically glued
together.

<div class="note" markdown="1">
**Why I am not publishing the full script.** The one I sent to the program is around 250
lines, because it does the serial enrolment, the race, the verification and the cleanup of
everything it creates. What is worth
learning is the function above; the rest is plumbing tied to one specific product.
</div>

## What the server returned

<figure>
  <img src="{{ '/assets/img/writeups/race-cupo-dispositivos/02-seis-en-paralelo.png' | relative_url }}"
       alt="Burp history showing six POST requests to the same endpoint, all stamped 12:29:04: two answer 200 and four answer 403">
  <figcaption>Six enrolments released in the same instant: all six stamped <code>12:29:04</code> and two coming back <code>200</code>, on a one-device account. Intermediate columns cropped out and the host redacted.</figcaption>
</figure>

Nine runs, two API hosts and two different plans. The two clearest:

| Plan | Already in use | In parallel | Accepted | What the server reports |
|---|---|---|---|---|
| 7 devices | 3 | 10 | **10** | `activateddevices=13`, `max_devices=7` |
| 1 device | 0 | 10 | **10** | `activateddevices=10`, `max_devices=1` |

I want to underline that last column, because it is not my inference: it is the server
itself, in its answer to `GET /users/me`, saying it has **ten active devices on a plan
that allows one**. Nothing needs interpreting.

And these are not sessions or concurrent connections. Each of the ten is a persistent
enrolment:

- it counts towards `activateddevices`,
- it has its own long-lived token, with a distinct identifier,
- and asking for `GET /certificate` returns `200` with its own client credential.

Which is to say: exactly what `max_devices` exists to limit.

<figure>
  <img src="{{ '/assets/img/writeups/race-cupo-dispositivos/03-contador-2-de-1.png' | relative_url }}"
       alt="Server response with two fields boxed in red: activateddevices with value 2 and max_devices with value 1">
  <figcaption>Not my inference — the server says it. <code>activateddevices: 2</code> against <code>max_devices: 1</code>.</figcaption>
</figure>

## How far I went, and where I stopped

Ten parallel requests, no more. Every device created was revoked, including when the
script was interrupted, and every account ended with the same device count it started
with. I only used my own test accounts. I never connected any of the extra devices to the
service: the server handing me the credential already proves the enrolment is real, and
connecting adds nothing to the report.

## Impact

<div class="impact" markdown="1">
The device count **is** what the company sells. Any subscriber can activate more than they
paid for: 13 on a 7-device plan, with one burst of ten requests and under a minute. The
one-device limit of the free and trial plans falls just as easily.

There is no confidentiality or availability impact, and no other account is affected. It
is a **revenue** bug: it removes the reason to buy the next tier up, and it lets one
subscription be shared or resold across many machines.
</div>
