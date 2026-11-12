---
title:       "A folder name as a weapon: command injection in a privileged macOS helper"
summary:     "A service running as root checked who was calling it by resolving their path and dropping it, in quotes, into a shell command. All it took was creating a folder whose name carried the injection. A four-character blacklist was not enough."
date:        2026-11-11 20:40:00 +0100
lang:        en
ref:         inyeccion-nombre-carpeta-helper
permalink:   /en/writeups/folder-name-command-injection-macos-helper/

severity:    high
cvss:        "7.8"
cvss_vector: "CVSS:3.1/AV:L/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H"
cwe:         "CWE-78 · CWE-807"
vuln_class:  "Injection"
target_type: "Privileged service (macOS)"
platform:    "YesWeHack"
status:      "Reported"
tags:        [privilege-escalation, macos, xpc, command-injection, root, blacklist]

takeaways:
  - "A character blacklist is the wrong control. If you have to enumerate what you forbid, you have already lost."
  - "The filesystem is user input: a folder name can carry an injection inside it."
  - "Identifying your caller by PID is a race lost in advance; macOS has a cryptographic mechanism for it and the product already used it elsewhere."
  - "If the vendor's own code documents the boundary their bug crosses, quote it. Nothing is more convincing than their own comment."
---

This bug has my favourite part of offensive security in it: the answer is not sending a
weird value, it is **creating a folder**. The filesystem, which nobody treats as user
input, is the user input.

<div class="warn" markdown="1">
**Everything is anonymised.** Vendor, service identifiers and product paths have been
changed. The mechanism, the checks the binary performs and the technique are exact.
</div>

## What a "privileged helper" is

On macOS, an ordinary application cannot touch system configuration. When it needs to —
configuring the network, installing a service, modifying protected folders — it installs a
**privileged helper**: a small separate program that runs **as root** permanently and that
the application asks for favours.

<div class="plain" markdown="1">
**In plain words:** it is a butler with the keys to everything. The app does not open the
doors: it asks the butler. And since the butler holds every key, **the only thing standing
between him and disaster is knowing who he is obeying**.

Which is why the security of these components boils down to one question: how does it check
who is talking to it?
</div>

## How this one checked its caller

The helper did this, in this order:

1. Asked for the **PID** — the process number — of whoever was talking to it.
2. Used that number to resolve the **executable's path** on disk.
3. Checked that path did not contain certain forbidden characters.
4. Dropped the path **between single quotes** into a shell command, to verify the
   program's digital signature.
5. Ran that command with `popen()`, which means launching `/bin/sh -c "…"`.

```c
std::string cmd = "/usr/bin/codesign -d --verbose=4 '" + path + "' 2>&1";
std::string out = runWithOutput(cmd);   // popen() → /bin/sh -c
```

Step 4 is the bug. The path — something **the attacker chooses**, because they choose where
their program lives — ends up inside a string the shell interprets.

<div class="plain" markdown="1">
**In plain words:** to verify your identity, the butler writes your address on a piece of
paper, hands it to the cook and says "do what it says". If your address is *"5 Main Street;
burn the house down"*, the cook reads both.
</div>

## Single quotes: the false sense of safety

The developer was not entirely naive. They put the path **between single quotes**, which in
a shell is the strongest way of saying "this is literal text".

```bash
echo 'this $(does not) execute'      # printed as is
```

And they added a **four-character blacklist**, so you could not sneak anything in.

<div class="plain" markdown="1">
**In plain words:** a blacklist is the *"I'll forbid the dangerous stuff"* strategy. The
problem is that for it to work you must have thought of **everything** dangerous. And
something always gets away.

What got away here was the single quote itself. If you **close** the quote, whatever comes
after is no longer literal text: it is code.
</div>

```bash
# the program builds this:
codesign -d --verbose=4 '<PATH>' 2>&1

# if the path is:   /tmp/p'$(my-script)'
# it becomes:
codesign -d --verbose=4 '/tmp/p'$(my-script)'' 2>&1
#                        └ closes ┘└ executes ┘
```

## The idea: make the injection the folder's name

Here is the beautiful part. The "path" is not something I make up: it is **where my program
lives**. So to inject, I have to **create a folder whose name is the injection**:

```bash
mkdir "/tmp/p\$(/bin/sh /tmp/x.sh)"
```

<div class="plain" markdown="1">
**In plain words:** I am not sending a malicious value through any field. I am creating a
folder with an odd name and putting my program inside it. When the butler asks "where do
you live?", the answer **is** the attack.

And it is a perfectly legal folder name on macOS: a quote, a dollar sign and a parenthesis.
Nothing forbidden.
</div>

A lovely detail of this case: the name **cannot contain a slash `/`**, because it is the
one character filesystems do not allow in a name. So the payload cannot be a command with
paths: it has to **call a script** living somewhere else. Filesystem limitations force you
to design the payload carefully, and that is part of the fun.

