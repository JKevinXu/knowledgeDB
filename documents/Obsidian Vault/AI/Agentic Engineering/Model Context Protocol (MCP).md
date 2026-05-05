---
title: Model Context Protocol (MCP)
created: 2026-05-05
updated: 2026-05-05
type: concept
tags:
  - ai
  - agents
  - mcp
  - mcp-apps
  - agentic-engineering
  - agent-native-infrastructure
  - deployment
sources:
  - https://modelcontextprotocol.io/extensions/apps/overview
  - https://modelcontextprotocol.io/extensions/apps/build
  - https://github.com/JKevinXu/mcp-app-server
  - https://mcp-app-server-psi.vercel.app
---

# Model Context Protocol (MCP)

MCP is a protocol for connecting AI agents to tools, resources, prompts, and interactive application surfaces through a standardized client-server interface.

In [[Agentic Engineering]], MCP matters because it turns integrations from one-off agent hacks into reusable infrastructure. A well-built MCP server becomes a stable capability boundary: the agent can discover tools, call them, read resources, and sometimes render or interact with app UIs without the agent runtime needing custom code for every integration.

## One-line thesis

MCP is becoming the plugin/runtime layer for agent-native software: tools expose actions, resources expose context, and MCP Apps expose interactive human-facing surfaces that can travel with the tool.

## Mental model

Think of MCP as four layers:

1. Server
   - Owns capabilities.
   - Registers tools, resources, and prompts.
   - Implements transport-specific lifecycle behavior.

2. Transport
   - Moves JSON-RPC messages between client and server.
   - Common modes:
     - `stdio` for local desktop/CLI integrations.
     - Streamable HTTP for remote hosted integrations.

3. Capabilities
   - `tools/list` and `tools/call` expose actions.
   - `resources/list` and `resources/read` expose addressable context.
   - Prompts can expose reusable instruction templates.

4. Host/client experience
   - The client decides how to present tools, resources, and MCP Apps.
   - Some clients only call tools.
   - MCP Apps-aware clients can render interactive HTML app resources.

## Why MCP is agentic engineering infrastructure

MCP separates three concerns that are often tangled in agent projects:

- Agent reasoning: what should be done?
- Capability execution: what external system performs the action?
- Integration surface: how does a user or app interact with that capability?

This separation makes agent systems easier to verify and maintain:

- The server can be smoke-tested independently of the agent.
- The same server can support multiple clients: Hermes, Claude Desktop-like hosts, Codex-style CLIs, browser-capable app hosts, or future agents.
- Tools/resources become versioned software artifacts instead of ephemeral prompt glue.
- Security boundaries become clearer: auth, CORS, endpoint exposure, and secret handling live at the server boundary.

Related: [[Agent-Native Infrastructure]], [[Productionization]], [[Verifiability in AI Automation]].

## Core server pattern

A useful MCP server should expose a small set of intentional capabilities rather than trying to mirror an entire backend API.

For the remote MCP Apps project, the server pattern was:

- Local repo: `/Users/kx/mcp-app-server`
- GitHub repo: https://github.com/JKevinXu/mcp-app-server
- Runtime: TypeScript + Node.js
- MCP SDK: `@modelcontextprotocol/sdk`
- MCP Apps extension: `@modelcontextprotocol/ext-apps`
- Local transport: `stdio`
- Remote transport: Streamable HTTP
- Remote MCP endpoint: `/mcp`
- Health endpoint: `/health`
- Metadata endpoint: `/`
- Production deployment: https://mcp-app-server-psi.vercel.app

The important design point is not the weather demo itself. The reusable pattern is a server that can be run locally over `stdio`, hosted remotely over HTTP, tested through full MCP lifecycle smoke tests, and connected to multiple agent clients.

## Streamable HTTP lesson: sessions are real state

A key implementation lesson: Streamable HTTP MCP is not just "POST JSON to `/mcp`."

A manual HTTP test exposed that creating a fresh `StreamableHTTPServerTransport` per request breaks the lifecycle after `initialize`. The server needs to preserve the transport/session relationship across requests.

