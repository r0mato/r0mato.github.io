---
title:       "Command injection in a privileged macOS helper: the payload is the folder's name"
summary:     "A service running as root checked who was calling it by resolving their path and dropping it, in quotes, into a shell command. All it took was creating a folder whose name carried the injection. A four-character blacklist was not enough."
date:        2026-10-23 08:30:00 +0100
lang:        en
ref:         inyeccion-nombre-carpeta-helper
image:       /assets/img/og/inyeccion-nombre-carpeta-helper-en.png
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

On macOS, an application that needs to touch system configuration installs a **privileged
helper**: a separate process running permanently as root that the application asks for
favours. All of its security comes down to one question: how it checks who is talking to it.

This one did it like so:

1. It asked for the caller's **PID**.
2. From that it resolved the **executable path** on disk.
3. It checked the path for certain forbidden characters.
4. It wrapped it in **single quotes** inside a shell command to verify the signature.
5. It ran that with `popen()`, which is `/bin/sh -c "…"`.

```c
std::string cmd = "/usr/bin/codesign -d --verbose=4 '" + path + "' 2>&1";
std::string out = runWithOutput(cmd);   // popen() → /bin/sh -c
```

Step 4 is the bug: the attacker chooses that path, because they choose where to put their
program.

## The quotes and the blacklist

Single quotes are the strongest way to say "this is literal text", and there was also a
blacklist of four characters. What slipped through was the single quote itself: if you
**close** it, what follows is no longer text.

```bash
# the program builds this:
codesign -d --verbose=4 '<PATH>' 2>&1

# if the path is:   /tmp/p'$(my-script)'
codesign -d --verbose=4 '/tmp/p'$(my-script)'' 2>&1
#                        └ closes ┘└  runs  ┘
```

<figure>
  <img src="{{ '/assets/img/writeups/inyeccion-nombre-carpeta/02-comillas-en.svg' | relative_url }}"
       alt="Diagram comparing the command the program expects, with the path quoted as literal text, and the one it gets, where a quote inside the name closes the quoting and what follows runs">
  <figcaption>Above, what the program thinks it is running. Below, what it actually runs.</figcaption>
</figure>

## The payload is the folder name

I do not get to invent the path: it is where my program lives. So to inject, you create a
folder whose name **is** the injection.

```bash
mkdir "/tmp/p\$(/bin/sh /tmp/x.sh)"
```

I am not sending a malicious value through any field. I create a folder with an odd name
and put my program inside it. When the helper asks where it lives, the answer is the attack.
A quote, a dollar and a parenthesis: a perfectly legal name on macOS.

One detail that forces care: the name **cannot contain a slash**, the one character a
filesystem will not allow in a name. So the payload cannot be a command with paths in it; it
has to call a script that lives elsewhere.

## The rest of the chain

Before reaching the vulnerable line, the helper verified that the program was signed with
the product's identifier. That is not a barrier: macOS lets you ad-hoc sign any binary, with
no developer certificate, carrying whatever identifier you like. It checks that the ID card
bears the company's name, not that the company issued it.

## What it reaches

<figure>
  <img src="{{ '/assets/img/writeups/inyeccion-nombre-carpeta/01-root-desde-cuenta-normal.png' | relative_url }}"
       alt="Terminal of an unprivileged account (uid 502). The executed code answers whoami -> root and uid=0(root), writes and deletes a canary file in a root-only directory, and reads the system accounts database">
  <figcaption>From a normal account (<code>uid=502</code>): <code>whoami → root</code>. It writes a canary into a root-only directory <strong>and deletes it again</strong>, and reads the system accounts file. The group list is covered because it includes one of the product's.</figcaption>
</figure>

Reading, never modifying: the local credential store and the system accounts file, readable
only by root. And the product's own privileged service, which root can rewrite — meaning the
attacker can replace the helper with one of their own and stay in even if the application is
uninstalled.

One thing that makes it worse: when the helper rejects a caller it does not recognise, it
terminates outright. Any legitimate install in progress fails with a generic error. It looks
like a broken installer, not an attack.

## The argument that closes the report

In the product's own installer scripts there was a comment from its developers saying, in
essence, that *otherwise an unprivileged process could request a reinstall at any time*. The
vendor had written down the boundary they wanted to defend; my report showed it was broken by
quoting their own sentence. That convinces far better than any opinion of mine.

## Impact

<div class="impact" markdown="1">
An ordinary user account on that Mac — with no admin password and unable to use `sudo` —
gets to **run code as root**. Nobody has to be tricked and nothing has to be waited for:
create a folder with the right name and ask the helper to do its job.

As root on the machine, the local credential store and the system accounts file are within
reach, and so is writing into system-reserved directories, which is where automatic startup
lives.

What makes it worse: the attacker can **rewrite the privileged component itself**. From
there they stay in even if the victim uninstalls the application, because what remains
installed is no longer the vendor's.

Rated **high (CVSS 7.8)**. Local, but complete: any account on the machine is an
administrator of the machine.
</div>