## The rest of the chain

One intermediate check remained: the helper verified the program was **signed** with the
product's identifier before reaching the vulnerable line.

That sounds like a barrier, but it is not: macOS lets you sign any binary **ad hoc**,
without a developer certificate, giving it whatever identifier you like. And that is exactly
what the check looked at.

<div class="plain" markdown="1">
**In plain words:** the butler checks you are carrying a badge with the company name on it.
But he does not check the company issued it — only that it says so. And anyone can print
one.
</div>

{% comment %} PENDIENTE DE CAPTURA — quita esta linea y la de cierre cuando exista el fichero
<figure>
  <img src="{{ '/assets/img/writeups/inyeccion-nombre-carpeta/01-root-conseguido.png' | relative_url }}"
       alt="Unprivileged user's terminal showing the canary file written by root and the contents of root-only files">
  <figcaption>From an unprivileged account: files only root can read, on screen.</figcaption>
</figure>
{% endcomment %}

## What it reaches from there

With code running as root I was able to confirm — by reading, never modifying — that it
reached:

- **The system's local credential store** and the accounts file, readable only by root.
- **The product's own privileged service**, which root can rewrite. In other words: the
  attacker can replace the butler with one of their own.

<div class="plain" markdown="1">
**In plain words:** once you are root on a Mac, the product you were attacking is the least
of it. You have the machine. And in this case you can also modify the privileged component
itself, which means you stay in even if the application is uninstalled.
</div>

And a detail that makes it worse: when the helper rejects a caller it does not recognise,
it **exits immediately**. The result is that any legitimate installation in progress fails
with a generic installer error. It looks like an installer glitch, not an attack.

## The negative control

| What I tried | What happened | What it rules out |
|---|---|---|
| The same program from a **normal** path | Works: no extra execution | That the helper ran things by itself |
| The injected path but **without** the ad hoc signature | Rejected before reaching it | That the signature check did not exist |
| Repeating the whole thing **again**, new canary and new name | Same result | That it was an odd state of one particular run |

Repeating it from scratch with **a different canary name** is what turns "it happened once"
into "this is reproducible". A triager who cannot reproduce your bug closes it.

## The argument that closes the report

Reading the product's own installer scripts, I found a comment from its developers saying,
in essence, that *otherwise an unprivileged process could request a reinstall at any time*.

<div class="plain" markdown="1">
**In plain words:** the vendor had written down, in their own code, which boundary they
wanted to defend. My report proved that boundary was broken, **quoting their own
sentence**.

This is one of the most effective things you can put in a report: it is not your opinion
about what should happen, it is theirs.
</div>

## The fix

1. **Do not build a shell command.** The binary already contained a safe way to launch
   programs with an argument list. Using it removes the entire class:

   ```c
   - std::string cmd = "/usr/bin/codesign -d --verbose=4 '" + path + "' 2>&1";
   - runWithOutput(cmd);                      // popen() → /bin/sh -c
   + const char *argv[] = {"/usr/bin/codesign", "-d", "--verbose=4", path, NULL};
   + runWithOutputArgv(argv);                 // no shell: nothing to escape
   ```

2. **Identify the caller by audit token**, not by PID and path. macOS provides a
   cryptographic mechanism for this that cannot be spoofed. The product **already used it**
   in another part of the same binary: it only had to be applied here too.

3. **Delete the blacklist.** With separate arguments there is nothing to filter. And a
   metacharacter blacklist is the wrong control anyway.

<div class="plain" markdown="1">
**In plain words:** identifying a process by PID is inherently unsafe, because process
numbers **get reused**: an attacker can make theirs die and have another take its number
right at the moment of the check. That is why audit tokens exist — they identify the
process in a way that cannot be forged.
</div>

## How to look for this yourself

On any privileged macOS service:

1. **Find them:** `ls -la /Library/PrivilegedHelperTools/` and `ls /Library/LaunchDaemons/`.
2. **Look at which functions it imports:** if `popen`, `system` or `exec` show up alongside
   string building, raise the alarm.
   ```bash
   nm -u /Library/PrivilegedHelperTools/com.example.helper | grep -E 'popen|system|exec'
   ```
3. **Find how it identifies the caller:** if you see `xpc_connection_get_pid` and
   `proc_pidpath` but **not** `SecCodeCreateWithAuditToken`, identification is PID-based and
   spoofable.
4. **Ask which part of that string you control.** Your own binary's path is the first one —
   and you choose it by creating folders.

<div class="note" markdown="1">
**Only on your own machine.** This is researched on your own VM, with your own accounts,
and you stop the moment the primitive is demonstrated. A harmless canary proves exactly the
same thing as a real attack, and leaves nobody in a compromised position — starting with
you.
</div>