Reusable pattern:

1. Client sends `initialize` to `/mcp`.
2. Server creates a `StreamableHTTPServerTransport`.
3. Server returns an `Mcp-Session-Id`.
4. Server stores the transport in a `Map` keyed by session ID.
5. Later requests reuse the same transport for:
   - `notifications/initialized`
   - `tools/list`
   - `tools/call`
   - `resources/read`
6. Server cleans up the map entry when the transport closes.

Engineering lesson: a green `/health` check is almost meaningless for MCP correctness. Verify the full lifecycle: initialize, initialized notification, tool listing, tool call, and resource read.

## MCP Apps

MCP Apps extend MCP from tool calling into embedded application experiences.

A minimal MCP App needs more than a static HTML file:

- A tool that advertises or is associated with an app experience.
- A registered app resource with a stable URI.
- A resource response with MCP Apps-compatible MIME type.
- A client/host that knows how to render or use the app resource.

In the project MVP:

- Tool: `weather_dashboard`
- App resource: `ui://weather-dashboard/mcp-app.html`
- MIME type: `text/html;profile=mcp-app`
- UI title: `Weather Dashboard`
- UI includes: `Refresh forecast`
- Frontend build: Vite + `vite-plugin-singlefile`
- Bundled app output: `dist/app/mcp-app.html`

The reusable MCP Apps pattern is:

1. Register the tool.
2. Register the app HTML as an MCP resource.
3. Bundle frontend assets into a single HTML resource when portability matters.
4. Return structured tool data that the app can render.
5. Smoke-test the app resource through `resources/read`, not only through a browser.

## Testing strategy

The project converged on a practical verification ladder:

```bash
npm run typecheck
npm run build
npm run smoke:stdio
npm run smoke:http
npm run smoke:apps
npm run smoke:remote
```

Each layer catches a different class of problem:

- `typecheck`: TypeScript/API contract errors.
- `build`: server and app bundling errors.
- `smoke:stdio`: local MCP client compatibility.
- `smoke:http`: Streamable HTTP initialize/session/tool flow.
- `smoke:apps`: MCP App resource and MIME behavior.
- `smoke:remote`: public URL metadata, CORS, optional auth, and remote-style HTTP behavior.

Smoke tests should assert behavior, not implementation details. For example, app HTML tests should check stable visible UI strings like `Weather Dashboard` and `Refresh forecast`, not raw source imports that may disappear after Vite bundling/minification.

## Remote MCP server checklist

A remote MCP server should include:

- `GET /health` for operational checks.
- `GET /` for service metadata and human/browser inspection.
- `POST /mcp` for Streamable HTTP MCP traffic.
- `OPTIONS /mcp` for browser preflight when needed.
- `PUBLIC_URL` or host-derived public endpoint metadata.
- Optional bearer auth, e.g. `MCP_BEARER_TOKEN`.
- Configurable CORS, e.g. `MCP_CORS_ORIGIN`.
- Safe `.env.example` with placeholders only.
- CI that runs lifecycle smoke tests.
- Documentation for local, hosted, and agent-client use.

A useful metadata response should answer:

- What is this server?
- What version is it?
- Where is the MCP endpoint?
- Is auth required?
- What app resource is available?
- What transport is expected?

## Deployment lesson: Vercel works for demos, but state matters

The server was deployed to Vercel by refactoring the Express app into an importable factory and adding a serverless adapter:

- `createHttpApp()` in `src/index.ts`
- `api/index.ts` Vercel handler
- `vercel.json` rewrites all paths to the handler
- `VERCEL_URL` fallback for public URL metadata

Production endpoint:

- https://mcp-app-server-psi.vercel.app
- https://mcp-app-server-psi.vercel.app/mcp
- https://mcp-app-server-psi.vercel.app/health

This is good for a working remote MVP. It is not automatically ideal for production-scale MCP sessions.

Why:

- The sample Streamable HTTP implementation stores session transports in process memory.
- Serverless functions can cold-start, recycle, or scale horizontally.
- A later request with the same MCP session ID may land on a different instance that lacks the in-memory session map.

