# AgentCore Tracing Design - Evaluation Support

## Overview

This document describes the OpenTelemetry instrumentation added to the Knowledge Base proxy Lambda function to support [AgentCore Evaluations](https://aws.amazon.com/blogs/aws/amazon-bedrock-agentcore-adds-quality-evaluations-and-policy-controls-for-deploying-trusted-ai-agents/).

## Why Tracing is Needed

AgentCore Evaluations uses LLM-as-judge to score agent quality. The evaluators require access to trace data containing:

- **Request content**: User queries, parameters, filters
- **Response content**: LLM responses, retrieved documents, citations
- **Context**: User roles, session IDs, tool selections

While AgentCore Gateway auto-captures operational metrics (latency, token counts, tool names), **content fields require explicit instrumentation** to be available for evaluation.

## Built-in Evaluators Supported

| Evaluator | What It Measures | Trace Data Required |
|-----------|------------------|---------------------|
| Correctness | Factual accuracy | `gen_ai.completion.content` |
| Faithfulness | Grounded in sources | Response + `response.documents` |
| Helpfulness | User value | `request.query` + response |
| Harmfulness | Harmful content | Response text |
| Stereotyping | Generalizations | Response text |
| Tool Selection | Right tool chosen | `request.query` + `tool.name` |
| Tool Parameter | Correct params | `request.query` + `request.filters` |

## Custom Evaluators Enabled

| Evaluator | Purpose | Trace Data Required |
|-----------|---------|---------------------|
| Access Compliance | Respects metadata filters | `user.*` + `request.filters` + `response.documents` |
| Metadata Filter Accuracy | Correct filters applied | `request.filters` |
| Citation Accuracy | Sources attributed | Response + `response.citations` |

## Architecture

```
+---------------------------------------------------------------------+
|                    Lambda Function                                   |
|  +---------------------------------------------------------------+  |
|  |  ADOT SDK (OpenTelemetry)                                     |  |
|  |  - Auto-instruments boto3 calls                               |  |
|  |  - Exports traces to CloudWatch                               |  |
|  +---------------------------------------------------------------+  |
|                              |                                       |
|  +---------------------------v-----------------------------------+  |
|  |  tracing.py                                                   |  |
|  |  - trace_span() - Context manager for spans                   |  |
|  |  - set_request_attributes() - Query, filters                  |  |
|  |  - set_response_attributes() - Documents                      |  |
|  |  - set_generation_attributes() - LLM output, citations        |  |
|  |  - set_user_context() - Role, department, accessLevel         |  |
|  +---------------------------------------------------------------+  |
|                              |                                       |
|  +---------------------------v-----------------------------------+  |
|  |  knowledge_base_proxy.py                                      |  |
|  |                                                               |  |
|  |  handler()                                                    |  |
|  |    +-> Span: "mcp.tool_call"                                  |  |
|  |         +-> tool.name = "query_knowledge_base"                |  |
|  |         +-> session.id = "..."                                |  |
|  |         +-> user.* = context attributes                       |  |
|  |                                                               |  |
|  |  query_knowledge_base()                                       |  |
|  |    +-> Span: "knowledge_base.retrieve"                        |  |
|  |         +-> request.query = "..."                             |  |
|  |         +-> request.filters = {...}                           |  |
|  |         +-> response.document_count = N                       |  |
|  |         +-> response.documents = [...]                        |  |
|  |                                                               |  |
|  |  retrieve_and_generate()                                      |  |
|  |    +-> Span: "knowledge_base.rag"                             |  |
|  |         +-> request.query = "..."                             |  |
|  |         +-> gen_ai.completion.content = "..."                 |  |
|  |         +-> response.citations = [...]                        |  |
|  +---------------------------------------------------------------+  |
+---------------------------------------------------------------------+
                              |
                              v
+---------------------------------------------------------------------+
|                    CloudWatch (via ADOT Layer)                       |
|  +-----------------+  +-----------------+  +---------------------+  |
|  |   Traces        |  |   Metrics       |  |   Logs              |  |
|  |   (X-Ray)       |  |   (EMF)         |  |   (Structured)      |  |
|  +-----------------+  +-----------------+  +---------------------+  |
+---------------------------------------------------------------------+
                              |
                              v
+---------------------------------------------------------------------+
|                    AgentCore Evaluations                             |
|  +-----------------------------------------------------------------+|
|  |  Data Source: CloudWatch Log Group                              ||
|  |  Sampling: 10-20% (configurable)                                ||
|  |  Evaluators: Built-in + Custom                                  ||
|  +-----------------------------------------------------------------+|
+---------------------------------------------------------------------+
```

## Span Attributes Reference

### Main Handler Span: `mcp.tool_call`

| Attribute | Type | Description | Example |
|-----------|------|-------------|---------|
| `tool.name` | string | Tool being invoked | `"query_knowledge_base"` |
| `session.id` | string | Session identifier | `"sess-abc123"` |
| `user.role` | string | User's role (if provided) | `"seller"` |
| `user.department` | string | User's department | `"finance"` |
| `user.accessLevel` | string | Access level | `"internal"` |

### Retrieve Span: `knowledge_base.retrieve`

| Attribute | Type | Description | Example |
|-----------|------|-------------|---------|
| `request.query` | string | Search query | `"What is the refund policy?"` |
| `request.filters` | JSON string | Metadata filters applied | `{"equals":{"key":"marketplace","value":"US"}}` |
| `request.max_results` | int | Max results requested | `5` |
| `response.document_count` | int | Documents returned | `3` |
| `response.documents` | JSON string | Retrieved docs (truncated) | `[{"content":"...","score":0.85}]` |

### RAG Span: `knowledge_base.rag`

| Attribute | Type | Description | Example |
|-----------|------|-------------|---------|
| `request.query` | string | User question | `"How do I return a product?"` |
| `gen_ai.completion.content` | string | LLM response | `"To return a product..."` |
| `gen_ai.model` | string | Model used | `"claude-3-sonnet"` |
| `response.citation_count` | int | Number of citations | `4` |
| `response.citations` | JSON string | Citation details | `[{"location":"s3://...","content":"..."}]` |

## User Context Support

To enable the custom Access Compliance evaluator, callers can include user context:

```json
{
  "tool_name": "query_knowledge_base",
  "tool_input": {
    "query": "What are the seller fees?",
    "filter": {"equals": {"key": "marketplace", "value": "US"}}
  },
  "user_context": {
    "role": "seller",
    "department": "finance",
    "accessLevel": "internal",
    "allowedMarketplaces": ["US", "CA"]
  }
}
```

These are captured as `user.*` span attributes for evaluation.

## Deployment

### Lambda Layer

The function requires the AWS ADOT Lambda layer:

```
arn:aws:lambda:us-west-2:901920570463:layer:aws-otel-python-amd64-ver-1-24-0:1
```

This is automatically added when using `deploy_gateway.sh`.

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OTEL_SERVICE_NAME` | Yes | Service name for traces (`knowledgedb-mcp`) |
| `ENABLE_TRACING` | No | Set to `false` to disable (default: `true`) |

## Dependencies

Added to `agentcore/lambda/requirements.txt`:

```
aws-opentelemetry-distro>=0.6.0
opentelemetry-api>=1.20.0
opentelemetry-sdk>=1.20.0
opentelemetry-instrumentation-botocore>=0.44b0
```

## Setting Up Evaluations

1. **Deploy Lambda** with tracing enabled:
   ```bash
   cd agentcore/scripts
   ./deploy_gateway.sh
   ```

2. **Enable Observability** on the AgentCore Gateway (console or CLI)

3. **Create Online Evaluation** in AgentCore Console:
   - Data source: CloudWatch log group `/aws/lambda/KnowledgeBaseProxy`
   - Select built-in evaluators: Correctness, Faithfulness, Helpfulness
   - Set sampling rate: 10-20% for production

4. **Add Custom Evaluators** (optional):
   - Access Compliance: Verify response respects metadata filters
   - Citation Accuracy: Verify sources are attributed

5. **Configure Alarms** in CloudWatch for threshold breaches

## Alerting Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| Faithfulness | < 0.85 (8hr avg) | < 0.75 (1hr avg) |
| Correctness | < 0.80 (8hr avg) | < 0.70 (1hr avg) |
| Helpfulness | < 0.75 (24hr avg) | < 0.60 (4hr avg) |
| Access Compliance | < 0.95 (1hr avg) | < 0.90 (15min avg) |

## Files Modified

| File | Changes |
|------|---------|
| `agentcore/lambda/requirements.txt` | Added ADOT/OpenTelemetry dependencies |
| `agentcore/lambda/tracing.py` | New - tracing utilities module |
| `agentcore/lambda/knowledge_base_proxy.py` | Added tracing instrumentation |
| `agentcore/scripts/deploy_gateway.sh` | Added ADOT layer configuration |

## References

- [AWS Blog: AgentCore Evaluations](https://aws.amazon.com/blogs/aws/amazon-bedrock-agentcore-adds-quality-evaluations-and-policy-controls-for-deploying-trusted-ai-agents/)
- [AgentCore Observability Configuration](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability-configure.html)
- [ADOT Lambda Layer](https://aws-otel.github.io/docs/getting-started/lambda)
- [OpenTelemetry Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/)
- [Evaluation Design Doc](https://github.com/JKevinXu/eval/blob/main/docs/agentcore-evaluation-design.md)

---

**Status**: Implemented | **Date**: January 4, 2026

