---
title:       "How a «+ 1» in a macOS installer ends up giving you root on anyone's Mac"
summary:     "An installation script added one to a number that came from the server. The problem is that in bash \"adding\" means \"evaluating\", and that number could be written by anyone on the internet without an account. Report accepted and rewarded."
date:        2026-11-11 19:30:00 +0100
lang:        en
ref:         rce-instalador-macos-aritmetica
permalink:   /en/writeups/macos-installer-arithmetic-rce/

severity:    high
cvss:        "8.0"
cvss_vector: "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:U/C:H/I:H/A:H"
cwe:         "CWE-78 · CWE-306"
vuln_class:  "Injection"
target_type: "Desktop installer (macOS)"
platform:    "YesWeHack"
status:      "Fixed"
reward:      "Rewarded"
tags:        [rce, macos, bash, installer, root, command-injection]

takeaways:
  - "In bash, `$(( ))` and `[[ … -ge … ]]` **evaluate** their contents. They are not innocent comparisons: they are an open interpreter."
  - "Quoting a variable does not save you inside an arithmetic context. The only thing that works is validating it really is a number."
  - "Desktop installers run as root and almost nobody looks at them. They are prime attack surface, and usually one `curl` away."
  - "If a script asks a server for data, always ask yourself who can write to that server."
---

This was my first published writeup, and I picked the finding I learned the most from: a
command execution **as root** on the Mac of any user of a fairly well-known desktop
application, caused by something that looks harmless at a glance — adding one to a number.

I am going to tell it from the beginning and assume nothing. If you have never touched bash
in your life, you should still be able to follow. If you have, you will see the pattern and
struggle not to look for it everywhere from now on.

<div class="warn" markdown="1">
**Everything is anonymised.** The program authorised publication on condition the product
is not identifiable. I have changed the vendor name, the kind of product, the hosts, the
version numbers and the field names. **The mechanism, the code and the chain are exact**:
the only thing you will not find here is who it happened to.
</div>

## What you will learn

1. Why desktop installers are a great place to look.
2. What `$(( ))` really does in bash and why it is an interpreter in disguise.
3. How to trace a value backwards until you find who controls it.
4. What a **negative control** is and why without one this would not have been a report.

## Why I looked at an installer

When you install a `.pkg` on macOS, the system can run two scripts: `preinstall` before
copying files and `postinstall` afterwards. If the package asks for it, those scripts run
**as root**, the user with total control of the machine.

<div class="plain" markdown="1">
**In plain words:** when you hit "Install" and type your password, you are not just copying
files. You are letting a script written by someone else run whatever it likes on your
computer with administrator privileges. Normally that script does boring, legitimate
things. But if someone manages to slip an order into it, that order runs with those same
privileges.
</div>

And the best part: **an installer is a public file**. You download it, open it and read the
code. No account needed, nothing to attack, not a single odd request sent. It is one of the
few surfaces where you can read the target's source code before touching it:

```bash
# a .pkg is an archive with a known structure
pkgutil --expand-full installer.pkg /tmp/installer-open

# and the scripts are right there, in plain text
cat /tmp/installer-open/*.pkg/Scripts/postinstall
```

That is all. Two commands and you are reading the code that will run as root on thousands
of people's computers.

{% comment %} PENDIENTE DE CAPTURA — quita esta linea y la de cierre cuando exista el fichero
<figure>
  <img src="{{ '/assets/img/writeups/rce-instalador-macos/01-pkg-expandido.png' | relative_url }}"
       alt="Terminal showing the expanded package and the folder structure with the postinstall script">
  <figcaption>The expanded package. From here on I am not guessing: I am reading.</figcaption>
</figure>
{% endcomment %}

## The line that made me stop

Reading the `postinstall` I found this:

```bash
# prepare data for feedback server
new_installation_count=$((install_count + 1))
```

An addition. The most harmless thing in the world. And yet that is where I stopped, for a
reason that deserves its own section.

## Masterclass: `$(( ))` does not add, it *evaluates*

This is the most important part of the article. If you take one thing away, take this.

In bash, `$(( ... ))` is called **arithmetic expansion**. You think you are asking it to
"do this sum", but what you are really saying is "**evaluate** this as an expression". And
evaluating, in bash, includes resolving whatever is inside.

Try it yourself in a terminal. First, the normal case:

```bash
number=5
echo $((number + 1))      # 6
```

No surprises. Now the not-so-normal case:

```bash
number='a[$(touch /tmp/i-got-in)]'
echo $((number + 1))      # 0
ls -l /tmp/i-got-in       # the file exists
```

<div class="plain" markdown="1">
**In plain words:** we asked bash to add one to a variable. But the variable did not hold a
number, it held **an order**. And bash, before adding, ran the order. The sum returned `0`
and looked like nothing happened — but the file is there. That is the whole vulnerability:
in a place expecting a number you put an order, and it runs.
</div>

Why does this happen? Because inside `$(( ))` bash allows array indices — `a[something]` —
and to know which index that is, it has to **resolve** what is inside the brackets. If
there is a `$(command)` in there, it runs it to find out the result. Command substitution
happens *before* the arithmetic.

And here is the part most people get wrong:

<div class="warn" markdown="1">
**Quotes do not protect you.** This still executes:

```bash
echo $(( "$number" + 1 ))
```

Quoting stops the shell splitting the variable into pieces, not evaluating it. Inside an
arithmetic context **the content is evaluated anyway**. The same goes for
`[[ "$x" -ge 10 ]]`, which plenty of people use believing it is a safe comparison.
</div>

Note the detail: with `[ "$x" -ge 10 ]` — **single bracket**, which is POSIX `test` — this
does **not** happen: you get an "integer expression expected" error and nothing runs. In
other words, the bug is not a "shell thing" in general: it is specific to `$(( ))` and
`[[ ]]`. That nuance later served as my negative control, as you will see.

## Where did that number come from?

Fine: there is a dangerous place. The next question is not "how do I exploit it?" but
**"who decides that value?"**. A `$(( ))` with a number the script computes itself is of no
interest whatsoever. What is interesting is whether that number comes from outside.

So I followed the variable backwards through the script, and found this:

```bash
# the script downloads a remote record identified by install_id
curl_data=$(curl -s "https://feedback.example.tld/v2/feedback/${install_id}?plain=1")

# and parses it by hand, stripping only the double quotes
while IFS=':' read -r name value; do
    case "$name" in
        *installCount*) install_count="${value//\"/}" ;;
    esac
done <<< "$curl_data"
```

<div class="plain" markdown="1">
**In plain words:** the installer calls a server, downloads some text, looks for a line
containing the word `installCount` and keeps whatever is to the right of it, stripping only
the quotes. Whatever the server put there ends up inside the variable. And that variable
ends up inside `$(( ))`.
</div>

In other words: **the server decides the value**. Which led to the question that opened
everything up.

## The question that opened everything up: who can write to that server?

If only the vendor can write that record, this is an ugly but barely exploitable bug. If
anyone can write it, it is remote command execution as root.

I tried writing, with no account, no token, nothing:

```http
POST /v2/feedback?plain=1 HTTP/2
Host: feedback.example.tld
Content-Type: application/json

{"clickId":"<my-canary-id>",
 "clickData":{"custom":{"installCount":"a[$(id > /tmp/canary_root)]"}}}
```

```http
HTTP/2 200 OK
```

Two hundred. No authentication. Anyone, from anywhere.

{% comment %} PENDIENTE DE CAPTURA — quita esta linea y la de cierre cuando exista el fichero
<figure>
  <img src="{{ '/assets/img/writeups/rce-instalador-macos/02-escritura-sin-auth.png' | relative_url }}"
       alt="Burp Repeater: POST request with no authorisation header and 200 OK response from the feedback server">
  <figcaption>No <code>Authorization</code> header, no cookie, nothing. <code>200 OK</code>.</figcaption>
</figure>
{% endcomment %}

And reading it back, the value came back **byte for byte**, nothing filtered or escaped:

```http
GET /v2/feedback/<my-canary-id>?plain=1
```

```
custom.installCount:"a[$(id > /tmp/canary_root)]"
```

## And how does the attacker know my identifier?

Good question, and it is the one separating a theoretical finding from a real one. The
`install_id` could have been an unguessable secret. It was not: the script itself pulls it
from the **downloaded file's name** and from the metadata macOS stores about where it came
from:

```bash
# macOS stores each download's origin URL in an extended attribute
mdls -name kMDItemWhereFroms installer_<install_id>.pkg
```

<div class="plain" markdown="1">
**In plain words:** that identifier travels glued to the installer. It is in the filename
and in the metadata macOS attaches on download. If someone shares their installer over
chat, a forum or an affiliate link, they are sharing the identifier. It is not a secret: it
is a label.
</div>

