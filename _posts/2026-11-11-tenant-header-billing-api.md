---
title:       "Reading any organisation's invoices through a client-controlled header"
summary:     "The gateway validated the token signature, but the billing service took the organisation identifier from an HTTP header the client could write. A test session could read the invoices, tax ID and IBANs of any other customer on the platform."
date:        2026-11-11 10:00:00 +0100
lang:        en
ref:         idor-tenant-header
permalink:   /en/writeups/tenant-header-billing-api/

severity:    high
cvss:        "8.6"
cvss_vector: "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:C/C:H/I:N/A:N"
cwe:         "CWE-639"
vuln_class:  "Access control"
target_type: "Multi-tenant REST API"
platform:    "Private program"
status:      "Fixed"
fixed:       "9 days"
reward:      "Rewarded"
tags:        [idor, bola, api, multi-tenant, authorization, headers]

takeaways:
  - "If an internal service accepts the tenant from a header, the edge is not authorising: it is only authenticating."
  - "Proprietary `X-*` headers that show up in JavaScript bundles are the best broken-authorisation lead there is."
  - "The negative control — the same request *without* the header — is what turns \"I saw a 200\" into a defensible report."
---

While reviewing a multi-tenant SaaS billing platform I found an object-level authorisation
flaw that let any registered user read the complete financial records of any other
organisation on the platform. The vector was not an identifier in the URL — that part was
properly controlled — but **a proprietary HTTP header the client could write freely**.

The issue was reported through the program's channel, fixed in nine days, and is published
here with their authorisation, with every identifier replaced by lab values.

## The signal

The web panel loaded its data through an API versioned under `/api/v2/`. Reading the
application's main bundle, I found the HTTP client the site itself uses:

```javascript
// app.4f1c9d.chunk.js — request interceptor (reformatted)
instance.interceptors.request.use((config) => {
  config.headers["Authorization"] = `Bearer ${session.accessToken}`;
  config.headers["X-Org-Context"]  = store.getState().org.activeId;   // ← this
  return config;
});
```

Two things stood out at once:

1. The organisation identifier travels **in a header**, not derived from the token.
2. Its value comes from client state (`store`) — something the browser, and therefore the
   attacker, fully controls.

An `X-*` header carrying a tenant identifier is, in my experience, the broken-authorisation
signal with the best cost/benefit ratio there is. It proves nothing on its own, but it
produces a very concrete hypothesis.

> **Hypothesis declared before testing:** the edge validates the JWT signature and assumes
> the organisation context has already been checked; the billing service uses the header as
> the source of truth and never cross-checks it against the user's memberships.
>
> *What confirms it:* a `200` with data from a tenant my account does not belong to.
> *What kills it:* a `403` for context mismatch, or a `200` with my own tenant's data
> (header ignored).

## Test environment

So that no real customer data was touched at any point, I registered **two organisations of
my own** in production using my own email addresses:

| Account | Organisation | Role | Use |
|---|---|---|---|
| `canary-a@…` | `4417` — *Lab Alpha* | Member | Attack origin |
| `canary-b@…` | `8831` — *Lab Bravo* | Owner | Target, with data I seeded |

In `Lab Bravo` I created two invoices with made-up but recognisable amounts and an IBAN.
That way, any data appearing in account A's response was traceable to my own lab and not to
a third party.

<div class="note" markdown="1">
Seeding your own canaries on both sides of the boundary is what lets you demonstrate impact
**without reading any real user's information**. The receiving team can verify the report
without having to audit whether customer data was exposed.
</div>

## Exploitation

From `canary-a`'s session (organisation `4417`), a request to organisation `8831`'s billing
endpoint, adding the header with the other tenant:

```http
GET /api/v2/organizations/8831/invoices HTTP/2
Host: api.example-target.tld
Authorization: Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6ImM4YTEi...
X-Org-Context: 8831
Accept: application/json
```

The response returned the other organisation's complete financial record:

```http
HTTP/2 200 OK
content-type: application/json; charset=utf-8

{
  "organization_id": 8831,
  "legal_name": "Lab Bravo S.L.",
  "tax_id": "B-8812****",
  "invoices": [
    {
      "number": "2026-0441",
      "total": 184250.00,
      "customer_email": "cfo@lab-bravo.invalid",
      "iban": "ES91 2100 **** **** 0418"
    }
  ]
}
```

