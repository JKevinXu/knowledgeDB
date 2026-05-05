---
title: Agentic Engineering
created: 2026-04-30
updated: 2026-04-30
type: concept
tags: [ai, agents, engineering, software-development]
sources:
  - [[Andrej Karpathy - From Vibe Coding to Agentic Engineering]]
  - [[Koshy John - AI Should Elevate Your Thinking Not Replace It]]
  - [[Model Context Protocol (MCP)]]
---

# Agentic Engineering

Agentic engineering is the discipline of using AI agents to move faster while preserving professional software quality: correctness, security, maintainability, architecture, and product taste.

It differs from [[Vibe Coding]]: vibe coding raises the floor by letting more people build software; agentic engineering tries to raise the ceiling without dropping the bar.

## Operating principles

- Humans own the spec, design, architecture, taste, and final responsibility.
- Agents execute large chunks, recall API details, generate code, test, debug, and explore alternatives.
- Verification is central: tests, type checks, security scans, adversarial review, and concrete acceptance criteria.
- Treat agents as powerful interns: useful, fast, and fallible.

## Risks

- Security vulnerabilities hidden behind working demos.
- Bloat, copy-paste, brittle abstractions, and code that works but is hard to maintain.
- Design mistakes that humans should catch, such as correlating payments and accounts by email instead of stable user IDs.

## Human judgment and ownership

Koshy John’s “AI should elevate your thinking, not replace it” adds a complementary warning: agentic engineering fails when AI is used to simulate competence rather than build leverage. The engineer should still understand, defend, and verify what agents produce. Good agent use shifts attention upward to problem framing, tradeoffs, risks, and clarity; bad agent use hides shallow thinking behind polished output.

Related: [[Software 3.0]], [[Verifiability in AI Automation]], [[Jagged Intelligence]], [[Agent-Native Infrastructure]], [[AI-Augmented Thinking]], [[Engineering Judgment]].

## Source note: MCP as agent-native infrastructure

[[Model Context Protocol (MCP)]] adds a concrete integration-layer lesson: agentic engineering needs stable capability boundaries, not just clever prompts. MCP servers package tools, resources, and sometimes interactive MCP Apps behind a protocol boundary that can be tested, versioned, deployed, and reused across clients. The remote MCP Apps server project showed that production-quality agent infrastructure requires the same engineering habits as ordinary backend systems: lifecycle smoke tests, session handling, auth/CORS controls, public metadata, CI, deployment docs, and secret hygiene. Related: [[Agent-Native Infrastructure]], [[Productionization]], [[Verifiability in AI Automation]].

## Source note: Musk / Fridman on production-grade real-world AI

[[Lex Fridman - Elon Musk on SpaceX Tesla Autopilot Robotics and AI]] adds a concrete production example: Tesla Autopilot is not just a model, but a full engineering loop of sensors, custom compilers, raw photon pipelines, auto-labeling, surround-video training, intervention metrics, regulator proof, and deployment feedback. It reinforces that [[Agentic Engineering]] is closer to productionizing a safety-critical system than prompting a one-off demo. Related: [[Productionization]], [[Real-World AI]], [[Embodied AI]].
