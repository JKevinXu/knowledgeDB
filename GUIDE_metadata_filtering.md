# Bedrock Knowledge Base - Metadata Filtering Guide

## Overview

AWS Bedrock Knowledge Base supports **metadata filtering** to retrieve documents based on custom attributes. The filter is a **separate field** in the API, not part of the query text.

## API Structure

### ✅ Correct: Separate Filter Field

```json
{
  "retrievalQuery": {
    "text": "What are the registration requirements?"
  },
  "retrievalConfiguration": {
    "vectorSearchConfiguration": {
      "numberOfResults": 5,
      "filter": {
        "equals": {
          "key": "marketplace",
          "value": "US"
        }
      }
    }
  }
}
```

### ❌ Incorrect: Metadata in Query Text

```json
{
  "retrievalQuery": {
    "text": "What are the registration requirements for US marketplace?"
  }
}
```
**Why incorrect**: Relies on semantic similarity, less accurate, may retrieve irrelevant documents.

## Adding Searchable Metadata

### Method: metadata.json Files

For each document, create a companion `.metadata.json` file:

**Document**: `seller-guide-us.md`  
**Metadata File**: `seller-guide-us.md.metadata.json`

```json
{
  "metadataAttributes": {
    "marketplace": "US",
    "region": "north_america",
    "document_type": "seller_guide",
    "language": "english"
  }
}
```

**Upload both files to S3**:
```bash
aws s3 cp seller-guide-us.md s3://your-bucket/documents/
aws s3 cp seller-guide-us.md.metadata.json s3://your-bucket/documents/
```

**Re-ingest to index metadata**:
```bash
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id YOUR_KB_ID \
  --data-source-id YOUR_DS_ID
```

## Filter Operators

### 1. Equals
```json
{
  "equals": {
    "key": "marketplace",
    "value": "US"
  }
}
```

### 2. In (Multiple Values)
```json
{
  "in": {
    "key": "marketplace",
    "value": ["US", "CA", "MX"]
  }
}
```

### 3. Not Equals
```json
{
  "notEquals": {
    "key": "marketplace",
    "value": "CN"
  }
}
```

### 4. And (Multiple Conditions)
```json
{
  "andAll": [
    {
      "equals": {
        "key": "marketplace",
        "value": "US"
      }
    },
    {
      "equals": {
        "key": "document_type",
        "value": "seller_guide"
      }
    }
  ]
}
```

### 5. Or (Any Condition)
```json
{
  "orAll": [
    {
      "equals": {
        "key": "marketplace",
        "value": "US"
      }
    },
    {
      "equals": {
        "key": "marketplace",
        "value": "CN"
      }
    }
  ]
}
```

### 6. Greater Than / Less Than
```json
{
  "greaterThan": {
    "key": "price",
    "value": 100
  }
}
```

## Test Results from Our Implementation

### Query: "What are the seller registration requirements and monthly fees?"

#### With marketplace="US" Filter:
- **Results**: 4 chunks, ALL from seller-guide-us.md
- **Top Result Score**: 0.463
- **Metadata Retrieved**: 
  - marketplace: US
  - region: north_america
  - document_type: seller_guide
  - language: english

#### With marketplace="CN" Filter:
- **Results**: 5 chunks, ALL from seller-guide-cn.md
- **Top Result Score**: 0.418
- **Metadata Retrieved**:
  - marketplace: CN
  - region: asia_pacific
  - document_type: seller_guide
  - language: chinese

#### Without Filter:
- **Results**: 6 chunks, MIXED (3 US + 3 CN)
- **Observation**: Returns results from both marketplaces based on semantic similarity

## AWS CLI Examples

### Retrieve with Filter
```bash
aws bedrock-agent-runtime retrieve \
  --knowledge-base-id OYBA7PFNNQ \
  --region us-west-2 \
  --retrieval-query '{"text":"Your question here"}' \
  --retrieval-configuration '{
    "vectorSearchConfiguration":{
      "numberOfResults":5,
      "filter":{
        "equals":{
          "key":"marketplace",
          "value":"US"
        }
      }
    }
  }'
```

### Retrieve and Generate with Filter
```bash
aws bedrock-agent-runtime retrieve-and-generate \
  --region us-west-2 \
  --input '{"text":"Your question here"}' \
  --retrieve-and-generate-configuration '{
    "type":"KNOWLEDGE_BASE",
    "knowledgeBaseConfiguration":{
      "knowledgeBaseId":"OYBA7PFNNQ",
      "modelArn":"arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0",
      "retrievalConfiguration":{
        "vectorSearchConfiguration":{
          "numberOfResults":5,
          "filter":{
            "equals":{
              "key":"marketplace",
              "value":"US"
            }
          }
        }
      }
    }
  }'
```

