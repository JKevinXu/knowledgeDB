#!/usr/bin/env python3
"""
Create AgentCore MCP Gateway and add Lambda target
This script creates the gateway infrastructure for the Knowledge Base proxy
"""

import boto3
import json
import time
import sys
import uuid

# Configuration
REGION = 'us-west-2'
ACCOUNT_ID = '313117444016'
GATEWAY_NAME = 'KnowledgeBaseGateway'
LAMBDA_FUNCTION_NAME = 'KnowledgeBaseProxy'
LAMBDA_ARN = f'arn:aws:lambda:{REGION}:{ACCOUNT_ID}:function:{LAMBDA_FUNCTION_NAME}'
GATEWAY_INVOKE_ROLE_ARN = f'arn:aws:iam::{ACCOUNT_ID}:role/AgentCoreGatewayInvokeRole'
GATEWAY_ROLE_NAME = 'AgentCoreGatewayServiceRole'

# Tool definitions for the Lambda target
TOOL_DEFINITIONS = [
    {
        'name': 'query_knowledge_base',
        'description': 'Search and retrieve relevant documents from the knowledge base using semantic search. Returns document chunks with similarity scores.',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'query': {
                    'type': 'string',
                    'description': 'The natural language search query to find relevant documents'
                },
                'max_results': {
                    'type': 'integer',
                    'description': 'Maximum number of results to return (1-25)',
                    'default': 5
                }
            },
            'required': ['query']
        }
    },
    {
        'name': 'retrieve_and_generate',
        'description': 'Ask a question and get an AI-generated answer based on the knowledge base documents with citations.',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'query': {
                    'type': 'string',
                    'description': 'The question to answer using the knowledge base'
                },
                'max_tokens': {
                    'type': 'integer',
                    'description': 'Maximum tokens in the generated response',
                    'default': 2048
                }
            },
            'required': ['query']
        }
    },
    {
        'name': 'list_sources',
        'description': 'List all data sources connected to the knowledge base',
        'inputSchema': {
            'type': 'object',
            'properties': {},
            'required': []
        }
    },
    {
        'name': 'get_knowledge_base_info',
        'description': 'Get information about the knowledge base configuration',
        'inputSchema': {
            'type': 'object',
            'properties': {},
            'required': []
        }
    }
]


def create_gateway_role(iam_client):
    """Create or get IAM role for the AgentCore Gateway"""
    role_arn = f'arn:aws:iam::{ACCOUNT_ID}:role/{GATEWAY_ROLE_NAME}'
    
    try:
        iam_client.get_role(RoleName=GATEWAY_ROLE_NAME)
        print(f"   ℹ️  Role '{GATEWAY_ROLE_NAME}' already exists")
        return role_arn
    except iam_client.exceptions.NoSuchEntityException:
        pass
    
    # Create the role
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "bedrock-agentcore.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    iam_client.create_role(
        RoleName=GATEWAY_ROLE_NAME,
        AssumeRolePolicyDocument=json.dumps(trust_policy),
        Description='Service role for AgentCore Gateway'
    )
    
    # Attach necessary policies
    gateway_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "lambda:InvokeFunction"
                ],
                "Resource": LAMBDA_ARN
            },
            {
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                "Resource": "*"
            }
        ]
    }
    
    iam_client.put_role_policy(
        RoleName=GATEWAY_ROLE_NAME,
        PolicyName='AgentCoreGatewayPolicy',
        PolicyDocument=json.dumps(gateway_policy)
    )
    
    print(f"   ✅ Role '{GATEWAY_ROLE_NAME}' created")
    time.sleep(10)  # Wait for role propagation
    return role_arn