## The full chain

<figure>
  <img src="{{ '/assets/img/writeups/rce-instalador-macos/03-cadena.svg' | relative_url }}"
       alt="Diagram: the attacker writes to the feedback server without authentication, the victim installs, the script downloads the value and evaluates it as root">
  <figcaption>Nobody validates anything along the way. The value goes in as text and comes out as an order.</figcaption>
</figure>

Summed up in five steps:

1. The attacker writes a malicious value to the feedback server. **No account.**
2. The victim installs or reinstalls the application. A normal, documented action.
3. The `postinstall`, running **as root**, downloads that value.
4. The parsing loop puts it in a variable, stripping only the quotes.
5. `$((install_count + 1))` **evaluates** it, and the order runs as root.

## The part that unsettled me most: the victim sees nothing

Reading the rest of the script I found this:

```bash
# always exit with code 0 to not show any error in the installer
trap finish EXIT
finish() { exit 0; }
```

<div class="plain" markdown="1">
**In plain words:** the script is programmed to always say "everything went fine", whatever
happens. It is a convenient decision so the user never sees odd errors. But it means that
if your order runs and breaks the script halfway, **the installer still shows a green tick**.
The victim gets not a single hint.
</div>

The script also used neither `set -u` nor `set -e`, so a malformed value did not stop it
either.

## The negative control: what turns this into a report

Here is the part bug bounty taught me the most, and the one most people skip.

Seeing that something "works" is not enough. You have to prove it works **for the reason
you say** and not another. For that you repeat exactly the same test changing **one single
thing**: the attack condition.

| What I tried | What happened | What it rules out |
|---|---|---|
| The same path with a normal numeric value (`"5"`) | The arithmetic resolves, **nothing runs** | That the mechanism fires on any input |
| `[ "$v" -ge 10 ]` — single bracket, POSIX `test` | Error: *integer expression expected*. Nothing runs | That it is generic to all shell comparisons |
| Writing to the server **without** the payload | `200`, stores the value and returns it unchanged | That the service filters or type-checks the field |
| The Windows installer, same field | Not affected: parses the value as an integer | That the bug belongs to the product in general |

<div class="plain" markdown="1">
**In plain words:** put a normal number in, nothing happens. Use the POSIX comparison,
nothing happens. Remove the order, nothing happens. It only happens when you put an order
inside an arithmetic context. That proves the bug is exactly the one I say it is and not a
coincidence.
</div>

That last point — that **Windows was not vulnerable** — I included by choice, even though
it narrowed my own finding. The Windows installer parses the same field as an integer, so a
string never reaches any interpreter. Scoping your own finding buys enormous credibility
with whoever triages it, and stops it coming back as overstated.

## Impact

<div class="impact" markdown="1">
**Impact.** Arbitrary command execution **as root** on the victim's Mac when installing or
reinstalling. Total control of the machine: reading any file, installing persistence,
stealing credentials. No account on the attacker's side and not a single visible hint for
the victim, who sees an installation that finished successfully.
</div>

## The fix

Conceptually one line: **validate it is a number before it touches an arithmetic context.**

```bash
install_count="${value//\"/}"
case "$install_count" in
    ''|*[!0-9]*) install_count=0 ;;   # not a number -> discard
esac
```

And what I also recommended:

1. The same guard **everywhere** that counter is read, not just here.
2. Require authentication on the `POST`, so a third party cannot write another
   installation's record.
3. Reject non-numeric values for that field server-side.
4. Treat everything coming from that server as **untrusted**, in every consumer. Client and
   server validation do not replace each other: they add up.

## How to look for this yourself

If you want to practise, this is literally a `grep`:

```bash
pkgutil --expand-full any-installer.pkg /tmp/x
grep -rnE '\$\(\(|\[\[ .* -(ge|gt|le|lt|eq) ' /tmp/x --include=postinstall --include=preinstall
```

And for each hit, the same two questions:

1. **Where does that value come from?** If the script computes it, forget it. If it comes
   from a file, an environment variable or the network, keep going.
2. **Who can write to that source?** If the answer is "anyone", you have it.

<div class="note" markdown="1">
**Only do this where you have permission.** Reading an installer you downloaded is yours
and it is legal. Writing to a company's production API **is not**, unless you are inside
the scope of a program that authorises it, and using your own canary data. I used a
disposable identifier of my own and deleted it when I was done.
</div>
