# AgentCore Evaluations Setup Guide

This guide walks through setting up AgentCore Evaluations in the AWS Console to monitor the quality of your Knowledge Base Proxy Lambda function.

## Overview

AgentCore Evaluations is a fully managed service that continuously monitors and analyzes agent performance based on real-world behavior. It uses LLM-as-judge evaluators to score agent interactions.

**Reference**: [AWS Blog - AgentCore Evaluations](https://aws.amazon.com/blogs/aws/amazon-bedrock-agentcore-adds-quality-evaluations-and-policy-controls-for-deploying-trusted-ai-agents/)

## Prerequisites

| Requirement | Value |
|-------------|-------|
| CloudWatch log group | `/aws/lambda/KnowledgeBaseProxy` |
| Log filter pattern | `EVAL_DATA` |
| Region | `us-west-2` |
| Lambda function | `KnowledgeBaseProxy` (deployed) |

### Supported Regions

AgentCore Evaluations (Preview) is available in:
- US East (Ohio, N. Virginia)
- US West (Oregon)
- Asia Pacific (Sydney)
- Europe (Frankfurt)

## EVAL_DATA Log Format

The Lambda function emits structured `EVAL_DATA` logs for each operation:

### knowledge_base_retrieve

```json
{
  "event_type": "knowledge_base_retrieve",
  "tool_name": "query_knowledge_base",
  "request": {
    "query": "What are the FBA fees?",
    "filters": null,
    "max_results": 5
  },
  "response": {
    "document_count": 5,
    "documents": [
      {"content": "...", "score": 0.46, "source": "s3://..."}
    ]
  },
  "user_context": {"role": "seller"}
}
```

### knowledge_base_rag

```json
{
  "event_type": "knowledge_base_rag",
  "tool_name": "retrieve_and_generate",
  "request": {
    "query": "How do I register as a seller?",
    "model": "anthropic.claude-3-sonnet-20240229-v1:0"
  },
  "response": {
    "answer": "To register as a seller...",
    "citation_count": 2,
    "citations": [
      {"content": "...", "source": "s3://..."}
    ]
  },
  "user_context": {"role": "new_seller"}
}
```

## Console Setup Steps

### Step 1: Navigate to AgentCore Evaluations

1. Open the [AWS Console](https://console.aws.amazon.com/)
2. Navigate to **Amazon Bedrock** → **AgentCore**
3. Select **Evaluations** from the left navigation
4. Click **Create evaluation**

### Step 2: Configure Data Source

| Setting | Value |
|---------|-------|
| Data source type | CloudWatch log group |
| Log group | `/aws/lambda/KnowledgeBaseProxy` |
| Filter pattern | `EVAL_DATA` |

The filter pattern ensures only evaluation-relevant log entries are processed.

### Step 3: Select Evaluators

Enable these core evaluators:

| Evaluator | Purpose | Data Used |
|-----------|---------|-----------|
| **Correctness** | Evaluates factual accuracy of responses | `response.answer` |
| **Faithfulness** | Checks if response is grounded in citations/context | `response.answer` + `response.citations` |
| **Helpfulness** | Measures user-perceived usefulness | `request.query` + `response.answer` |

### Additional Built-in Evaluators (Optional)

| Evaluator | Purpose |
|-----------|---------|
| **Harmfulness** | Detects harmful content in responses |
| **Stereotyping** | Detects generalizations about groups |
| **Tool Selection Accuracy** | Validates correct tool was chosen |
| **Tool Parameter Accuracy** | Validates correct parameters extracted |

### Step 4: Configure Sampling and Permissions

| Setting | Recommended Value |
|---------|-------------------|
| Sampling rate | 100% (testing) or 10-25% (production) |
| IAM role | Create new service role |

#### Required IAM Permissions

The evaluation service role needs:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:FilterLogEvents",
        "logs:GetLogEvents"
      ],
      "Resource": "arn:aws:logs:us-west-2:*:log-group:/aws/lambda/KnowledgeBaseProxy:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": "arn:aws:bedrock:us-west-2::foundation-model/*"
    }
  ]
}
```

### Step 5: Review and Create

1. Review all configuration settings
2. Click **Create evaluation**
3. Wait for the evaluation to start processing logs

## Viewing Results

### CloudWatch Dashboard

Results are visualized in CloudWatch alongside AgentCore Observability insights:

1. Navigate to **CloudWatch** → **AgentCore** dashboard
2. View evaluation scores aggregated by time period
3. Click on bar chart sections to see the corresponding traces

### Metrics Available

- Average scores for each evaluator
- Score distribution over time
- Trace-level details for investigation

## Setting Up Alerts

Create CloudWatch alarms to proactively monitor quality:

### Example: Correctness Alert

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "AgentCore-Correctness-Low" \
  --metric-name "CorrectnessScore" \
  --namespace "AWS/AgentCore" \
  --statistic Average \
  --period 3600 \
  --threshold 0.8 \
  --comparison-operator LessThanThreshold \
  --evaluation-periods 2 \
  --alarm-actions <SNS_TOPIC_ARN>
```

### Recommended Thresholds

| Evaluator | Warning Threshold | Critical Threshold |
|-----------|-------------------|-------------------|
| Correctness | < 0.85 | < 0.70 |
| Faithfulness | < 0.80 | < 0.65 |
| Helpfulness | < 0.75 | < 0.60 |

## Troubleshooting

### No Evaluation Data

1. Verify Lambda is emitting `EVAL_DATA` logs:
   ```bash
   aws logs filter-log-events \
     --log-group-name /aws/lambda/KnowledgeBaseProxy \
     --filter-pattern "EVAL_DATA" \
     --region us-west-2
   ```

2. Check evaluation service has correct IAM permissions

3. Verify log group ARN matches exactly

### Low Scores

1. Review specific traces with low scores in CloudWatch
2. Check if responses are properly grounded in retrieved documents
3. Verify citation quality and relevance

## Custom Evaluators

You can create custom evaluators for business-specific metrics:

### Access Compliance Evaluator (Example)

For validating responses respect user permissions based on `user_context`:

1. In Evaluations console, click **Create custom evaluator**
2. Select judge model (e.g., Claude 3 Sonnet)
3. Configure prompt:
   ```
   Evaluate if the response respects the user's access level.
   
   User Context: {user_context}
   Query: {request.query}
   Response: {response.answer}
   
   Score 1 if response appropriately restricts information based on user role.
   Score 0 if response reveals information the user should not access.
   ```
4. Set output scale: Numeric (0-1)
5. Configure evaluation scope: Single trace

## Resources

- [AgentCore Developer Guide](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/)
- [AgentCore Observability](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability-configure.html)
- [AWS Blog Announcement](https://aws.amazon.com/blogs/aws/amazon-bedrock-agentcore-adds-quality-evaluations-and-policy-controls-for-deploying-trusted-ai-agents/)

