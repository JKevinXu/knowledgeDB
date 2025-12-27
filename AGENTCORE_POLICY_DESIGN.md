# AgentCore Policy - Design Document

## Overview

AgentCore Policy enforces security controls over AI agent tool calls. Policies are written in **Cedar** and evaluated at the Gateway before each tool invocation.

```
MCP Client → Gateway → Policy Engine → Lambda (if permitted)
                           ↓
                     DENY → Error
```

## Basic Use Case

**Goal**: Control access to Knowledge Base tools with ability to emergency shutdown.

### Policies (v1 - Minimal)

| Policy | Rule | Purpose |
|--------|------|---------|
| Emergency Shutdown | `forbid(principal, action, resource)` | Block all access instantly |
| IAM Full Access | `permit(principal is IAMUser, ...)` | Allow backend/admin access |
| OAuth User Access | `permit(principal is OAuthUser, ...)` | Allow external users |

### Cedar Policy File

```cedar
// Emergency Shutdown (uncomment to activate)
// forbid(principal, action, resource);

// Allow IAM users
permit(
    principal is AgentCore::IAMUser,
    action,
    resource
);

// Allow OAuth users  
permit(
    principal is AgentCore::OAuthUser,
    action,
    resource
);
```

## Implementation

### Step 1: Create Policy Engine

```bash
aws bedrock-agentcore-control create-policy-engine \
  --name KnowledgeBasePolicyEngine \
  --region us-west-2
```

### Step 2: Add Policy

```bash
aws bedrock-agentcore-control create-policy \
  --policy-engine-id <POLICY_ENGINE_ID> \
  --name BasicAccessPolicy \
  --policy-type CEDAR \
  --policy-content file://agentcore/policies/knowledge_base_policies.cedar
```

### Step 3: Attach to Gateway

```bash
aws bedrock-agentcore-control update-gateway \
  --gateway-identifier knowledgebasegatewayoauth2-pf7rmcexrm \
  --policy-engine-id <POLICY_ENGINE_ID> \
  --policy-enforcement-mode LOG
```

### Step 4: Test & Enforce

1. Make test requests while in `LOG` mode
2. Check CloudWatch for policy decisions
3. Switch to `ENFORCE` mode when ready

## Emergency Shutdown

To immediately block all access:

1. Edit `knowledge_base_policies.cedar`
2. Uncomment the forbid line
3. Re-deploy policy

```cedar
// Activate this to block everything
forbid(principal, action, resource)
advice { "System is in maintenance mode." };
```

## Future Enhancements

When needed, add policies for:
- Marketplace access control (CN vs US)
- Token limits per user tier
- Query content filtering
- Rate limiting

---

**Status**: Draft | **Date**: December 27, 2025
