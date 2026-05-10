---
title: Agentic Services Protocol ASP Server Landscape
created: 2026-05-10
updated: 2026-05-10
type: source-summary
tags:
  - ai/agentic-engineering
  - protocols/asp
  - protocols/mcp
  - agent-native-infrastructure
sources:
  - https://github.com/ProsusAI/agentic-services-protocol
  - https://github.com/ProsusAI/asp-samples
  - https://github.com/JKevinXu/asp-sample-agent
  - https://kiro.dev/docs/mcp/
---

# Agentic Services Protocol ASP Server Landscape

## One-line thesis

Agentic Services Protocol (ASP) is currently closer to an early protocol plus reference-implementation ecosystem than a mature commercial server product category.

## Why this matters

ASP tries to define a service-transaction interface for agents: discovery, catalog browsing, checkout, order tracking, streaming updates, personalization, and reviews. This is a different niche from [[Model Context Protocol (MCP)]], which mainly exposes tools/resources/prompts to agents. ASP is about making real-world services purchasable and trackable by agents.

In [[Agent-Native Infrastructure]] terms:

- MCP answers: “What tools/context can this agent call?”
- ASP answers: “What service can this agent discover, order, and track end-to-end?”

## Source context and validation

Findings are based on remote inspection on 2026-05-10:

- GitHub search for `"Agentic Services Protocol"`, `"Agentic Services Protocol" "ASP" "server"`, `"Agentic Services Protocol" "ASP" server product`, and related queries.
- Remote README inspection for:
  - `ProsusAI/agentic-services-protocol`
  - `ProsusAI/asp-samples`
- Kiro docs inspection for MCP/spec/hook capabilities, especially `https://kiro.dev/docs/mcp/`.
- Local project work in `JKevinXu/asp-sample-agent` / `/Users/kx/ws/asp-sample-agent-repo`, which implements a small ASP client and mock ASP server demo.

## Current public artifacts

### 1. ProsusAI/agentic-services-protocol

GitHub: https://github.com/ProsusAI/agentic-services-protocol

This is the main ASP specification repository. It defines ASP as an open protocol for end-to-end agent-to-service transactions, including:

- provider discovery
- catalog browsing
- checkout / fulfillment
- order tracking
- live streaming
- personalization
- reviews

The README describes ASP as compatible with Google UCP-style checkout flows, extended for live services such as food delivery, ride hailing, and travel.

Repository shape:

- source schemas
- generated published schemas
- generated TypeScript / Python models
- documentation
- optional vertical domain profiles such as food delivery, ride hailing, and travel

Interpretation: this is a protocol/specification repo, not a hosted ASP server product.

### 2. ProsusAI/asp-samples

GitHub: https://github.com/ProsusAI/asp-samples

This is currently the closest public implementation of ASP servers. It is a reference/demo repository, not a commercial product.

It includes independent domain samples:

| Domain | Server role | Client role |
|---|---|---|
| Food Delivery | ASP server for restaurants, menus, modifiers, ordering, tracking | AI client agent with chat UI |
| Ride Hailing | ASP server for ride providers, vehicles, booking, tracking | AI client agent |
| Travel Booking | ASP server for accommodations, room comparison, reservation, status | AI client agent |

Representative architecture from the README:

```text
Browser UI -> Client Agent -> ASP Server
                       /.well-known/asp
                       /discovery/search
                       /catalog/{id}/catalog
                       /checkouts
                       /orders/{id}/tracking
                       /orders/{id}/tracking/stream
                       /personalization/*
                       /reviews/*
                       /catalog/reorder
```

Key design distinction:

- ASP Server = merchant/service platform, pure protocol API, no chat logic.
- Client Agent = consumer assistant that discovers capabilities and calls ASP endpoints.

Interpretation: useful as a server reference implementation and testbed, but not a packaged framework or product.

### 3. JKevinXu/asp-sample-agent

GitHub: https://github.com/JKevinXu/asp-sample-agent
Local path: `/Users/kx/ws/asp-sample-agent-repo`

This is a small local sample created to understand and test ASP mechanics. It includes:

- Python ASP client agent
- deterministic rule-based agent flow, no LLM key required
- FastAPI mock ASP provider
- Typer CLI
- browser UI at `/ui`
- tests and GitHub Actions CI

Implemented demo flow:

```text
GET  /.well-known/asp
POST /discovery/search
GET  /catalog/{provider_id}/catalog
POST /checkouts
POST /orders
GET  /orders/{order_id}/tracking
```

