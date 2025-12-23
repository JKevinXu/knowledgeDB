#!/usr/bin/env python3
"""
Complete setup script for AWS Bedrock Knowledge Base using AWS CLI and SDK
This script creates the OpenSearch index and then the Knowledge Base resources
"""

import boto3
import json
import time
import sys
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth

def get_stack_outputs():
    """Get CloudFormation stack outputs"""
    print("📊 Retrieving stack outputs...")
    cfn = boto3.client('cloudformation')
    
    response = cfn.describe_stacks(StackName='CdkStack')
    outputs = response['Stacks'][0]['Outputs']
    
    output_dict = {}
    for output in outputs:
        output_dict[output['OutputKey']] = output['OutputValue']
    
    return output_dict

def create_opensearch_index(collection_endpoint, region):
    """Create OpenSearch index with proper AWS authentication"""
    print("\n🔧 Creating OpenSearch index...")
    
    # Remove https:// from endpoint
    host = collection_endpoint.replace('https://', '').replace('http://', '')
    
    # Get AWS credentials
    session = boto3.Session(region_name=region)
    credentials = session.get_credentials()
    
    # Create AWS auth
    auth = AWSV4SignerAuth(credentials, region, 'aoss')
    
    # Create OpenSearch client
    client = OpenSearch(
        hosts=[{'host': host, 'port': 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=30
    )
    
    # Index configuration for Bedrock Knowledge Base
    index_name = 'bedrock-knowledge-base-index'
    index_body = {
        "settings": {
            "index.knn": True,
            "number_of_shards": 2,
            "number_of_replicas": 0
        },
        "mappings": {
            "properties": {
                "bedrock-knowledge-base-default-vector": {
                    "type": "knn_vector",
                    "dimension": 1024,
                    "method": {
                        "name": "hnsw",
                        "engine": "faiss",
                        "space_type": "l2",
                        "parameters": {
                            "ef_construction": 512,
                            "m": 16
                        }
                    }
                },
                "AMAZON_BEDROCK_TEXT_CHUNK": {
                    "type": "text",
                    "index": True
                },
                "AMAZON_BEDROCK_METADATA": {
                    "type": "text",
                    "index": False
                }
            }
        }
    }
    
    try:
        # Check if index already exists
        if client.indices.exists(index=index_name):
            print(f"   ✅ Index '{index_name}' already exists")
            return True
        
        # Create the index
        response = client.indices.create(index=index_name, body=index_body)
        print(f"   ✅ Index '{index_name}' created successfully")
        
        # Wait for the index to be fully propagated and visible
        print("   ⏳ Waiting 60 seconds for index to propagate...")
        time.sleep(60)
        return True
        
    except Exception as e:
        print(f"   ❌ Error creating index: {str(e)}")
        return False

def create_knowledge_base(role_arn, collection_endpoint, region):
    """Create Bedrock Knowledge Base"""
    print("\n🧠 Creating Bedrock Knowledge Base...")
    
    bedrock = boto3.client('bedrock-agent', region_name=region)
    
    # Extract collection ID from endpoint
    collection_host = collection_endpoint.replace('https://', '').replace('http://', '')
    collection_id = collection_host.split('.')[0]
    
    # Get account ID
    sts = boto3.client('sts')
    account_id = sts.get_caller_identity()['Account']
    
    collection_arn = f"arn:aws:aoss:{region}:{account_id}:collection/{collection_id}"
    
    try:
        response = bedrock.create_knowledge_base(
            name='DocumentKnowledgeBase',
            description='Knowledge Base for document retrieval and Q&A',
            roleArn=role_arn,
            knowledgeBaseConfiguration={
                'type': 'VECTOR',
                'vectorKnowledgeBaseConfiguration': {
                    'embeddingModelArn': f'arn:aws:bedrock:{region}::foundation-model/amazon.titan-embed-text-v2:0'
                }
            },
            storageConfiguration={
                'type': 'OPENSEARCH_SERVERLESS',
                'opensearchServerlessConfiguration': {
                    'collectionArn': collection_arn,
                    'vectorIndexName': 'bedrock-knowledge-base-index',
                    'fieldMapping': {
                        'vectorField': 'bedrock-knowledge-base-default-vector',
                        'textField': 'AMAZON_BEDROCK_TEXT_CHUNK',
                        'metadataField': 'AMAZON_BEDROCK_METADATA'
                    }
                }
            }
        )
        
        kb_id = response['knowledgeBase']['knowledgeBaseId']
        kb_arn = response['knowledgeBase']['knowledgeBaseArn']
        
        print(f"   ✅ Knowledge Base created successfully")
        print(f"   📝 Knowledge Base ID: {kb_id}")
        print(f"   📝 Knowledge Base ARN: {kb_arn}")
        
        return kb_id, kb_arn
        
    except Exception as e:
        print(f"   ❌ Error creating Knowledge Base: {str(e)}")
        return None, None

def create_data_source(kb_id, bucket_arn, region):
    """Create Data Source for the Knowledge Base"""
    print("\n📁 Creating Data Source...")
    
    bedrock = boto3.client('bedrock-agent', region_name=region)
    
    try:
        response = bedrock.create_data_source(
            knowledgeBaseId=kb_id,
            name='S3DocumentSource',
            description='S3 bucket containing documents for the knowledge base',
            dataSourceConfiguration={
                'type': 'S3',
                's3Configuration': {
                    'bucketArn': bucket_arn,
                    'inclusionPrefixes': ['documents/']
                }
            }
        )
        
        ds_id = response['dataSource']['dataSourceId']
        print(f"   ✅ Data Source created successfully")
        print(f"   📝 Data Source ID: {ds_id}")
        
        return ds_id
        
    except Exception as e:
        print(f"   ❌ Error creating Data Source: {str(e)}")
        return None

def main():
    """Main execution function"""
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║           AWS BEDROCK KNOWLEDGE BASE - AUTOMATED SETUP               ║")
    print("╚══════════════════════════════════════════════════════════════════════╝\n")
    
    # Get stack outputs
    outputs = get_stack_outputs()
    
    collection_endpoint = outputs['CollectionEndpoint']
    bucket_arn = outputs['KnowledgeBucketArn']
    role_arn = outputs['KnowledgeBaseRoleArn']
    bucket_name = outputs['KnowledgeBucketName']
    
    # Get region from session
    session = boto3.Session()
    region = session.region_name
    
    print(f"   • Collection: {collection_endpoint}")
    print(f"   • Bucket: {bucket_arn}")
    print(f"   • Role: {role_arn}")
    print(f"   • Region: {region}")
    
    # Step 1: Create OpenSearch index
    if not create_opensearch_index(collection_endpoint, region):
        print("\n❌ Failed to create OpenSearch index. Exiting...")
        sys.exit(1)
    
    # Step 2: Create Knowledge Base
    kb_id, kb_arn = create_knowledge_base(role_arn, collection_endpoint, region)
    if not kb_id:
        print("\n❌ Failed to create Knowledge Base. Exiting...")
        sys.exit(1)
    
    # Step 3: Create Data Source
    ds_id = create_data_source(kb_id, bucket_arn, region)
    if not ds_id:
        print("\n❌ Failed to create Data Source. Exiting...")
        sys.exit(1)
    
    # Success summary
    print("\n╔══════════════════════════════════════════════════════════════════════╗")
    print("║                         ✅ SETUP COMPLETE!                            ║")
    print("╚══════════════════════════════════════════════════════════════════════╝\n")
    
    print("📋 RESOURCE IDs:")
    print(f"   • Knowledge Base ID: {kb_id}")
    print(f"   • Data Source ID: {ds_id}")
    
    print("\n📝 NEXT STEPS:")
    print(f"\n1. Upload documents to S3:")
    print(f"   aws s3 cp your-document.pdf s3://{bucket_name}/documents/")
    
    print(f"\n2. Sync the data source:")
    print(f"   aws bedrock-agent start-ingestion-job \\")
    print(f"     --knowledge-base-id {kb_id} \\")
    print(f"     --data-source-id {ds_id}")
    
    print(f"\n3. Query your knowledge base:")
    print(f"   aws bedrock-agent-runtime retrieve-and-generate \\")
    print(f"     --input '{{\"text\":\"Your question here\"}}' \\")
    print(f"     --retrieve-and-generate-configuration '{{")
    print(f"       \"type\":\"KNOWLEDGE_BASE\",")
    print(f"       \"knowledgeBaseConfiguration\":{{")
    print(f"         \"knowledgeBaseId\":\"{kb_id}\",")
    print(f"         \"modelArn\":\"arn:aws:bedrock:{region}::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0\"")
    print(f"       }}")
    print(f"     }}'")
    
    print("\n🎉 Your Bedrock Knowledge Base is ready to use!\n")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

