#!/bin/bash

# This script helps set up the Bedrock Knowledge Base after the infrastructure is deployed
# Run this after creating the OpenSearch index through the AWS Console

set -e

echo "=== Bedrock Knowledge Base Setup ===" 
echo ""

# Get stack outputs
COLLECTION_ARN=$(aws cloudformation describe-stacks --stack-name CdkStack --query "Stacks[0].Outputs[?OutputKey=='CollectionEndpoint'].OutputValue" --output text | sed 's/https:\/\///')
COLLECTION_ENDPOINT=$(aws cloudformation describe-stacks --stack-name CdkStack --query "Stacks[0].Outputs[?OutputKey=='CollectionEndpoint'].OutputValue" --output text)
BUCKET_ARN=$(aws cloudformation describe-stacks --stack-name CdkStack --query "Stacks[0].Outputs[?OutputKey=='KnowledgeBucketArn'].OutputValue" --output text)
ROLE_ARN=$(aws cloudformation describe-stacks --stack-name CdkStack --query "Stacks[0].Outputs[?OutputKey=='KnowledgeBaseRoleArn'].OutputValue" --output text)
REGION=$(aws configure get region)

echo "Collection Endpoint: $COLLECTION_ENDPOINT"
echo "Bucket ARN: $BUCKET_ARN"
echo "Role ARN: $ROLE_ARN"
echo ""

# Get the collection ARN properly
COLLECTION_ID=$(echo $COLLECTION_ARN | cut -d'.' -f1)
FULL_COLLECTION_ARN="arn:aws:aoss:${REGION}:$(aws sts get-caller-identity --query Account --output text):collection/${COLLECTION_ID}"

echo "Creating Knowledge Base..."
echo ""

# Create Knowledge Base
KB_RESPONSE=$(aws bedrock-agent create-knowledge-base \
  --name "DocumentKnowledgeBase" \
  --description "Knowledge Base for document retrieval and Q&A" \
  --role-arn "$ROLE_ARN" \
  --knowledge-base-configuration '{
    "type": "VECTOR",
    "vectorKnowledgeBaseConfiguration": {
      "embeddingModelArn": "arn:aws:bedrock:'$REGION'::foundation-model/amazon.titan-embed-text-v2:0"
    }
  }' \
  --storage-configuration '{
    "type": "OPENSEARCH_SERVERLESS",
    "opensearchServerlessConfiguration": {
      "collectionArn": "'$FULL_COLLECTION_ARN'",
      "vectorIndexName": "bedrock-knowledge-base-index",
      "fieldMapping": {
        "vectorField": "bedrock-knowledge-base-default-vector",
        "textField": "AMAZON_BEDROCK_TEXT_CHUNK",
        "metadataField": "AMAZON_BEDROCK_METADATA"
      }
    }
  }')

KB_ID=$(echo $KB_RESPONSE | jq -r '.knowledgeBase.knowledgeBaseId')
KB_ARN=$(echo $KB_RESPONSE | jq -r '.knowledgeBase.knowledgeBaseArn')

echo "✅ Knowledge Base created successfully!"
echo "Knowledge Base ID: $KB_ID"
echo "Knowledge Base ARN: $KB_ARN"
echo ""

# Create Data Source
echo "Creating Data Source..."
DS_RESPONSE=$(aws bedrock-agent create-data-source \
  --knowledge-base-id "$KB_ID" \
  --name "S3DocumentSource" \
  --description "S3 bucket containing documents for the knowledge base" \
  --data-source-configuration '{
    "type": "S3",
    "s3Configuration": {
      "bucketArn": "'$BUCKET_ARN'",
      "inclusionPrefixes": ["documents/"]
    }
  }')

DS_ID=$(echo $DS_RESPONSE | jq -r '.dataSource.dataSourceId')

echo "✅ Data Source created successfully!"
echo "Data Source ID: $DS_ID"
echo ""
echo "=== Setup Complete ===" 
echo ""
echo "Next steps:"
echo "1. Upload documents to: s3://$(basename $BUCKET_ARN)/documents/"
echo "2. Sync the data source: aws bedrock-agent start-ingestion-job --knowledge-base-id $KB_ID --data-source-id $DS_ID"

