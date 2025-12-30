# AgentCore Evaluations - Design Document

## Overview

AgentCore Evaluations is a managed service that assesses AI agent performance through automated quality scoring. It monitors agent interactions, applies evaluators (LLM-as-judge), and publishes metrics to CloudWatch.

```
Agent Traces → Evaluators → Scores → CloudWatch → Alerts
```

## Evaluation Types

| Type | Description | Use Case |
|------|-------------|----------|
| **On-Demand** | Manual, one-time assessment | Development, testing, debugging |
| **Online** | Continuous real-time monitoring | Production monitoring |

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Agent (Knowledge Base)                        │
│                                                                      │
│  User Query → Tool Calls → Response                                 │
│       ↓                                                              │
│  OpenTelemetry Traces                                               │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    AgentCore Evaluations                             │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ Evaluation Configuration                                        ││
│  │  • Data Source: CloudWatch Log Group / Agent Endpoint           ││
│  │  • Sampling Rate: 10%                                           ││
│  │  • Evaluators: [correctness, helpfulness, tool_accuracy]        ││
│  └─────────────────────────────────────────────────────────────────┘│
│                               │                                      │
│                               ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ Evaluators (LLM-as-Judge)                                       ││
│  │                                                                  ││
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐               ││
│  │  │ Correctness │ │ Helpfulness │ │ Tool Select │               ││
│  │  │  Score: 0.9 │ │  Score: 0.8 │ │  Score: 1.0 │               ││
│  │  └─────────────┘ └─────────────┘ └─────────────┘               ││
│  │                                                                  ││
│  └─────────────────────────────────────────────────────────────────┘│
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Amazon CloudWatch                             │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐           │
│  │   Dashboard   │  │    Alarms     │  │     Logs      │           │
│  │   (Metrics)   │  │  (< 0.7 avg)  │  │   (Traces)    │           │
│  └───────────────┘  └───────────────┘  └───────────────┘           │
└─────────────────────────────────────────────────────────────────────┘
```

## Built-in Evaluators (13 Available)

| Category | Evaluator | Description | Score Range |
|----------|-----------|-------------|-------------|
| **Quality** | `correctness` | Is the answer factually correct? | 0.0 - 1.0 |
| | `helpfulness` | Does the answer address the user's need? | 0.0 - 1.0 |
| | `coherence` | Is the response logically structured? | 0.0 - 1.0 |
| **RAG** | `faithfulness` | Is the answer grounded in retrieved context? | 0.0 - 1.0 |
| | `relevance` | Are retrieved documents relevant to the query? | 0.0 - 1.0 |
| | `context_precision` | How precise is the retrieved context? | 0.0 - 1.0 |
| **Tools** | `tool_selection` | Did the agent choose the right tool? | 0.0 - 1.0 |
| | `tool_input_accuracy` | Were tool inputs formatted correctly? | 0.0 - 1.0 |
| **Safety** | `harmfulness` | Does the response contain harmful content? | 0.0 - 1.0 |
| | `toxicity` | Is the language appropriate? | 0.0 - 1.0 |

## Design for Knowledge Base Gateway

### Evaluators to Use

| Evaluator | Why |
|-----------|-----|
| `faithfulness` | Ensure answers are grounded in KB documents |
| `relevance` | Verify retrieved docs match user query |
| `helpfulness` | Measure if answers address seller questions |
| `tool_selection` | Validate correct tool (query vs RAG) chosen |

### Evaluation Configuration

```yaml
name: KnowledgeBaseEvaluation
description: Evaluate KB query quality for seller guides

dataSource:
  type: CLOUDWATCH_LOG_GROUP
  logGroupName: /aws/lambda/KnowledgeBaseProxy

samplingRate: 0.1  # Evaluate 10% of requests

evaluators:
  - name: faithfulness
    type: BUILT_IN
  - name: relevance  
    type: BUILT_IN
  - name: helpfulness
    type: BUILT_IN
  - name: MarketplaceAccuracy  # Custom
    type: CUSTOM
    modelArn: arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-haiku-20240307-v1:0
    prompt: |
      Evaluate if the response correctly identifies the marketplace (CN vs US) 
      based on the user's query. Score 1.0 if correct, 0.0 if wrong marketplace.

filters:
  - field: tool_name
    operator: IN
    values: [query_knowledge_base, retrieve_and_generate]
