# AWS Bedrock Knowledge Base - Deployment Summary

## ✅ DEPLOYMENT COMPLETE!

All infrastructure and resources have been successfully deployed using AWS CDK and CLI.

## 📋 Deployed Resources

### Infrastructure (via CDK)
- ✅ **S3 Bucket**: `knowledge-base-313117444016-us-west-2`
- ✅ **OpenSearch Serverless Collection**: `kb-313117444016`
  - Endpoint: `https://syz46c1427ouyyvlouhf.us-west-2.aoss.amazonaws.com`
- ✅ **IAM Role**: `CdkStack-BedrockKnowledgeBaseRole24C5E17B-P1fxNLJaX1iq`
- ✅ **Data Access Policies**: Configured with proper permissions
- ✅ **Network & Encryption Policies**: Configured

### Bedrock Resources (via CLI/SDK)
- ✅ **OpenSearch Index**: `bedrock-knowledge-base-index` (created with proper vector mappings)
- ✅ **Knowledge Base**: `DocumentKnowledgeBase`
  - **ID**: `OYBA7PFNNQ`
  - **ARN**: `arn:aws:bedrock:us-west-2:313117444016:knowledge-base/OYBA7PFNNQ`
- ✅ **Data Source**: `S3DocumentSource`
  - **ID**: `E2EDW4MOKC`
  - Connected to: `s3://knowledge-base-313117444016-us-west-2/documents/`

## 🚀 Quick Start Guide

### 1. Upload Documents

Upload your documents to the S3 bucket:

```bash
# Upload a single document
aws s3 cp your-document.pdf s3://knowledge-base-313117444016-us-west-2/documents/

# Upload a directory
aws s3 sync ./your-docs/ s3://knowledge-base-313117444016-us-west-2/documents/

# Supported formats: PDF, TXT, MD, HTML, DOC, DOCX, CSV, XLS, XLSX
```

### 2. Sync/Ingest Documents

Start an ingestion job to process and vectorize your documents:

```bash
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id OYBA7PFNNQ \
  --data-source-id E2EDW4MOKC \
  --region us-west-2
```

Check ingestion job status:

```bash
aws bedrock-agent list-ingestion-jobs \
  --knowledge-base-id OYBA7PFNNQ \
  --data-source-id E2EDW4MOKC \
  --region us-west-2
```

### 3. Query Your Knowledge Base

#### Using AWS CLI

```bash
aws bedrock-agent-runtime retrieve-and-generate \
  --input '{"text":"What is the main topic of the documents?"}' \
  --retrieve-and-generate-configuration '{
    "type":"KNOWLEDGE_BASE",
    "knowledgeBaseConfiguration":{
      "knowledgeBaseId":"OYBA7PFNNQ",
      "modelArn":"arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0"
    }
  }' \
  --region us-west-2
```

#### Using Python SDK

```python
import boto3
import json

# Initialize client
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name='us-west-2')

# Query the knowledge base
response = bedrock_agent_runtime.retrieve_and_generate(
    input={'text': 'What is the main topic of the documents?'},
    retrieveAndGenerateConfiguration={
        'type': 'KNOWLEDGE_BASE',
        'knowledgeBaseConfiguration': {
            'knowledgeBaseId': 'OYBA7PFNNQ',
            'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0'
        }
    }
)

print(response['output']['text'])

# Access retrieved source documents
for citation in response.get('citations', []):
    for reference in citation.get('retrievedReferences', []):
        print(f"Source: {reference['location']['s3Location']['uri']}")
        print(f"Content: {reference['content']['text']}")
```

#### Using Node.js SDK

```javascript
import { BedrockAgentRuntimeClient, RetrieveAndGenerateCommand } from "@aws-sdk/client-bedrock-agent-runtime";

const client = new BedrockAgentRuntimeClient({ region: "us-west-2" });

const command = new RetrieveAndGenerateCommand({
  input: { text: "What is the main topic of the documents?" },
  retrieveAndGenerateConfiguration: {
    type: "KNOWLEDGE_BASE",
    knowledgeBaseConfiguration: {
      knowledgeBaseId: "OYBA7PFNNQ",
      modelArn: "arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0"
    }
  }
});

const response = await client.send(command);
console.log(response.output.text);
```

## 🔍 Monitoring & Management

### Check Knowledge Base Status

```bash
aws bedrock-agent get-knowledge-base \
  --knowledge-base-id OYBA7PFNNQ \
  --region us-west-2
```

### List Data Sources

```bash
aws bedrock-agent list-data-sources \
  --knowledge-base-id OYBA7PFNNQ \
  --region us-west-2
```

### View Documents in S3

```bash
aws s3 ls s3://knowledge-base-313117444016-us-west-2/documents/ --recursive
```

## 🛠️ Management Commands

### Update Documents

After updating documents in S3, re-sync:

```bash
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id OYBA7PFNNQ \
  --data-source-id E2EDW4MOKC \
  --region us-west-2
```

### Delete a Document

```bash
# Remove from S3
aws s3 rm s3://knowledge-base-313117444016-us-west-2/documents/your-document.pdf

# Re-sync to update the index
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id OYBA7PFNNQ \
  --data-source-id E2EDW4MOKC \
  --region us-west-2
```

## 📊 Architecture

```
┌─────────────────────┐
│   Your Documents    │
│     (PDF, TXT,      │
│    MD, DOCX, etc)   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│    S3 Bucket        │
│  /documents/*       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Data Source       │
│   (Auto-sync or     │
│   Manual trigger)   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Titan Embeddings   │
│     v2 Model        │
│  (1024 dimensions)  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   OpenSearch        │
│   Serverless        │
│  (Vector Store)     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Knowledge Base     │
│      (RAG)          │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Query with Claude  │
│   or other models   │
└─────────────────────┘
```

## 🧹 Cleanup

To delete all resources:

```bash
# 1. Delete Knowledge Base (this also deletes data sources)
aws bedrock-agent delete-knowledge-base \
  --knowledge-base-id OYBA7PFNNQ \
  --region us-west-2

# 2. Empty S3 bucket (if you want to delete the bucket)
aws s3 rm s3://knowledge-base-313117444016-us-west-2 --recursive

# 3. Destroy CDK stack
cd cdk
cdk destroy
```

## 💡 Tips & Best Practices

1. **Document Preparation**:
   - Clean and well-formatted documents work best
   - Break large documents into smaller chunks
   - Use consistent formatting

2. **Chunking Strategy**:
   - Default chunk size: 300 tokens
   - Overlap: 20% recommended
   - Adjust based on your content type

3. **Query Optimization**:
   - Be specific in your questions
   - Provide context when needed
   - Use natural language

4. **Cost Optimization**:
   - Monitor OpenSearch Serverless usage
   - Use S3 Intelligent-Tiering (already configured)
   - Delete old document versions periodically

5. **Security**:
   - S3 bucket has SSL enforcement enabled
   - OpenSearch uses encryption at rest
   - IAM roles follow least privilege principle

## 📚 Additional Resources

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Knowledge Base for Amazon Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base.html)
- [OpenSearch Serverless](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/serverless.html)

## 🆘 Troubleshooting

### Ingestion Job Fails
- Check S3 permissions
- Verify document formats are supported
- Review CloudWatch logs

### Query Returns No Results
- Ensure ingestion job completed successfully
- Check that documents are in the `documents/` prefix
- Try broader queries

### Permission Errors
- Verify IAM role has necessary permissions
- Check data access policies for OpenSearch
- Ensure Bedrock service is enabled in your region

---

**Deployed on**: December 23, 2025  
**Region**: us-west-2  
**Status**: ✅ Operational

