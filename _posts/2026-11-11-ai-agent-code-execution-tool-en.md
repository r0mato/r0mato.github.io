---
title:       "I asked the chatbot to run code and it did: RCE in production through an AI agent"
summary:     "An internal conversational assistant had, among its tools, one that executed Python on the server. Anyone could ask for it. I proved it with a cryptographic canary, because \"the model made that up\" is the objection that kills these reports."
date:        2026-11-11 20:00:00 +0100
lang:        en
ref:         rce-agente-ia-tool
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

<div class="plain" markdown="1">
**In plain words:** a chatbot is someone on the phone giving you advice. An agent is
someone on the phone **with the keys to your house**. The conversation is just as harmless;
what changes is what they can do while talking to you.

That is why, when auditing an AI assistant, the question is not "can I make it say silly
things?". The question is **"what tools does it have and who can ask it to use them?"**.
</div>

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

<div class="plain" markdown="1">
**In plain words:** IPython is an interactive Python interpreter. A tool called "run an
IPython cell" means, literally, **"run the Python code you are given"**. Inside an assistant
anyone can write to.
</div>

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

<div class="plain" markdown="1">
**In plain words:** a hash is a fingerprint of a piece of text. Change one letter and the
fingerprint changes completely. There is no way to "deduce" it: you have to compute it.

A language model **cannot compute hashes**. It can recite famous hashes it saw during
training, but it cannot produce one for a string I just invented. If the server returns
exactly the same fingerprint I computed on my laptop, there is only one explanation: **it
really ran the code**.
</div>

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

<div class="plain" markdown="1">
**In plain words:** the code was not running in an isolated toy box. It ran as administrator
inside the company's internal network, with access to other services that should never be
reachable from the internet. From there, an attacker is not "chatting with a bot": **they
are inside**.
</div>

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

<div class="plain" markdown="1">
**In plain words:** it is one thing for the front door to be open and another for there to
be a lever inside that blows up the building. Fixing the door does not remove the lever.
</div>

## The negative control

| What I tried | What happened | What it rules out |
|---|---|---|
| Asking for the hash **without** invoking the tool | The model returns an **incorrect** hash | That the model could compute it: the proof is the execution |
| Same canary, **different** string | Returns the correct hash for the new one | Caching or a memorised answer |
| Repeating from another session and another container | Same behaviour | That it was an odd state of one particular instance |
| Asking without a token | `401` | That the endpoint was open by design |

<div class="plain" markdown="1">
**In plain words:** the first row is the key. When I ask for the hash **without** the tool,
the model invents it and gets it wrong. When I ask it to use the tool, it gets it right.
That difference proves what is getting it right is not the model: it is the Python
interpreter behind it.
</div>

## Impact

<div class="impact" markdown="1">
**Impact.** Arbitrary code execution as **root** in a production container, reachable from
the internet and with no account required. From that position: reading the process
credentials, lateral movement to the visible internal services, and access to the data
those services hold. In practice, the worst possible outcome for an exposed application.
</div>

## The fix

1. **Remove any code-executing tool from the agent.** If it cannot be removed because it is
   part of the product, isolate it: ephemeral container, no network, no credentials,
   unprivileged user, CPU and memory limits, and no host mounts.
2. **Do not run as root.** Ever, but least of all something interpreting user input.
3. **Authorise per tool**, not just per conversation: whoever can chat should not, by that
   fact alone, be able to invoke anything in the catalogue.
4. **Log every invocation** with who, which tool and which arguments. In this case there was
   no way to know whether anyone had used it before me, which is the question every company
   asks after a report like this.
5. And the obvious one: fix the front door too.

## How to audit an AI agent

A short script you can follow on any assistant within scope:

1. **Ask it what tools it has.** It is surprising how often it lists them.
2. **Look for the dangerous ones by name:** anything with `exec`, `run`, `shell`, `code`,
   `python`, `sql`, `query`, `http`, `fetch`, `file`, `read`, `write`.
3. **Check who can invoke them.** Do you need to be an administrator? Do you need an account
   at all?
4. **If it executes something, prove it with a cryptographic canary.** Never with output the
   model could have invented.
5. **Measure the environment with the minimum:** user, host, network. And stop there.

<div class="note" markdown="1">
**What is NOT a finding.** Getting the assistant to say something outrageous, write
something offensive or recite its system prompt **is not a vulnerability** on its own.
Without secrets inside, without a tool behind it and without someone else's data, it is an
informative at best. What gets paid is what the **tools, data and identity** layer allows —
not what the model says.
</div>