```

## Custom Evaluator Example

For our Knowledge Base, create a custom evaluator to check marketplace accuracy:

```python
custom_evaluator = {
    "name": "MarketplaceAccuracy",
    "type": "CUSTOM",
    "description": "Verify response matches queried marketplace",
    "modelArn": "arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-haiku-20240307-v1:0",
    "prompt": """
You are evaluating a knowledge base response for marketplace accuracy.

User Query: {{input}}
Retrieved Documents: {{context}}
Agent Response: {{output}}

Evaluate:
1. Did the user ask about a specific marketplace (CN or US)?
2. Does the response contain information from the correct marketplace?
3. Is there any cross-marketplace contamination?

Return a JSON object:
{
  "score": 0.0-1.0,
  "reasoning": "explanation"
}

Score 1.0 = Perfect marketplace match
Score 0.5 = Partially correct
Score 0.0 = Wrong marketplace or mixed data
"""
}
```

## Implementation Steps

### Step 1: Instrument Lambda with OpenTelemetry

Add tracing to the Lambda function:

```python
# knowledge_base_proxy.py
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# Initialize tracer
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

def handler(event, context):
    with tracer.start_as_current_span("knowledge_base_query") as span:
        span.set_attribute("tool_name", event.get("tool_name"))
        span.set_attribute("user_input", event.get("tool_input", {}).get("query"))
        
        # ... existing logic ...
        
        span.set_attribute("output", result)
        return result
```

### Step 2: Create Evaluation Configuration

```python
import boto3

client = boto3.client('bedrock-agentcore-control', region_name='us-west-2')

# Create online evaluation
response = client.create_online_evaluation(
    name='KnowledgeBaseQualityEval',
    description='Monitor KB response quality',
    dataSource={
        'type': 'CLOUDWATCH_LOG_GROUP',
        'cloudWatchLogGroup': {
            'logGroupName': '/aws/lambda/KnowledgeBaseProxy'
        }
    },
    evaluators=[
        {'evaluatorName': 'faithfulness', 'type': 'BUILT_IN'},
        {'evaluatorName': 'relevance', 'type': 'BUILT_IN'},
        {'evaluatorName': 'helpfulness', 'type': 'BUILT_IN'}
    ],
    samplingRate=0.1
)
```

### Step 3: Set Up CloudWatch Alarms

```python
cloudwatch = boto3.client('cloudwatch', region_name='us-west-2')

# Alert when faithfulness drops below 0.7
cloudwatch.put_metric_alarm(
    AlarmName='KB-Faithfulness-Low',
    MetricName='faithfulness',
    Namespace='AgentCore/Evaluations',
    Dimensions=[{'Name': 'EvaluationName', 'Value': 'KnowledgeBaseQualityEval'}],
    Statistic='Average',
    Period=300,
    EvaluationPeriods=3,
    Threshold=0.7,
    ComparisonOperator='LessThanThreshold',
    AlarmActions=['arn:aws:sns:us-west-2:123456789012:agent-quality-alerts']
)
```

## Metrics Dashboard

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| `faithfulness` | > 0.85 | < 0.7 |
| `relevance` | > 0.8 | < 0.6 |
| `helpfulness` | > 0.8 | < 0.65 |
| `tool_selection` | > 0.95 | < 0.9 |
| `MarketplaceAccuracy` | > 0.95 | < 0.85 |

## Sample Evaluation Results

```json
{
  "sessionId": "sess-12345",
  "timestamp": "2025-12-27T10:30:00Z",
  "input": "What are shipping requirements for CN marketplace?",
  "output": "For the China marketplace, sellers must use...",
  "evaluations": {
    "faithfulness": {
      "score": 0.92,
      "reasoning": "Response accurately reflects KB content about CN shipping"
    },
    "relevance": {
      "score": 0.88,
      "reasoning": "Retrieved documents are highly relevant to shipping query"
    },
    "helpfulness": {
      "score": 0.85,
      "reasoning": "Answer provides actionable information for sellers"
    },
    "MarketplaceAccuracy": {
      "score": 1.0,
      "reasoning": "Response correctly identifies and uses CN marketplace data"
    }
  }
}
```

## Cost Considerations

| Component | Cost Factor |
|-----------|-------------|
| Evaluator LLM calls | Per evaluation (use sampling) |
| CloudWatch Logs | Storage volume |
| CloudWatch Metrics | Number of metrics |

**Recommendation**: Start with 10% sampling rate, increase as needed.

## API Availability

> ⚠️ **Note**: As of Dec 2025, Evaluation APIs may be in preview. 
> Check `boto3` for available operations:

```python
import boto3
client = boto3.client('bedrock-agentcore-control', region_name='us-west-2')
eval_ops = [m for m in dir(client) if 'eval' in m.lower()]
print(eval_ops)
```

## Next Steps

1. **Phase 1**: Add OpenTelemetry instrumentation to Lambda
2. **Phase 2**: Create built-in evaluators (faithfulness, relevance)
3. **Phase 3**: Add custom MarketplaceAccuracy evaluator
4. **Phase 4**: Set up CloudWatch dashboard and alarms
5. **Phase 5**: Iterate based on evaluation insights

---

**Status**: Draft | **Date**: December 27, 2025

