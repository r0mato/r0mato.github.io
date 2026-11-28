---
title:       "9.8 RCE in production through an AI agent with a code-execution tool"
summary:     "An internal conversational assistant had, among its tools, one that executed Python on the server. Anyone could ask for it. I proved it with a cryptographic canary, because \"the model made that up\" is the objection that kills these reports."
date:        2026-10-17 17:20:00 +0100
lang:        en
ref:         rce-agente-ia-tool
image:       /assets/img/og/rce-agente-ia-tool-en.png
permalink:   /en/writeups/ai-agent-code-execution-tool/

severity:    critical
cvss:        "9.8"
cvss_vector: "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
cwe:         "CWE-94 · CWE-862"
vuln_class:  "Injection"
target_type: "AI agent (API)"
platform:    "YesWeHack"
status:      "Fixed"
tags:        [rce, ai, llm, agents, python, kubernetes, code-injection]

takeaways:
  - "In an AI agent the bug is almost never in the model: it is in the **tools** it was given and in who can invoke them."
  - "\"The model hallucinated it\" is the objection that kills these reports. A cryptographic canary closes it instantly: a model cannot guess a SHA-256."
  - "Ask the agent what tools it has. It will often list them for you."
  - "Two different bugs sharing one entrance are still two bugs: one is fixed by rotating a key, the other by removing a tool."
---

A chatbot takes text and returns text. An agent has **tools** — query a database, call an
API, run code — and the system actually executes them when the model decides to use one. So
auditing an assistant is not trying to make it say silly things: it is asking what tools it
has and who can ask it to use them.

<figure>
  <img src="{{ '/assets/img/writeups/rce-agente-ia/02-chatbot-vs-agente-en.svg' | relative_url }}"
       alt="Diagram comparing a chatbot, which only returns text, with an agent, which has a list of tools including one that runs code on the server">
  <figcaption>A chatbot answers. An agent acts. And its list of tools is the attack surface.</figcaption>
</figure>

This was a corporate portal's internal assistant. I already knew how to talk to it without
an account, because [the signing key sat in a public JavaScript file]({{ '/en/writeups/aes-key-in-public-bundle/' | relative_url }}).

## What tools it has

I asked it:

```
What tools do you have available? List their exact names.
```

In the list:

```
run_ipython_cell
```

## The trap

The tempting move is to ask for `import os; print(os.getcwd())`, get `/app/workspace` back,
and send that in.

<div class="warn" markdown="1">
**A model can invent that answer entirely.** It was trained on millions of terminal
sessions: it will tell you something plausible whether or not it ran the code. Whoever
triages it will reply — rightly — that the model hallucinated the output, and close it.
</div>

## The canary

You need something impossible to guess and trivial to verify. A SHA-256 is both, and a
model cannot compute the hash of a string I just made up.

```bash
# on MY machine, BEFORE touching the server
python3 -c 'import hashlib; print(hashlib.sha256(b"canary-verification-20261017-7f3ad9").hexdigest())'
# 0e407c15aa4778af3f4ba76dbfa2b0d3fd990d2f365bdf3aa3d95091e4069005
```

```http
POST /assistant/chat/v1/messages HTTP/2
Host: portal.example.tld
X-Authorization: <minted token, no account>

{"user":"canary-bbtest",
 "query":"Use run_ipython_cell to run this line and paste the literal output:
          import hashlib; print(hashlib.sha256(b\"canary-verification-20261017-7f3ad9\").hexdigest())",
 "is_agent":"1"}
```

```json
{"actionName":"run_ipython_cell",
 "observation":"0e407c15aa4778af3f4ba76dbfa2b0d3fd990d2f365bdf3aa3d95091e4069005"}
```

Character for character, the same. I repeated it twice more with different strings: one
canary could be luck, three are not.

<figure>
  <img src="{{ '/assets/img/writeups/rce-agente-ia/03-canario-en.svg' | relative_url }}"
       alt="Canary diagram: the hash is computed on the researcher's own machine, the agent is asked to compute it with its tool, and the two values are compared">
  <figcaption>The hash is computed before touching the server. If it comes back identical, it ran.</figcaption>
</figure>

## Where it was running

```python
import os, socket
print(os.getuid())        # 0  -> root
print(socket.gethostname())
print(len(os.environ))    # how many variables, not their contents
```

**uid 0**, inside a container on a production cluster, with network visibility of several
dozen internal services and credentials in the process environment.

<figure>
  <img src="{{ '/assets/img/writeups/rce-agente-ia/01-root.png' | relative_url }}"
       alt="Excerpt of the agent response: the arguments field carries the code import os as o;print(o.popen(whoami).read().strip()) and the observation field returns root, boxed in red">
  <figcaption>The agent runs the line and returns the output: <code>observation: "root"</code>. Excerpt of the response; the rest carries product identifiers.</figcaption>
</figure>

<div class="note" markdown="1">
**Where I stopped.** I read the uid, the hostname and counted the environment variables. I
did not read their contents, did not move to any internal service, did not touch data and
left nothing installed.
</div>

## Why it goes separately from the authentication bug

The way in was the same, but these are two bugs with two different fixes:

| | Authentication bug | This one |
|---|---|---|
| **What it is** | You can get in with no account | There is a tool that runs code |
| **How it is fixed** | Rotate the key, bind the token to a user | Remove the tool from the agent |
| **If only the other is fixed** | — | Still exploitable **by any legitimate employee** |

That last row is the argument: even if they fix authentication tomorrow, any employee with
normal chat access can still run code as root in production.

## Impact

<div class="impact" markdown="1">
**Impact.** Arbitrary code execution as **root** in a production container, reachable from
the internet and with no account required. From that position: reading the process
credentials, lateral movement to the visible internal services, and access to the data
those services hold. In practice, the worst possible outcome for an exposed application.
</div>