<figure>
  <img src="{{ '/assets/img/writeups/idor-tenant/01-peticion-respuesta.svg' | relative_url }}"
       alt="Burp Repeater: request with tenant 4417's session and X-Org-Context 8831, responding 200 OK with tenant 8831's data">
  <figcaption>The session belongs to <code>4417</code>; the header points to <code>8831</code>. The API responds with <code>8831</code>'s data.</figcaption>
</figure>

The URL identifier and the header had to match, but **neither was checked against the
token**. Changing the pair to `(8832, 8832)`, `(8833, 8833)`… walked the whole platform;
identifiers are sequential, so enumerating them requires guessing nothing.

<div class="impact" markdown="1">
**Impact.** Any user with a free account could read, for any organisation on the platform:
legal name, tax ID, invoice history with amounts, billing contact emails and a partially
masked IBAN. That is exposure of third-party tax and financial data, with direct GDPR
implications for the operator and immediate value for fraud aimed at a finance department.
</div>

## Negative control

This is the step that decides whether there is a report at all. I repeated **exactly the
same request, changing one single thing**: removing the `X-Org-Context` header.

```http
GET /api/v2/organizations/8831/invoices HTTP/2
Host: api.example-target.tld
Authorization: Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6ImM4YTEi...
Accept: application/json
```

```http
HTTP/2 403 Forbidden

{ "error": "organization_scope_mismatch",
  "message": "Your session is not scoped to organization 8831." }
```

<figure>
  <img src="{{ '/assets/img/writeups/idor-tenant/02-control-negativo.svg' | relative_url }}"
       alt="The same request without the X-Org-Context header: the API responds 403 Forbidden with organization_scope_mismatch">
  <figcaption>Negative control: without the header the server <strong>does</strong> enforce authorisation. The resource was not public.</figcaption>
</figure>

This closes the two alternative explanations that would have invalidated the finding:

- It was **not** a public resource: without the header, authorisation exists and denies.
- It was **not** an effect of my own membership: my account is not a member of `8831`, and
  the error message says so itself.

The header does not *add* context: it **replaces** it.

## Root cause

<figure>
  <img src="{{ '/assets/img/writeups/idor-tenant/03-flujo-ataque.svg' | relative_url }}"
       alt="Diagram: the attacker sends the header, the gateway only validates the JWT signature, the billing service trusts the header and the database returns the other tenant">
  <figcaption>The edge authenticates; nobody authorises. The header crosses the architecture unchecked.</figcaption>
</figure>

The gap sits between two assumptions that were never written down in the same place:

- **The gateway** assumes its job is to verify the token is signed and not expired. It does
  that correctly.
- **The billing service** assumes that if a request reached it, the organisation context
  travelling with it was already validated at the edge.

Neither compares the requested tenant against the real memberships of the user signing the
token. The header existed for a legitimate reason — a user can belong to several
organisations and switch between them — but it was implemented as *input data* instead of
as *a preference to validate*.

## Remediation

What I recommended, in order of priority:

1. **Derive the tenant from the token, not from the request.** User memberships must be
   resolved server-side from the JWT's `sub`. If the header is kept for compatibility,
   treat it as a *preference*: validate that the value is in the user's organisation list
   and reject with `403` otherwise.
2. **Authorise in the service, not only at the edge.** The billing service must run its own
   membership check before querying the database; a compromised edge or internal lateral
   access must not be enough.
3. **Normalise the header at the perimeter.** The gateway should strip or overwrite any
   incoming `X-Org-Context`, so a client-supplied value never reaches the internal network.
4. **Detection.** Alert on requests where the requested tenant matches none of the `sub`'s
   memberships: on a healthy platform that event should be essentially non-existent.

The team shipped points 1 and 3 in nine days and confirmed point 2 for the following
release cycle.

## Timeline

| Date | Milestone |
|---|---|
| 2026-10-14 | Report submitted with proof of concept and negative control |
| 2026-10-14 | Acknowledged by the program |
| 2026-10-16 | Triaged as *High*, severity accepted unchanged |
| 2026-10-23 | Fix deployed and verified with the canary accounts |
| 2026-11-11 | Authorised publication of this writeup |