Production options:

- Use a long-running Node/Docker host such as Fly.io, Render, Railway, or a container platform.
- Add shared session/session-affinity storage if staying on serverless.
- Evaluate stateless MCP patterns only if the target client/server flow supports them.

## Client support reality

MCP support and MCP Apps support are different.

A client may support:

- Connecting to MCP servers.
- Listing and calling tools.
- Reading resources.
- Rendering interactive MCP Apps.

These are not the same capability.

Practical examples from the project:

- Hermes can connect to the local MCP server and discover/call `echo`, `weather_dashboard`, and `server_info`.
- A remote Streamable HTTP endpoint can be tested by raw JSON-RPC calls and browser-console fetches.
- Codex-style terminal clients may support MCP tool/resource access but are not guaranteed to render an interactive HTML MCP App UI.
- A browser-like or MCP Apps-aware host is needed for the full visual app experience.

## Security lessons

Remote MCP servers are public integration surfaces. Treat them like APIs.

Minimum security posture:

- Do not commit local client config if it may contain secrets.
- Do not preserve deployment tokens in notes or repos.
- Use placeholder-only `.env.example` files.
- Add optional bearer-token auth for remote endpoints.
- Configure CORS intentionally rather than accidentally.
- Rotate any token pasted into an agent session after use.
- Keep project metadata such as `.vercel` out of git.

For this project, the Vercel token used for deployment was not recorded in the knowledge base. It should be treated as compromised-by-chat and rotated/revoked.

## Reusable engineering lessons

1. Build the smallest complete vertical slice: server, transport, tool, resource, app UI, tests, CI, deployment.
2. Test MCP lifecycle behavior, not only process health.
3. For Streamable HTTP, session reuse is a first-class correctness requirement.
4. MCP Apps require server-side resource registration and the right MIME type; a static page alone is not an MCP App.
5. Bundle MCP App UI into a single HTML resource when portability is more important than frontend complexity.
6. Remote MCP needs product-grade API concerns: metadata, auth, CORS, public URLs, and deployment docs.
7. Serverless is convenient for demos, but production MCP sessions may prefer long-running infrastructure.
8. Tool clients and app-rendering clients should be evaluated separately.
9. Agent-created infrastructure should be written back into a durable wiki so future work starts from learned patterns rather than chat transcript archaeology.

## Project reference implementation

The current reference implementation is the TypeScript Weather Dashboard MCP Apps server:

- GitHub: https://github.com/JKevinXu/mcp-app-server
- Vercel: https://mcp-app-server-psi.vercel.app
- Latest noted commit: `05af2ec`
- Important commits:
  - `27662a0 feat: add MCP Apps MVP`
  - `68120c6 feat: make MCP Apps server remote-ready`
  - `7365820 feat: add Vercel deployment support`
  - `05af2ec chore: ignore Vercel project metadata`

Useful commands:

```bash
cd /Users/kx/mcp-app-server
npm run typecheck
npm run build
npm run smoke:stdio
npm run smoke:http
npm run smoke:apps
npm run smoke:remote
```

Hermes local config shape:

```yaml
mcp_servers:
  mcp_app_server:
    url: "http://127.0.0.1:3099/mcp"
    timeout: 120
    connect_timeout: 30
```

Hermes remote config shape:

```yaml
mcp_servers:
  vercel_mcp_app_server:
    url: "https://mcp-app-server-psi.vercel.app/mcp"
    timeout: 120
    connect_timeout: 30
```

## Related

- [[Agentic Engineering]]
- [[Agent-Native Infrastructure]]
- [[Productionization]]
- [[Verifiability in AI Automation]]
- [[LLM Knowledge Bases]]
- [[Obsidian as an LLM Wiki IDE]]

## References

- MCP Apps overview: https://modelcontextprotocol.io/extensions/apps/overview
- MCP Apps build guide: https://modelcontextprotocol.io/extensions/apps/build
- Reference repo: https://github.com/JKevinXu/mcp-app-server
- Reference deployment: https://mcp-app-server-psi.vercel.app
