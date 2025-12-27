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
// POLICY 3: Allow OAuth Users to Query
// ----------------------------------------------------------------------------
// External users authenticated via OAuth can use all tools.

permit(
    principal is AgentCore::OAuthUser,
    action,
    resource
);