Useful as a compact learning harness, not a production ASP server.

## Product landscape answer

No clear public commercial/off-the-shelf “ASP server product” was found.

Current landscape:

| Category | Public example | Maturity |
|---|---|---|
| Protocol/spec | `ProsusAI/agentic-services-protocol` | Early but concrete |
| Reference servers | `ProsusAI/asp-samples` | Demo/reference implementation |
| Minimal learning harness | `JKevinXu/asp-sample-agent` | Local educational sample |
| Commercial hosted ASP server | None found | Not yet visible |
| ASP server framework | None found | Opportunity area |

## Can Codex be an ASP server?

Codex does not appear to natively expose ASP endpoints. It is primarily a terminal coding agent.

But Codex can be wrapped behind an ASP server:

```text
ASP client
  -> ASP wrapper server
    -> Codex CLI / coding agent process
      -> git repo / filesystem / tests / PR
```

Possible mapping:

- `/.well-known/asp`: advertise a software-development service provider
- `/discovery/search`: list coding services such as bug fix, feature build, PR review
- `/catalog/{provider_id}/catalog`: task templates and service levels
- `/checkouts`: validate repo, branch, permissions, task, timeout, sandbox mode
- `/orders`: start `codex exec ...`
- `/orders/{order_id}/tracking`: report queued/running/tests/pushed/failed/completed
- tracking stream: stream Codex logs

Interpretation: Codex can be a fulfillment engine behind ASP, but is not itself an ASP server.

## Can Kiro be an ASP server?

Kiro does not appear to natively expose ASP endpoints either.

Kiro publicly documents:

- spec-driven development
- agent hooks
- conversational coding
- MCP server integration

Kiro can consume MCP servers, and its docs describe MCP as a way for Kiro to communicate with external servers that provide tools, prompts, resources, and context. That is not the same as Kiro acting as an ASP server.

Possible wrapper model:

```text
ASP client
  -> ASP wrapper server
    -> Kiro automation layer
      -> Kiro workspace / specs / hooks / git repo
```

Main blocker: Kiro is primarily an IDE. A robust ASP wrapper would need a stable headless API, CLI, or supported automation interface. Desktop automation would be fragile and should be avoided for production.

Interpretation: Kiro can inspire an ASP-style software-development service, but it is not currently an ASP server product.

## Implementation pattern for a future ASP server framework

A useful ASP server product/framework would likely provide:

1. Protocol surface
   - `/.well-known/asp` generator
   - capability declarations
   - versioning and domain profiles

2. Domain modules
   - discovery
   - catalog
   - fulfillment / checkout
   - order lifecycle
   - tracking and streaming
   - reviews and personalization

3. Developer ergonomics
   - FastAPI / Node adapters
   - schema validation from ASP JSON Schemas
   - generated Pydantic / TypeScript types
   - conformance tests
   - local protocol inspector

4. Production concerns
   - auth and permissions
   - idempotency keys
   - audit logs
   - payment / UCP integration
   - webhook delivery
   - retry semantics
   - sandbox/test mode

5. Agent test harness
   - reference client agent
   - transcript replay
   - contract tests
   - failure-mode simulations

## Practical takeaway

ASP is worth tracking because it targets an important missing layer: agent-native service commerce and fulfillment. But adoption is early. Today, the best way to learn ASP is to inspect the Prosus reference implementations and build small wrappers or mock servers.

For software-agent use cases such as Codex or Kiro, ASP is not a native interface yet. The viable approach is a wrapper server that turns coding tasks into ASP-style discoverable, orderable, trackable services.

## Open questions

- Will ASP remain focused on real-world service marketplaces, or expand into digital labor / coding services?
- Will commercial platforms expose ASP endpoints directly?
- Will ASP and MCP converge, or remain complementary layers?
- What auth/payment standard will ASP implementations actually use in production?
- Is there enough demand for an “ASP server framework” before more clients support the protocol?

## Related

- [[Agentic Engineering]]
- [[Agent-Native Infrastructure]]
- [[Model Context Protocol (MCP)]]
- [[Verifiability in AI Automation]]
- [[Productionization]]

## References

- ProsusAI Agentic Services Protocol: https://github.com/ProsusAI/agentic-services-protocol
- ProsusAI ASP samples: https://github.com/ProsusAI/asp-samples
- Local/user ASP sample agent: https://github.com/JKevinXu/asp-sample-agent
- Kiro MCP docs: https://kiro.dev/docs/mcp/