def main():
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║           AGENTCORE MCP GATEWAY - CREATION SCRIPT                     ║")
    print("╚══════════════════════════════════════════════════════════════════════╝\n")
    
    # Initialize clients
    client = boto3.client('bedrock-agentcore-control', region_name=REGION)
    iam_client = boto3.client('iam', region_name=REGION)
    
    # Step 1: Create or get gateway IAM role
    print("🔐 Step 1: Setting up IAM role for gateway...")
    gateway_role_arn = create_gateway_role(iam_client)
    print(f"   • Role ARN: {gateway_role_arn}")
    
    # Step 2: Check if gateway already exists
    print("\n🔍 Step 2: Checking for existing gateway...")
    gateway_id = None
    
    try:
        response = client.list_gateways()
        for gateway in response.get('gateways', []):
            if gateway.get('name') == GATEWAY_NAME:
                gateway_id = gateway.get('gatewayId')
                print(f"   ℹ️  Gateway '{GATEWAY_NAME}' already exists: {gateway_id}")
                break
    except Exception as e:
        print(f"   ⚠️  Error listing gateways: {e}")
    
    # Step 3: Create gateway if it doesn't exist
    if not gateway_id:
        print("\n🚀 Step 3: Creating AgentCore Gateway...")
        try:
            response = client.create_gateway(
                name=GATEWAY_NAME,
                description='MCP Gateway for Knowledge Base access - provides semantic search and RAG capabilities',
                roleArn=gateway_role_arn,
                protocolType='MCP',
                authorizerType='AWS_IAM',
                protocolConfiguration={
                    'mcp': {
                        'supportedVersions': ['2025-03-26'],
                        'instructions': 'This gateway provides tools to search and query a knowledge base containing seller guides and documentation.',
                        'searchType': 'SEMANTIC'
                    }
                }
            )
            gateway_id = response.get('gatewayId')
            gateway_status = response.get('status')
            print(f"   ✅ Gateway created successfully!")
            print(f"   📝 Gateway ID: {gateway_id}")
            print(f"   📝 Status: {gateway_status}")
            
            # Wait for gateway to be ready
            print("   ⏳ Waiting for gateway to be ready...")
            time.sleep(10)
            
        except client.exceptions.ConflictException:
            print(f"   ℹ️  Gateway '{GATEWAY_NAME}' already exists")
            # Try to get the gateway ID
            response = client.list_gateways()
            for gateway in response.get('gateways', []):
                if gateway.get('name') == GATEWAY_NAME:
                    gateway_id = gateway.get('gatewayId')
                    break
        except Exception as e:
            print(f"   ❌ Error creating gateway: {e}")
            sys.exit(1)
    else:
        print("\n⏭️  Step 3: Skipping gateway creation (already exists)")
    
    if not gateway_id:
        print("❌ Failed to get gateway ID")
        sys.exit(1)
    
    # Step 4: Get gateway details
    print(f"\n📋 Step 4: Getting gateway details...")
    try:
        response = client.get_gateway(gatewayId=gateway_id)
        gateway_status = response.get('status')
        gateway_endpoint = response.get('gatewayUrl', 'Not available yet')
        print(f"   • Gateway ID: {gateway_id}")
        print(f"   • Status: {gateway_status}")
        print(f"   • Endpoint: {gateway_endpoint}")
    except Exception as e:
        print(f"   ⚠️  Could not get gateway details: {e}")
        gateway_endpoint = "See AWS Console"
    
    # Step 5: Check existing targets
    print(f"\n🎯 Step 5: Checking existing gateway targets...")
    existing_targets = []
    try:
        response = client.list_gateway_targets(gatewayId=gateway_id)
        existing_targets = response.get('gatewayTargets', [])
        print(f"   Found {len(existing_targets)} existing target(s)")
        for target in existing_targets:
            print(f"   • {target.get('name', 'Unknown')}: {target.get('targetId', 'Unknown')}")
    except Exception as e:
        print(f"   ⚠️  Error listing targets: {e}")
    
    # Step 6: Create Lambda target
    target_name = 'KnowledgeBaseProxyTarget'
    target_exists = any(t.get('name') == target_name for t in existing_targets)
    
    if target_exists:
        print(f"\n⏭️  Step 6: Lambda target '{target_name}' already exists")
    else:
        print(f"\n🔗 Step 6: Creating Lambda target...")
        try:
            response = client.create_gateway_target(
                gatewayId=gateway_id,
                name=target_name,
                description='Lambda function that proxies Knowledge Base queries',
                targetConfiguration={
                    'lambdaTargetConfiguration': {
                        'lambdaArn': LAMBDA_ARN
                    }
                },
                credentialProviderConfigurations=[
                    {
                        'credentialProviderType': 'GATEWAY_IAM_ROLE'
                    }
                ],
                toolSchemas={
                    'inlinePayload': [
                        {
                            'name': tool['name'],
                            'description': tool['description'],
                            'inputSchema': {'json': json.dumps(tool['inputSchema'])}
                        }
                        for tool in TOOL_DEFINITIONS
                    ]
                }
            )
            target_id = response.get('targetId')
            print(f"   ✅ Lambda target created successfully!")
            print(f"   📝 Target ID: {target_id}")
        except client.exceptions.ConflictException:
            print(f"   ℹ️  Target '{target_name}' already exists")
        except Exception as e:
            print(f"   ❌ Error creating target: {e}")
            print(f"   Debug: Lambda ARN = {LAMBDA_ARN}")
            print(f"   Debug: Gateway Role ARN = {gateway_role_arn}")
    
    # Summary
    print("\n╔══════════════════════════════════════════════════════════════════════╗")
    print("║                         ✅ SETUP COMPLETE!                            ║")
    print("╚══════════════════════════════════════════════════════════════════════╝\n")
    
    print("📋 GATEWAY DETAILS:")
    print(f"   • Gateway Name: {GATEWAY_NAME}")
    print(f"   • Gateway ID: {gateway_id}")
    print(f"   • Endpoint: {gateway_endpoint}")
    
    print("\n📝 MCP CLIENT CONFIGURATION:")
    print(f'''
Configure your MCP client (Claude Desktop, Cursor, etc.) with:

{{
  "mcpServers": {{
    "knowledge-base": {{
      "url": "{gateway_endpoint}/mcp",
      "transport": "sse"
    }}
  }}
}}
''')
    
    print("🔗 AWS CONSOLE:")
    print(f"   https://console.aws.amazon.com/bedrock/home?region={REGION}#/agentcore/gateways/{gateway_id}")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

