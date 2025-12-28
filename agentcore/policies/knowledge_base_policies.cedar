// ============================================================================
// Knowledge Base MCP Gateway - Basic Policies (v1)
// ============================================================================
// Simplified policy set for initial deployment.
// Start with these basics, then add complexity as needed.
// ============================================================================

// ----------------------------------------------------------------------------
// POLICY 1: Emergency Shutdown (Disabled by default)
// ----------------------------------------------------------------------------
// Uncomment to immediately block ALL access during incidents.
//
// forbid(principal, action, resource)
// advice { "System is in maintenance mode." };

// ----------------------------------------------------------------------------
// POLICY 2: Allow IAM Users Full Access
// ----------------------------------------------------------------------------
// Internal/backend access via IAM authentication - always permitted.

permit(
    principal is AgentCore::IAMUser,
    action,
    resource
);

// ----------------------------------------------------------------------------
// POLICY 3: Block suspended users
// ----------------------------------------------------------------------------
// Users with "suspended" tag are denied access.

forbid(
    principal is AgentCore::OAuthUser,
    action,
    resource
)
when { principal.hasTag("suspended") };

// ----------------------------------------------------------------------------
// POLICY 4: Limit max_tokens to 2048
// ----------------------------------------------------------------------------
// Prevent excessive token usage (cost control).

forbid(
    principal is AgentCore::OAuthUser,
    action == AgentCore::Action::"KnowledgeBaseProxyTarget___retrieve_and_generate",
    resource
)
when { context.toolInput.max_tokens > 2048 }
advice { "max_tokens cannot exceed 2048" };

// ----------------------------------------------------------------------------
// POLICY 5: Allow OAuth Users to Query
// ----------------------------------------------------------------------------
// External users authenticated via OAuth can use all tools.

permit(
    principal is AgentCore::OAuthUser,
    action,
    resource
);