## Python SDK Example

```python
import boto3

bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name='us-west-2')

# Retrieve with metadata filter
response = bedrock_agent_runtime.retrieve(
    knowledgeBaseId='OYBA7PFNNQ',
    retrievalQuery={'text': 'What are the seller requirements?'},
    retrievalConfiguration={
        'vectorSearchConfiguration': {
            'numberOfResults': 5,
            'filter': {
                'equals': {
                    'key': 'marketplace',
                    'value': 'US'
                }
            }
        }
    }
)

# Process results
for result in response['retrievalResults']:
    print(f"Score: {result['score']}")
    print(f"Source: {result['location']['s3Location']['uri']}")
    print(f"Metadata: {result['metadata']}")
    print(f"Content: {result['content']['text'][:200]}...\n")
```

## Node.js SDK Example

```javascript
import { BedrockAgentRuntimeClient, RetrieveCommand } from "@aws-sdk/client-bedrock-agent-runtime";

const client = new BedrockAgentRuntimeClient({ region: "us-west-2" });

const command = new RetrieveCommand({
  knowledgeBaseId: "OYBA7PFNNQ",
  retrievalQuery: { text: "What are the seller requirements?" },
  retrievalConfiguration: {
    vectorSearchConfiguration: {
      numberOfResults: 5,
      filter: {
        equals: {
          key: "marketplace",
          value: "US"
        }
      }
    }
  }
});

const response = await client.send(command);

response.retrievalResults.forEach(result => {
  console.log(`Score: ${result.score}`);
  console.log(`Marketplace: ${result.metadata.marketplace}`);
  console.log(`Content: ${result.content.text.substring(0, 200)}...\n`);
});
```

## Best Practices

### 1. Metadata Design
- Use consistent key names across documents
- Keep metadata simple and relevant
- Include hierarchical attributes (marketplace, region, category)

### 2. Query Strategy
- **General Query**: Use semantic search without filters
- **Specific Query**: Add metadata filters to narrow results
- **Multi-tenant**: Filter by tenant_id, organization, etc.

### 3. Performance
- Metadata filtering happens BEFORE semantic search
- More restrictive filters = faster queries
- Balance specificity with result coverage

### 4. Metadata vs Query Text
- **Metadata**: Exact matching (marketplace="US")
- **Query Text**: Semantic similarity (natural language)
- **Best**: Combine both for precision

## Common Use Cases

### Multi-Region Documentation
```json
{
  "equals": {
    "key": "region",
    "value": "north_america"
  }
}
```

### Multi-Language Content
```json
{
  "equals": {
    "key": "language",
    "value": "english"
  }
}
```

### Document Type Filtering
```json
{
  "in": {
    "key": "document_type",
    "value": ["user_guide", "api_reference", "tutorial"]
  }
}
```

### Version-Specific Docs
```json
{
  "andAll": [
    {
      "equals": {
        "key": "product",
        "value": "api"
      }
    },
    {
      "equals": {
        "key": "version",
        "value": "v2"
      }
    }
  ]
}
```

### Multi-Tenant Applications
```json
{
  "equals": {
    "key": "tenant_id",
    "value": "company_123"
  }
}
```

## Troubleshooting

### Metadata Not Showing in Results
1. Verify `.metadata.json` file format is correct
2. Ensure metadata file is uploaded to S3
3. Re-run ingestion job after adding metadata
4. Check metadata file naming: `document.ext.metadata.json`

### Filter Not Working
1. Verify the metadata key name matches exactly
2. Check metadata value is a string (use quotes)
3. Ensure documents have been re-ingested after adding metadata
4. Review CloudWatch logs for ingestion errors

### Wrong Results Returned
1. Verify filter syntax is correct (equals vs in vs andAll)
2. Check if metadata values are case-sensitive
3. Test without filter first to confirm documents are indexed
4. Verify metadata is attached to the correct chunks

## Summary

| Aspect | Details |
|--------|---------|
| **Metadata Location** | Separate `filter` field in API, NOT in query text |
| **Metadata Source** | `.metadata.json` files alongside documents |
| **Operators** | equals, in, notEquals, andAll, orAll, greaterThan, lessThan |
| **Performance** | Filters applied BEFORE semantic search (efficient) |
| **Use Case** | Multi-marketplace, multi-tenant, versioned docs, localization |

---

**Knowledge Base ID**: OYBA7PFNNQ  
**Test Documents**: seller-guide-us.md, seller-guide-cn.md  
**Tested**: December 2025  
**Status**: ✅ Fully Operational

