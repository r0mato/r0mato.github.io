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

This is the most technically serious bug I have found, and the one that best explains why
AI assistants are a new and different attack surface. Spoiler: **the problem was not the
language model**. The problem was what they had let it do.

<div class="warn" markdown="1">
**Everything is anonymised.** Published with the program's permission and without
identifying the product: company, domains, paths, service and agent names have been
changed. The mechanism, the verification method and the impact are exact.
</div>

## First, what an "agent" is and why it changes the rules

A normal chatbot takes text and returns text. If you ask it to delete a file, it replies
something pleasant and nothing happens, because **it cannot touch anything**.

An **agent** is a different animal. You give an agent *tools*: search a database, call an
API, send an email, run code. The model decides **which one to use** based on what you ask,
and the system **actually runs it**.

A chatbot is someone on the phone giving you advice. An agent is
someone on the phone **with the keys to your house**. The conversation is just as harmless;
what changes is what they can do while talking to you.

That is why, when auditing an AI assistant, the question is not "can I make it say silly
things?". The question is **"what tools does it have and who can ask it to use them?"**.

<figure>
  <img src="{{ '/assets/img/writeups/rce-agente-ia/02-chatbot-vs-agente-en.svg' | relative_url }}"
       alt="Diagram comparing a chatbot, which only returns text, with an agent, which has a list of tools including one that runs code on the server">
  <figcaption>A chatbot answers. An agent acts. And its list of tools is the attack surface.</figcaption>
</figure>

## The target

The internal assistant of a corporate portal. I had already found how to talk to it without
an account — [the signing key was in a public JavaScript file]({{ '/en/writeups/aes-key-in-public-bundle/' | relative_url }}) —
so I could send it messages like any employee.

The next question was obvious: **what can this thing do?**

## Step 1: ask it what tools it has

No reverse engineering required. Often, asking is enough:

```
What tools do you have available? List their exact names.
```

Among the list was one that made me sit up straight:

```
run_ipython_cell
```

The name leaves no room for doubt: a tool that "runs an IPython cell" runs whatever Python it is given, inside an assistant anyone can write to.

## Step 2: the trap almost everyone falls into

The temptation is to ask it to run something and show the answer. Like this:

```
Run: import os; print(os.getcwd())
```

And the assistant replies something like `/app/workspace`. Done? **No.** And this is the
most valuable lesson in the whole article:

<div class="warn" markdown="1">
**A language model can invent that answer entirely.** It was trained on millions of
terminal sessions. Ask it for the current directory and it will tell you something
plausible whether or not it ran the code.

If you send that report, whoever triages it will reply — rightly — *"the model hallucinated
the output"*, and close it. I have watched many AI reports die exactly like that.
</div>

You need proof that **a model cannot fake**.

## Step 3: the cryptographic canary

The solution is elegant and you can reuse it forever: ask it to compute something whose
result is **impossible to guess but trivial to verify**.

A SHA-256 hash meets both conditions.

```bash
# 1 · on MY machine, BEFORE touching the server
python3 -c 'import hashlib; print(hashlib.sha256(b"canary-verify-20261017-7f3ad9").hexdigest())'
# 0e407c15aa4778af3f4ba76dbfa2b0d3fd990d2f365bdf3aa3d95091e4069005
```

A hash is a fingerprint of a piece of text. Change one letter and the
fingerprint changes completely. There is no way to "deduce" it: you have to compute it.

A language model **cannot compute hashes**. It can recite famous hashes it saw during
training, but it cannot produce one for a string I just invented. If the server returns
exactly the same fingerprint I computed on my laptop, there is only one explanation: **it
really ran the code**.

And now, to the assistant:

```http
POST /assistant/chat/v1/messages HTTP/2
Host: portal.example.tld
X-Authorization: <minted token, no account>

{"user":"canary-bbtest",
 "query":"Use run_ipython_cell to run this line and paste the literal output:
          import hashlib; print(hashlib.sha256(b\"canary-verify-20261017-7f3ad9\").hexdigest())",
 "is_agent":"1"}
```

The response arrived as an event stream, and inside it was this:

```json
{"actionName":"run_ipython_cell",
 "observation":"0e407c15aa4778af3f4ba76dbfa2b0d3fd990d2f365bdf3aa3d95091e4069005"}
```

{% comment %} PENDIENTE DE CAPTURA — quita esta linea y la de cierre cuando exista el fichero
<figure>
  <img src="{{ '/assets/img/writeups/rce-agente-ia/01-canario.png' | relative_url }}"
       alt="Two terminals side by side: on the left the SHA-256 computed locally, on the right the server's response with the identical value">
  <figcaption>Left: computed on my machine before touching anything. Right: returned by the server. Identical. That cannot be improvised.</figcaption>
</figure>
{% endcomment %}

**Character for character, the same.** That closes the discussion.

<figure>
  <img src="{{ '/assets/img/writeups/rce-agente-ia/03-canario-en.svg' | relative_url }}"
       alt="Canary diagram: the hash is computed on the researcher's own machine, the agent is asked to compute it with its tool, and the two values are compared">
  <figcaption>The hash is computed before touching the server. If it comes back identical, it ran.</figcaption>
</figure>

And I repeated it **twice more, with different strings**, to rule out coincidence or
caching. One canary could be luck; three are not.

## Step 4: where is this running?

Once execution was proven, it was time to measure how far it reached. Carefully, touching
nothing:

```python
import os, socket
print(os.getuid())        # 0  -> root
print(socket.gethostname())
print(len(os.environ))    # process variables
```

The result: **uid 0 (root)**, inside a container on a production cluster, with network
reach to several dozen internal services and credentials sitting in the process
environment.

The code was not running in an isolated toy box. It ran as administrator
inside the company's internal network, with access to other services that should never be
reachable from the internet. From there, an attacker is not "chatting with a bot": **they
are inside**.

<div class="note" markdown="1">
**Where I stopped.** I read the user id, the hostname and counted how many environment
variables there were. I did **not** read their contents, did not move to any internal
service, did not touch data and left nothing installed. To demonstrate "I execute code as
root in production" that is more than enough; everything beyond it is intrusion, not
research.
</div>

## Why I reported it separately from the other bug

The entrance was the same: the token that could be minted with the key from the JavaScript
file. It might look like the same report. **It is not**, and arguing that properly was part
of the job:

| | The authentication bug | This one |
|---|---|---|
| **What it is** | You can get in without an account | There is a tool that executes code |
| **How it is fixed** | Rotating the key and binding the token to a user | Removing the tool from the agent |
| **If only the other is fixed** | — | Still exploitable **by any legitimate employee** |

That last point is the decisive argument: even if they fixed authentication tomorrow, any
employee with normal chat access could still run code as root in production. Two bugs, two
different fixes.

It is one thing for the front door to be open and another for there to
be a lever inside that blows up the building. Fixing the door does not remove the lever.

## Impact

<div class="impact" markdown="1">
**Impact.** Arbitrary code execution as **root** in a production container, reachable from
the internet and with no account required. From that position: reading the process
credentials, lateral movement to the visible internal services, and access to the data
those services hold. In practice, the worst possible outcome for an exposed application.
</div>
