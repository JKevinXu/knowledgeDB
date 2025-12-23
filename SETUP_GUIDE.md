# Bedrock Knowledge Base Setup Guide

The infrastructure (S3, OpenSearch Serverless, IAM roles) has been deployed successfully. However, the Knowledge Base creation requires the OpenSearch index to be created through the AWS Console due to permission complexities.

## Current Status ✅

The following resources are deployed:
- ✅ S3 Bucket for documents
- ✅ OpenSearch Serverless Collection  
- ✅ IAM Role for Bedrock Knowledge Base
- ✅ Data Access Policies
- ❌ Knowledge Base (needs manual creation)
- ❌ Data Source (needs manual creation)

## Stack Outputs

Run `cdk deploy` or check AWS CloudFormation console for:
- **Collection Endpoint**: `https://syz46c1427ouyyvlouhf.us-west-2.aoss.amazonaws.com`
- **S3 Bucket**: `knowledge-base-313117444016-us-west-2`
- **IAM Role ARN**: `arn:aws:iam::313117444016:role/CdkStack-BedrockKnowledgeBaseRole24C5E17B-P1fxNLJaX1iq`

## Complete Setup via AWS Console

### Step 1: Navigate to Amazon Bedrock Console

1. Open the [AWS Console](https://console.aws.amazon.com/)
2. Navigate to **Amazon Bedrock** service
3. In the left sidebar, click **Knowledge bases** under "Orchestration"

### Step 2: Create Knowledge Base

1. Click **Create knowledge base**
2. **Knowledge base details**:
   - Name: `DocumentKnowledgeBase`
   - Description: `Knowledge Base for document retrieval and Q&A`
   - IAM Role: Select **Use an existing service role**
   - Service role ARN: `arn:aws:iam::313117444016:role/CdkStack-BedrockKnowledgeBaseRole24C5E17B-P1fxNLJaX1iq`
   - Click **Next**

3. **Set up data source**:
   - Data source name: `S3DocumentSource`
   - S3 URI: `s3://knowledge-base-313117444016-us-west-2/documents/`
   - Click **Next**

4. **Select embeddings model**:
   - Embeddings model: **Titan Embeddings G1 - Text v2.0**
   - Click **Next**

5. **Configure vector store**:
   - Vector database: **OpenSearch Serverless**
   - Select **Use an existing OpenSearch Serverless collection**
   - Collection: Select `kb-313117444016`
   - Vector index name: `bedrock-knowledge-base-index`
   - Vector field: `bedrock-knowledge-base-default-vector`
   - Text field: `AMAZON_BEDROCK_TEXT_CHUNK`
   - Metadata field: `AMAZON_BEDROCK_METADATA`
   - Click **Next**

6. **Review and create**:
   - Review all settings
   - Click **Create knowledge base**

**Note**: The console will automatically create the OpenSearch index with the correct schema during this process.

### Step 3: Wait for Creation

The Knowledge Base creation takes 2-3 minutes. Wait for the status to show **Active**.

### Step 4: Upload Documents and Sync

1. Upload documents to S3:
   ```bash
   aws s3 cp your-document.pdf s3://knowledge-base-313117444016-us-west-2/documents/
   ```

2. In the Bedrock Console, select your Knowledge Base
3. Go to the **Data source** tab
4. Click **Sync** to ingest the documents
5. Wait for the sync to complete

### Step 5: Test the Knowledge Base

1. In the Knowledge Base details page, click **Test**
2. Ask a question about your documents
3. The Knowledge Base will retrieve relevant information and respond

## Using the Knowledge Base

### Query via AWS CLI

```bash
aws bedrock-agent-runtime retrieve-and-generate \
  --input '{"text":"Your question here"}' \
  --retrieve-and-generate-configuration '{
    "type":"KNOWLEDGE_BASE",
    "knowledgeBaseConfiguration":{
      "knowledgeBaseId":"<YOUR_KB_ID>",
      "modelArn":"arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0"
    }
  }'
```

### Query via Python SDK

```python
import boto3

bedrock = boto3.client('bedrock-agent-runtime')

response = bedrock.retrieve_and_generate(
    input={'text': 'Your question here'},
    retrieveAndGenerateConfiguration={
        'type': 'KNOWLEDGE_BASE',
        'knowledgeBaseConfiguration': {
            'knowledgeBaseId': '<YOUR_KB_ID>',
            'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0'
        }
    }
)

print(response['output']['text'])
```

## Troubleshooting

### "No such index" Error
This occurs when trying to create the Knowledge Base via CDK/CloudFormation before the index exists. Use the AWS Console method above to avoid this issue.

### Sync Fails
- Ensure documents are in `s3://knowledge-base-313117444016-us-west-2/documents/`
- Check that files are in supported formats (PDF, TXT, MD, HTML, DOC, DOCX)
- Verify the IAM role has S3 read permissions

### Access Denied
- Ensure the Bedrock service role ARN is correctly specified
- Check that data access policies include the role

## Clean Up

To delete all resources:

```bash
# Delete Knowledge Base via Console first
# Then destroy CDK stack
cd cdk
cdk destroy
```

## Alternative: Using CDK (After Console Setup)

After creating the Knowledge Base through the console once, you can uncomment the Knowledge Base code in `cdk/lib/cdk-stack.ts` and deploy via CDK. The index will already exist, so CDK deployment will work.


