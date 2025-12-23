# knowledgeDB

A comprehensive solution for building an enterprise knowledge base with **metadata filtering** and **access control** using **Amazon Bedrock Knowledge Bases**.

## Overview

This project provides a robust approach to building a knowledge base that enables:
- **Fine-grained retrieval** through metadata filtering
- **Access control** to ensure users only see authorized documents
- **Semantic search** with vector embeddings
- **RAG (Retrieval-Augmented Generation)** for intelligent responses

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Application Layer                               │
├─────────────────────────────────────────────────────────────────────────────┤
│   User Request ──▶ API Gateway ──▶ Lambda (Access Control Logic)            │
└─────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Amazon Bedrock Knowledge Base                       │
├─────────────────────────────────────────────────────────────────────────────┤
│   Retrieve API + Metadata Filters ◀──▶ OpenSearch Serverless (Vector Store) │
│                 │                                                            │
│                 └──────────────────▶ Foundation Model (Claude/Titan)         │
└─────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Amazon S3 Data Source                          │
├─────────────────────────────────────────────────────────────────────────────┤
│   documents/                                                                 │
│   ├── finance/quarterly-report.pdf + .metadata.json                         │
│   ├── engineering/architecture-guide.md + .metadata.json                    │
│   └── hr/employee-handbook.pdf + .metadata.json                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Technology Stack

| Component          | Technology              | Purpose                         |
| ------------------ | ----------------------- | ------------------------------- |
| **Storage**        | Amazon S3               | Documents + metadata JSON files |
| **Vector Search**  | Bedrock KB + OpenSearch | Semantic search with embeddings |
| **Filtering**      | Bedrock Retrieve API    | Query-time metadata filters     |
| **Access Control** | Lambda + Metadata       | Role/department-based filtering |
| **Generation**     | Bedrock + Claude/Titan  | RAG response generation         |

## Features

### Metadata Filtering
Query-time filters on document attributes including:
- Department (engineering, finance, hr, legal, marketing)
- Document type (policy, report, guide, memo, contract)
- Access level (public, internal, confidential, restricted)
- Custom tags and attributes

### Filter Operators

| Operator            | Description                  |
| ------------------- | ---------------------------- |
| `equals`            | Exact match                  |
| `notEquals`         | Not equal                    |
| `greaterThan`       | Greater than (numbers/dates) |
| `lessThan`          | Less than                    |
| `in`                | Value in list                |
| `notIn`             | Value not in list            |
| `startsWith`        | String prefix                |
| `stringContains`    | Substring match              |
| `listContains`      | List contains value          |
| `andAll`            | All conditions must match    |
| `orAll`             | Any condition matches        |

## Document Structure

```
s3://knowledge-base-bucket/
├── documents/
│   ├── engineering/
│   │   ├── system-design-guide.pdf
│   │   └── system-design-guide.pdf.metadata.json
│   ├── finance/
│   │   ├── q3-earnings-report.pdf
│   │   └── q3-earnings-report.pdf.metadata.json
│   └── hr/
│       ├── employee-handbook.pdf
│       └── employee-handbook.pdf.metadata.json
```

### Metadata File Example

```json
{
  "metadataAttributes": {
    "documentId": "eng-001",
    "department": "engineering",
    "documentType": "guide",
    "accessLevel": "internal",
    "author": "Platform Team",
    "createdDate": "2025-06-15",
    "tags": ["architecture", "best-practices", "microservices"],
    "allowedRoles": ["engineer", "tech-lead", "architect", "admin"]
  }
}
```

## Best Practices

1. **Metadata Schema Governance** - Define a standard schema and validate all metadata files
2. **Security** - Always apply access filters at query time
3. **Performance** - Limit filter conditions and use indexed metadata attributes
4. **Monitoring** - Log all queries with user context and filters applied
5. **Data Lifecycle** - Implement metadata update automation when documents change

## Getting Started

### Prerequisites

- Node.js 18+
- AWS CLI configured with appropriate credentials
- AWS CDK CLI (`npm install -g aws-cdk`)

### Deploy Infrastructure

1. **Navigate to CDK directory:**

```bash
cd cdk
npm install
```

2. **Bootstrap CDK (first time only):**

```bash
cdk bootstrap
```

3. **Deploy the S3 bucket:**

```bash
cdk deploy
```

This will create:
- S3 bucket with versioning and encryption enabled
- Bucket policy granting Amazon Bedrock access
- Intelligent tiering for cost optimization
- Lifecycle rules for old versions

### Upload Documents

After deployment, upload your documents with metadata files:

```bash
# Upload a document
aws s3 cp my-document.pdf s3://knowledge-base-<account-id>-<region>/documents/engineering/

# Upload its metadata
aws s3 cp my-document.pdf.metadata.json s3://knowledge-base-<account-id>-<region>/documents/engineering/
```

### Next Steps

1. Create metadata JSON files for each document
2. Configure Amazon Bedrock Knowledge Base with S3 as data source
3. Implement query-time filtering in your application layer

## References

- [Amazon Bedrock Knowledge Bases Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base.html)
- [Bedrock Retrieval Filter API Reference](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_agent-runtime_Retrieve.html)
- [Full Implementation Guide](https://jkevinxu.github.io/github-blog/2025/12/22/aws-knowledge-base-metadata-filtering-solution.html)

## License

MIT
