# AgentCore MCP Gateway to Lambda - Knowledge Base Proxy

This guide explains how to create an **Amazon Bedrock AgentCore MCP Gateway** that uses **AWS Lambda** to proxy your existing Knowledge Base, enabling AI agents (like Claude Desktop, Cursor, or custom MCP clients) to access your document knowledge base through the Model Context Protocol (MCP).

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Step 1: Create the Lambda Function](#step-1-create-the-lambda-function)
5. [Step 2: Create the AgentCore Gateway](#step-2-create-the-agentcore-gateway)
6. [Step 3: Configure OAuth Authorization](#step-3-configure-oauth-authorization)
7. [Step 4: Add Lambda Target to Gateway](#step-4-add-lambda-target-to-gateway)
8. [Step 5: Connect MCP Clients](#step-5-connect-mcp-clients)
9. [CDK Implementation](#cdk-implementation)
10. [Testing](#testing)
11. [Troubleshooting](#troubleshooting)

---

## Overview

### What is AgentCore MCP Gateway?

The **Amazon Bedrock AgentCore Gateway** is a managed AWS service that acts as an MCP (Model Context Protocol) server. It provides a unified, secure endpoint for AI agents to discover and invoke tools. The gateway handles:

- **Protocol Translation**: Converts MCP requests to AWS service calls
- **Authentication**: OAuth-based inbound authorization
- **Tool Discovery**: Exposes tools from multiple targets (Lambda, API Gateway, etc.)
- **Credential Management**: Securely manages outbound credentials

### Why Use Lambda as a Proxy?

Using Lambda as a proxy between the AgentCore Gateway and your Knowledge Base provides:

- **Custom Logic**: Transform queries, filter results, add context
- **Security**: Additional validation and access control layer
- **Flexibility**: Support multiple operations (retrieve, retrieve-and-generate)
- **Logging**: Enhanced observability and audit trails
- **Cost Control**: Add rate limiting, caching, and quota management

### Your Existing Infrastructure

Based on your deployment, you have:

| Resource | Value |
|----------|-------|
| Knowledge Base ID | `OYBA7PFNNQ` |
| Data Source ID | `E2EDW4MOKC` |
| S3 Bucket | `knowledge-base-313117444016-us-west-2` |
| Region | `us-west-2` |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                              MCP Clients                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────────┐ │
│  │   Claude    │  │   Cursor    │  │   Custom    │  │   Amazon Bedrock Agent   │ │
│  │   Desktop   │  │     IDE     │  │   Agent     │  │   (with MCP enabled)     │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └────────────┬─────────────┘ │
└─────────┼────────────────┼────────────────┼──────────────────────┼───────────────┘
          │                │                │                      │
          └────────────────┴────────────────┴──────────────────────┘
                                    │
                                    │ MCP Protocol (JSON-RPC over HTTP)
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                        AgentCore MCP Gateway                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                     OAuth Inbound Authorization                              │ │
│  │                    (Amazon Cognito / Custom OAuth)                           │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                         Tool Registry                                        │ │
│  │  • query_knowledge_base - Retrieve documents from knowledge base             │ │
│  │  • retrieve_and_generate - Query with LLM-generated response                 │ │
│  │  • list_documents - List indexed documents                                   │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                    Outbound Credential Management                            │ │
│  │                       (IAM Role Assumption)                                  │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Lambda Invocation
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                      AWS Lambda Function                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │  • Parse MCP tool call                                                       │ │
│  │  • Validate input                                                            │ │
│  │  • Call Bedrock Agent Runtime                                                │ │
│  │  • Format response                                                           │ │
│  │  • Return MCP-compatible result                                              │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Bedrock Agent Runtime API
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                    Amazon Bedrock Knowledge Base                                  │
│  ┌────────────────────┐  ┌────────────────────┐  ┌────────────────────────────┐  │
│  │   S3 Data Source   │  │  Titan Embeddings  │  │  OpenSearch Serverless     │  │
│  │   (Documents)      │  │  (Vector Model)    │  │  (Vector Store)            │  │
│  └────────────────────┘  └────────────────────┘  └────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

Before starting, ensure you have:

1. ✅ AWS CLI configured with appropriate permissions
2. ✅ Existing Bedrock Knowledge Base (ID: `OYBA7PFNNQ`)
3. ✅ Node.js 18+ and npm installed
4. ✅ Python 3.12+ installed
5. ✅ AWS CDK installed (`npm install -g aws-cdk`)

### Required IAM Permissions

Your AWS user/role needs permissions for:
- `bedrock-agentcore:*` - AgentCore Gateway management
- `lambda:*` - Lambda function management
- `cognito-idp:*` - Cognito user pool management
- `iam:*` - IAM role management
- `bedrock-agent-runtime:*` - Knowledge Base queries

---

## Step 1: Create the Lambda Function

The Lambda function serves as the bridge between the AgentCore Gateway and your Knowledge Base.

### 1.1 Lambda Function Code

Create the file `agentcore/lambda/knowledge_base_proxy.py`:

```python
"""
Knowledge Base Proxy Lambda Function
Handles MCP tool calls from AgentCore Gateway and proxies to Bedrock Knowledge Base
"""

import json
import boto3
import os
from typing import Any, Dict, List, Optional

# Initialize clients
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')

# Configuration from environment variables
KNOWLEDGE_BASE_ID = os.environ.get('KNOWLEDGE_BASE_ID', 'OYBA7PFNNQ')
MODEL_ARN = os.environ.get('MODEL_ARN', 'arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0')
REGION = os.environ.get('AWS_REGION', 'us-west-2')


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for AgentCore Gateway requests
    
    Event structure from AgentCore Gateway:
    {
        "tool_name": "query_knowledge_base",
        "tool_input": {
            "query": "What is the shipping policy?",
            "max_results": 5
        }
    }
    """
    print(f"Received event: {json.dumps(event)}")
    
    try:
        tool_name = event.get('tool_name', event.get('name', ''))
        tool_input = event.get('tool_input', event.get('input', {}))
        
        # Handle different tools
        if tool_name == 'query_knowledge_base':
            return query_knowledge_base(tool_input)
        elif tool_name == 'retrieve_and_generate':
            return retrieve_and_generate(tool_input)
        elif tool_name == 'list_sources':
            return list_sources(tool_input)
        else:
            return error_response(f"Unknown tool: {tool_name}")
            
    except Exception as e:
        print(f"Error processing request: {str(e)}")
        return error_response(str(e))


def query_knowledge_base(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Retrieve relevant documents from the knowledge base
    
    Parameters:
    - query (str): The search query
    - max_results (int): Maximum number of results to return (default: 5)
    - filter (dict): Optional metadata filter
    """
    query = params.get('query', '')
    max_results = params.get('max_results', 5)
    metadata_filter = params.get('filter')
    
    if not query:
        return error_response("Query parameter is required")
    
    retrieve_params = {
        'knowledgeBaseId': KNOWLEDGE_BASE_ID,
        'retrievalQuery': {
            'text': query
        },
        'retrievalConfiguration': {
            'vectorSearchConfiguration': {
                'numberOfResults': min(max_results, 25)  # Cap at 25
            }
        }
    }
    
    # Add metadata filter if provided
    if metadata_filter:
        retrieve_params['retrievalConfiguration']['vectorSearchConfiguration']['filter'] = metadata_filter
    
    try:
        response = bedrock_agent_runtime.retrieve(**retrieve_params)
        
        results = []
        for item in response.get('retrievalResults', []):
            result = {
                'content': item.get('content', {}).get('text', ''),
                'score': item.get('score', 0),
                'location': item.get('location', {}).get('s3Location', {}).get('uri', ''),
                'metadata': item.get('metadata', {})
            }
            results.append(result)
        
        return success_response({
            'results': results,
            'count': len(results),
            'query': query
        })
        
    except Exception as e:
        return error_response(f"Failed to retrieve from knowledge base: {str(e)}")


def retrieve_and_generate(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Query the knowledge base and generate a response using an LLM
    
    Parameters:
    - query (str): The question to answer
    - model_arn (str): Optional model ARN override
    - max_tokens (int): Maximum tokens in response (default: 2048)
    """
    query = params.get('query', '')
    model_arn = params.get('model_arn', MODEL_ARN)
    max_tokens = params.get('max_tokens', 2048)
    
    if not query:
        return error_response("Query parameter is required")
    
    try:
        response = bedrock_agent_runtime.retrieve_and_generate(
            input={'text': query},
            retrieveAndGenerateConfiguration={
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': KNOWLEDGE_BASE_ID,
                    'modelArn': model_arn,
                    'generationConfiguration': {
                        'inferenceConfig': {
                            'textInferenceConfig': {
                                'maxTokens': max_tokens,
                                'temperature': 0.7,
                                'topP': 0.9
                            }
                        }
                    }
                }
            }
        )
        
        output_text = response.get('output', {}).get('text', '')
        
        # Extract citations
        citations = []
        for citation in response.get('citations', []):
            for ref in citation.get('retrievedReferences', []):
                citations.append({
                    'content': ref.get('content', {}).get('text', '')[:500],  # Truncate
                    'location': ref.get('location', {}).get('s3Location', {}).get('uri', ''),
                    'metadata': ref.get('metadata', {})
                })
        
        return success_response({
            'answer': output_text,
            'citations': citations,
            'query': query
        })
        
    except Exception as e:
        return error_response(f"Failed to generate response: {str(e)}")


def list_sources(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    List the available data sources in the knowledge base
    """
    try:
        bedrock_agent = boto3.client('bedrock-agent')
        
        response = bedrock_agent.list_data_sources(
            knowledgeBaseId=KNOWLEDGE_BASE_ID
        )
        
        sources = []
        for source in response.get('dataSourceSummaries', []):
            sources.append({
                'id': source.get('dataSourceId'),
                'name': source.get('name'),
                'status': source.get('status'),
                'updated_at': source.get('updatedAt', '').isoformat() if source.get('updatedAt') else None
            })
        
        return success_response({
            'knowledge_base_id': KNOWLEDGE_BASE_ID,
            'sources': sources
        })
        
    except Exception as e:
        return error_response(f"Failed to list sources: {str(e)}")


def success_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """Format a successful response"""
    return {
        'statusCode': 200,
        'body': json.dumps({
            'success': True,
            'data': data
        }),
        'headers': {
            'Content-Type': 'application/json'
        }
    }


def error_response(message: str, status_code: int = 400) -> Dict[str, Any]:
    """Format an error response"""
    return {
        'statusCode': status_code,
        'body': json.dumps({
            'success': False,
            'error': message
        }),
        'headers': {
            'Content-Type': 'application/json'
        }
    }
```

### 1.2 Create the Lambda Function via AWS CLI

```bash
# Create a deployment package
cd agentcore/lambda
zip -r function.zip knowledge_base_proxy.py

# Create IAM role for Lambda
aws iam create-role \
  --role-name KnowledgeBaseProxyLambdaRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach policies
aws iam attach-role-policy \
  --role-name KnowledgeBaseProxyLambdaRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Create inline policy for Bedrock access
aws iam put-role-policy \
  --role-name KnowledgeBaseProxyLambdaRole \
  --policy-name BedrockKnowledgeBaseAccess \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "bedrock:InvokeModel",
          "bedrock:Retrieve",
          "bedrock:RetrieveAndGenerate"
        ],
        "Resource": "*"
      },
      {
        "Effect": "Allow",
        "Action": [
          "bedrock-agent-runtime:Retrieve",
          "bedrock-agent-runtime:RetrieveAndGenerate"
        ],
        "Resource": "*"
      },
      {
        "Effect": "Allow",
        "Action": [
          "bedrock-agent:ListDataSources",
          "bedrock-agent:GetDataSource"
        ],
        "Resource": "*"
      }
    ]
  }'

# Wait for role to propagate
sleep 10

# Create the Lambda function
aws lambda create-function \
  --function-name KnowledgeBaseProxy \
  --runtime python3.12 \
  --role arn:aws:iam::313117444016:role/KnowledgeBaseProxyLambdaRole \
  --handler knowledge_base_proxy.handler \
  --zip-file fileb://function.zip \
  --timeout 30 \
  --memory-size 256 \
  --environment Variables='{
    "KNOWLEDGE_BASE_ID": "OYBA7PFNNQ",
    "MODEL_ARN": "arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0"
  }' \
  --region us-west-2
```

---

## Step 2: Create the AgentCore Gateway

### 2.1 Create Gateway via AWS Console

1. Navigate to **Amazon Bedrock** → **AgentCore** → **Gateways**
2. Click **Create gateway**
3. Configure:
   - **Name**: `KnowledgeBaseGateway`
   - **Description**: `MCP Gateway for Knowledge Base access`
4. Click **Create**

### 2.2 Create Gateway via AWS CLI

```bash
# Create the AgentCore Gateway
aws bedrock-agentcore create-gateway \
  --name KnowledgeBaseGateway \
  --description "MCP Gateway for proxying Knowledge Base queries" \
  --region us-west-2
```

> **Note**: The exact CLI commands may vary. Check the latest AWS documentation for the current API structure.

---

## Step 3: Configure OAuth Authorization

AgentCore Gateway requires OAuth-based inbound authorization. You can use Amazon Cognito as your OAuth provider.

### 3.1 Create Cognito User Pool

```bash
# Create User Pool
aws cognito-idp create-user-pool \
  --pool-name AgentCoreGatewayPool \
  --policies '{
    "PasswordPolicy": {
      "MinimumLength": 12,
      "RequireUppercase": true,
      "RequireLowercase": true,
      "RequireNumbers": true,
      "RequireSymbols": true
    }
  }' \
  --auto-verified-attributes email \
  --region us-west-2

# Note the UserPoolId from the output
```

### 3.2 Create User Pool Client

```bash
# Create App Client for machine-to-machine auth
aws cognito-idp create-user-pool-client \
  --user-pool-id <USER_POOL_ID> \
  --client-name AgentCoreClient \
  --generate-secret \
  --explicit-auth-flows ALLOW_USER_SRP_AUTH ALLOW_REFRESH_TOKEN_AUTH \
  --allowed-o-auth-flows client_credentials \
  --allowed-o-auth-scopes "agentcore/invoke" \
  --supported-identity-providers COGNITO \
  --region us-west-2

# Note the ClientId and ClientSecret
```

### 3.3 Create Resource Server

```bash
# Create resource server for custom scopes
aws cognito-idp create-resource-server \
  --user-pool-id <USER_POOL_ID> \
  --identifier agentcore \
  --name "AgentCore Gateway API" \
  --scopes '[
    {
      "ScopeName": "invoke",
      "ScopeDescription": "Invoke AgentCore Gateway tools"
    }
  ]' \
  --region us-west-2
```

### 3.4 Create Domain

```bash
# Create a domain for OAuth endpoints
aws cognito-idp create-user-pool-domain \
  --domain knowledge-base-gateway-<ACCOUNT_ID> \
  --user-pool-id <USER_POOL_ID> \
  --region us-west-2
```

### 3.5 Configure Gateway Authorization

In the AgentCore Gateway console:

1. Go to **Inbound Authorization**
2. Select **OAuth 2.0**
3. Configure:
   - **Token Endpoint**: `https://knowledge-base-gateway-<ACCOUNT_ID>.auth.us-west-2.amazoncognito.com/oauth2/token`
   - **Authorization Endpoint**: `https://knowledge-base-gateway-<ACCOUNT_ID>.auth.us-west-2.amazoncognito.com/oauth2/authorize`
   - **Client ID**: Your Cognito App Client ID
   - **Scopes**: `agentcore/invoke`

---

## Step 4: Add Lambda Target to Gateway

### 4.1 Create IAM Role for Gateway

```bash
# Create role for AgentCore Gateway to invoke Lambda
aws iam create-role \
  --role-name AgentCoreGatewayInvokeRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach Lambda invoke policy
aws iam put-role-policy \
  --role-name AgentCoreGatewayInvokeRole \
  --policy-name LambdaInvokePolicy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": "lambda:InvokeFunction",
      "Resource": "arn:aws:lambda:us-west-2:313117444016:function:KnowledgeBaseProxy"
    }]
  }'
```

### 4.2 Define Tool Schemas

Create `agentcore/tool_definitions.json`:

```json
{
  "tools": [
    {
      "name": "query_knowledge_base",
      "description": "Search and retrieve relevant documents from the knowledge base. Use this for finding specific information or documents.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "query": {
            "type": "string",
            "description": "The search query to find relevant documents"
          },
          "max_results": {
            "type": "integer",
            "description": "Maximum number of results to return (1-25)",
            "default": 5,
            "minimum": 1,
            "maximum": 25
          },
          "filter": {
            "type": "object",
            "description": "Optional metadata filter for narrowing results",
            "properties": {
              "andAll": {
                "type": "array",
                "items": {
                  "type": "object"
                }
              }
            }
          }
        },
        "required": ["query"]
      }
    },
    {
      "name": "retrieve_and_generate",
      "description": "Ask a question and get an AI-generated answer based on the knowledge base documents. Includes citations from source documents.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "query": {
            "type": "string",
            "description": "The question to answer using the knowledge base"
          },
          "max_tokens": {
            "type": "integer",
            "description": "Maximum tokens in the generated response",
            "default": 2048,
            "minimum": 100,
            "maximum": 4096
          }
        },
        "required": ["query"]
      }
    },
    {
      "name": "list_sources",
      "description": "List all data sources connected to the knowledge base",
      "inputSchema": {
        "type": "object",
        "properties": {},
        "required": []
      }
    }
  ]
}
```

### 4.3 Add Target via Console

1. Go to your AgentCore Gateway in the console
2. Navigate to **Targets**
3. Click **Add target**
4. Configure:
   - **Target type**: Lambda
   - **Lambda function ARN**: `arn:aws:lambda:us-west-2:313117444016:function:KnowledgeBaseProxy`
   - **Execution role**: `arn:aws:iam::313117444016:role/AgentCoreGatewayInvokeRole`
5. Add each tool from the tool definitions above
6. Click **Save**

---

## Step 5: Connect MCP Clients

### 5.1 Get Gateway Endpoint

After creating the gateway, note the MCP endpoint URL:
```
https://<gateway-id>.agentcore.us-west-2.amazonaws.com/mcp
```

### 5.2 Configure Claude Desktop

Edit `~/.config/claude/claude_desktop_config.json` (macOS/Linux) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "knowledge-base": {
      "url": "https://<gateway-id>.agentcore.us-west-2.amazonaws.com/mcp",
      "transport": "sse",
      "auth": {
        "type": "oauth2",
        "tokenUrl": "https://knowledge-base-gateway-<ACCOUNT_ID>.auth.us-west-2.amazoncognito.com/oauth2/token",
        "clientId": "<COGNITO_CLIENT_ID>",
        "clientSecret": "<COGNITO_CLIENT_SECRET>",
        "scopes": ["agentcore/invoke"]
      }
    }
  }
}
```

### 5.3 Configure Cursor

Edit `.cursor/mcp.json` in your project or global settings:

```json
{
  "mcpServers": {
    "knowledge-base": {
      "url": "https://<gateway-id>.agentcore.us-west-2.amazonaws.com/mcp",
      "transport": "sse",
      "auth": {
        "type": "oauth2",
        "tokenUrl": "https://knowledge-base-gateway-<ACCOUNT_ID>.auth.us-west-2.amazoncognito.com/oauth2/token",
        "clientId": "<COGNITO_CLIENT_ID>",
        "clientSecret": "<COGNITO_CLIENT_SECRET>",
        "scopes": ["agentcore/invoke"]
      }
    }
  }
}
```

### 5.4 Use with Python MCP Client

```python
"""
Example: Using the AgentCore Gateway with a Python MCP client
"""
import asyncio
import httpx
from mcp import ClientSession
from mcp.client.sse import sse_client

async def get_oauth_token(token_url: str, client_id: str, client_secret: str) -> str:
    """Get OAuth access token from Cognito"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            token_url,
            data={
                'grant_type': 'client_credentials',
                'scope': 'agentcore/invoke'
            },
            auth=(client_id, client_secret)
        )
        response.raise_for_status()
        return response.json()['access_token']

async def main():
    # Configuration
    gateway_url = "https://<gateway-id>.agentcore.us-west-2.amazonaws.com/mcp"
    token_url = "https://knowledge-base-gateway-<ACCOUNT_ID>.auth.us-west-2.amazoncognito.com/oauth2/token"
    client_id = "<COGNITO_CLIENT_ID>"
    client_secret = "<COGNITO_CLIENT_SECRET>"
    
    # Get access token
    token = await get_oauth_token(token_url, client_id, client_secret)
    
    # Connect to the gateway
    headers = {"Authorization": f"Bearer {token}"}
    
    async with sse_client(gateway_url, headers=headers) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()
            
            # List available tools
            tools = await session.list_tools()
            print("Available tools:")
            for tool in tools.tools:
                print(f"  - {tool.name}: {tool.description}")
            
            # Query the knowledge base
            result = await session.call_tool(
                "query_knowledge_base",
                arguments={"query": "What is the return policy?", "max_results": 3}
            )
            print(f"\nQuery results: {result}")
            
            # Get an AI-generated answer
            answer = await session.call_tool(
                "retrieve_and_generate",
                arguments={"query": "How do I return a product?"}
            )
            print(f"\nGenerated answer: {answer}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## CDK Implementation

For infrastructure-as-code deployment, add the following to your CDK stack:

### Update `cdk/lib/cdk-stack.ts`

```typescript
import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import * as path from 'path';
import { Construct } from 'constructs';

// Add to your existing CdkStack class:

// ============================================
// AGENTCORE GATEWAY INFRASTRUCTURE
// ============================================

// Lambda function for Knowledge Base proxy
const knowledgeBaseProxyFn = new lambda.Function(this, 'KnowledgeBaseProxyFunction', {
  functionName: 'KnowledgeBaseProxy',
  runtime: lambda.Runtime.PYTHON_3_12,
  handler: 'knowledge_base_proxy.handler',
  code: lambda.Code.fromAsset(path.join(__dirname, '../../agentcore/lambda')),
  timeout: cdk.Duration.seconds(30),
  memorySize: 256,
  environment: {
    KNOWLEDGE_BASE_ID: 'OYBA7PFNNQ',  // Replace with your KB ID or use a parameter
    MODEL_ARN: `arn:aws:bedrock:${cdk.Aws.REGION}::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0`,
  },
});

// Grant Bedrock permissions to Lambda
knowledgeBaseProxyFn.addToRolePolicy(new iam.PolicyStatement({
  effect: iam.Effect.ALLOW,
  actions: [
    'bedrock:InvokeModel',
    'bedrock:Retrieve',
    'bedrock:RetrieveAndGenerate',
    'bedrock-agent-runtime:Retrieve',
    'bedrock-agent-runtime:RetrieveAndGenerate',
    'bedrock-agent:ListDataSources',
    'bedrock-agent:GetDataSource',
  ],
  resources: ['*'],
}));

// Cognito User Pool for OAuth
const userPool = new cognito.UserPool(this, 'AgentCoreUserPool', {
  userPoolName: 'AgentCoreGatewayPool',
  selfSignUpEnabled: false,
  signInAliases: { email: true },
  passwordPolicy: {
    minLength: 12,
    requireUppercase: true,
    requireLowercase: true,
    requireDigits: true,
    requireSymbols: true,
  },
});

// Resource Server for custom scopes
const resourceServer = userPool.addResourceServer('AgentCoreResourceServer', {
  identifier: 'agentcore',
  scopes: [
    { scopeName: 'invoke', scopeDescription: 'Invoke AgentCore Gateway tools' },
  ],
});

// App Client for machine-to-machine auth
const appClient = userPool.addClient('AgentCoreClient', {
  userPoolClientName: 'AgentCoreGatewayClient',
  generateSecret: true,
  oAuth: {
    flows: {
      clientCredentials: true,
    },
    scopes: [
      cognito.OAuthScope.custom('agentcore/invoke'),
    ],
  },
});

appClient.node.addDependency(resourceServer);

// User Pool Domain
const domain = userPool.addDomain('AgentCoreDomain', {
  cognitoDomain: {
    domainPrefix: `knowledge-base-gateway-${cdk.Aws.ACCOUNT_ID}`,
  },
});

// IAM Role for AgentCore Gateway to invoke Lambda
const gatewayInvokeRole = new iam.Role(this, 'AgentCoreGatewayInvokeRole', {
  assumedBy: new iam.ServicePrincipal('bedrock-agentcore.amazonaws.com'),
  description: 'Role for AgentCore Gateway to invoke Lambda functions',
});

gatewayInvokeRole.addToPolicy(new iam.PolicyStatement({
  effect: iam.Effect.ALLOW,
  actions: ['lambda:InvokeFunction'],
  resources: [knowledgeBaseProxyFn.functionArn],
}));

// Outputs
new cdk.CfnOutput(this, 'LambdaFunctionArn', {
  value: knowledgeBaseProxyFn.functionArn,
  description: 'Knowledge Base Proxy Lambda ARN',
});

new cdk.CfnOutput(this, 'CognitoUserPoolId', {
  value: userPool.userPoolId,
  description: 'Cognito User Pool ID',
});

new cdk.CfnOutput(this, 'CognitoClientId', {
  value: appClient.userPoolClientId,
  description: 'Cognito App Client ID',
});

new cdk.CfnOutput(this, 'CognitoTokenUrl', {
  value: `https://${domain.domainName}.auth.${cdk.Aws.REGION}.amazoncognito.com/oauth2/token`,
  description: 'Cognito OAuth Token URL',
});

new cdk.CfnOutput(this, 'GatewayInvokeRoleArn', {
  value: gatewayInvokeRole.roleArn,
  description: 'IAM Role ARN for AgentCore Gateway',
});
```

---

## Testing

### ✅ Deployment Verified (December 25, 2025)

The Lambda function has been successfully deployed and tested with the following results:

#### Deployed Resources

| Resource | Value |
|----------|-------|
| Lambda Function | `arn:aws:lambda:us-west-2:313117444016:function:KnowledgeBaseProxy` |
| Lambda Role | `arn:aws:iam::313117444016:role/KnowledgeBaseProxyLambdaRole` |
| Gateway Invoke Role | `arn:aws:iam::313117444016:role/AgentCoreGatewayInvokeRole` |
| Cognito User Pool | `us-west-2_KCrB4IFHM` |
| Cognito Client ID | `6p0atln929gufjgnfibnttg2st` |
| Token URL | `https://kb-gateway-313117444016.auth.us-west-2.amazoncognito.com/oauth2/token` |

### Test Results

#### Test 1: Query Knowledge Base - China Market

```bash
aws lambda invoke \
  --function-name KnowledgeBaseProxy \
  --payload '{"tool_name": "query_knowledge_base", "tool_input": {"query": "What are the seller guidelines for China market?", "max_results": 3}}' \
  --cli-binary-format raw-in-base64-out \
  --region us-west-2 \
  response_cn.json
```

**Result**: ✅ Success (StatusCode: 200)

```json
{
  "success": true,
  "data": {
    "results": [
      {
        "content": "# Amazon Seller Guide - China Marketplace ## Marketplace: CN (Amazon.cn) **Region**: Asia Pacific **Currency**: CNY (Chinese Yuan) **Language**: Simplified Chinese...",
        "score": 0.5715,
        "location": "s3://knowledge-base-313117444016-us-west-2/documents/seller-guide-cn.md",
        "metadata": {
          "marketplace": "CN",
          "language": "chinese",
          "region": "asia_pacific",
          "document_type": "seller_guide"
        }
      }
    ],
    "count": 3,
    "query": "What are the seller guidelines for China market?",
    "knowledge_base_id": "OYBA7PFNNQ"
  }
}
```

#### Test 2: Query Knowledge Base - US Market

```bash
aws lambda invoke \
  --function-name KnowledgeBaseProxy \
  --payload '{"tool_name": "query_knowledge_base", "tool_input": {"query": "What are the seller guidelines for US market?", "max_results": 3}}' \
  --cli-binary-format raw-in-base64-out \
  --region us-west-2 \
  response_us.json
```

**Result**: ✅ Success (StatusCode: 200)

```json
{
  "success": true,
  "data": {
    "results": [
      {
        "content": "# Amazon Seller Guide - United States Marketplace ## Marketplace: US **Region**: North America **Currency**: USD **Language**: English...",
        "score": 0.5222,
        "location": "s3://knowledge-base-313117444016-us-west-2/documents/seller-guide-us.md",
        "metadata": {
          "marketplace": "US",
          "language": "english",
          "region": "north_america",
          "document_type": "seller_guide"
        }
      }
    ],
    "count": 3,
    "query": "What are the seller guidelines for US market?",
    "knowledge_base_id": "OYBA7PFNNQ"
  }
}
```

#### Test 3: Retrieve and Generate - Compare CN vs US

```bash
aws lambda invoke \
  --function-name KnowledgeBaseProxy \
  --payload '{"tool_name": "retrieve_and_generate", "tool_input": {"query": "What are the key differences between selling on Amazon CN vs US marketplace?", "max_tokens": 1024}}' \
  --cli-binary-format raw-in-base64-out \
  --region us-west-2 \
  response_rag.json
```

**Result**: ✅ Success (StatusCode: 200)

**AI-Generated Answer**:
> Some key differences between selling on the Amazon CN (China) vs US marketplace include:
> 
> 1. **Registration requirements**: For the CN marketplace, you need a Chinese business license, Chinese bank account, and legal representative ID card. For the US, you only need a US bank account/credit card, tax ID number, and business address.
> 
> 2. **Seller types**: The CN marketplace only has a Professional Seller plan (¥300/month), while the US has both Individual (per-item fee) and Professional plans.
> 
> 3. **Product compliance**: The CN marketplace has additional requirements like CCC certification for many products, China Food Safety Law for imported food, cosmetics/medical device registration with NMPA, and import licenses/documentation. The US has requirements like FDA, FCC, CPSC standards.
> 
> 4. **Fulfillment**: Both have Fulfillment by Amazon options, but the CN FBA has fewer warehouses concentrated in major cities, while the US FBA has 175+ warehouses across the country.
> 
> 5. **Marketing tools**: The US has more established marketing tools like Sponsored Products ads, Amazon Vine for reviews, and Lightning Deals. The CN marketplace is still developing these.
> 
> 6. **Cultural considerations**: For the CN market, sellers need to be aware of things like lucky/unlucky numbers, color preferences, gift-giving customs, and major shopping festivals like 11.11 and 6.18.

**Citations**: 5 source documents from both `seller-guide-cn.md` and `seller-guide-us.md`

### Test Commands

```bash
# Test query_knowledge_base
aws lambda invoke \
  --function-name KnowledgeBaseProxy \
  --payload '{"tool_name": "query_knowledge_base", "tool_input": {"query": "Your query here", "max_results": 5}}' \
  --cli-binary-format raw-in-base64-out \
  --region us-west-2 \
  response.json && cat response.json | jq .

# Test retrieve_and_generate
aws lambda invoke \
  --function-name KnowledgeBaseProxy \
  --payload '{"tool_name": "retrieve_and_generate", "tool_input": {"query": "Your question here"}}' \
  --cli-binary-format raw-in-base64-out \
  --region us-west-2 \
  response.json && cat response.json | jq -r '.body | fromjson | .data'

# Test list_sources
aws lambda invoke \
  --function-name KnowledgeBaseProxy \
  --payload '{"tool_name": "list_sources", "tool_input": {}}' \
  --cli-binary-format raw-in-base64-out \
  --region us-west-2 \
  response.json && cat response.json | jq .
```

### Test via MCP Client

Use the Python script from Section 5.4 or configure Claude Desktop/Cursor and test interactively.

---

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `AccessDeniedException` | Missing IAM permissions | Check Lambda role has Bedrock permissions |
| `ResourceNotFoundException` | Invalid Knowledge Base ID | Verify `KNOWLEDGE_BASE_ID` environment variable |
| `ValidationException` | Invalid request format | Check tool input schema matches expected format |
| `ThrottlingException` | Rate limit exceeded | Implement retry logic with exponential backoff |
| `OAuth token invalid` | Expired or incorrect credentials | Refresh token or verify Cognito configuration |

### Enable Debug Logging

Add to Lambda environment variables:
```
LOG_LEVEL=DEBUG
```

Update the Lambda code to use structured logging:

```python
import logging

logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

def handler(event, context):
    logger.debug(f"Event: {json.dumps(event)}")
    # ... rest of handler
```

### View CloudWatch Logs

```bash
aws logs tail /aws/lambda/KnowledgeBaseProxy --follow
```

---

## Security Best Practices

1. **Least Privilege**: Grant only required permissions to IAM roles
2. **Rotate Credentials**: Regularly rotate Cognito client secrets
3. **Enable CloudTrail**: Log all API calls for audit purposes
4. **VPC Deployment**: Consider deploying Lambda in a VPC for network isolation
5. **Input Validation**: Always validate inputs in the Lambda function
6. **Rate Limiting**: Implement request throttling to prevent abuse

---

## Cost Considerations

| Component | Pricing Model |
|-----------|---------------|
| AgentCore Gateway | Per request |
| Lambda | Per invocation + duration |
| Bedrock Knowledge Base | Per retrieve request |
| Bedrock LLM (Claude) | Per input/output token |
| Cognito | Per MAU (monthly active users) |

**Cost Optimization Tips:**
- Use caching for frequent queries
- Set appropriate `max_tokens` limits
- Implement request batching where possible
- Monitor usage with AWS Cost Explorer

---

## Next Steps

1. **Add More Tools**: Extend the Lambda function with additional tools (e.g., document upload, metadata search)
2. **Implement Caching**: Add response caching for common queries
3. **Set Up Monitoring**: Create CloudWatch dashboards and alarms
4. **Enable Tracing**: Add AWS X-Ray for distributed tracing
5. **Automate Deployment**: Create CI/CD pipeline for updates

---

## References

- [Amazon Bedrock AgentCore Gateway Documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway.html)
- [Amazon Bedrock Knowledge Base Developer Guide](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base.html)
- [Model Context Protocol (MCP) Specification](https://modelcontextprotocol.io/)
- [AWS Lambda Developer Guide](https://docs.aws.amazon.com/lambda/latest/dg/)
- [Amazon Cognito Developer Guide](https://docs.aws.amazon.com/cognito/latest/developerguide/)

---

**Created**: December 25, 2025  
**Last Tested**: December 26, 2025 ✅  
**Knowledge Base ID**: OYBA7PFNNQ  
**Region**: us-west-2  
**Lambda Function**: KnowledgeBaseProxy  
**Status**: Deployed and Operational

---

## ✅ AgentCore Gateway Deployment (December 26, 2025)

### Gateway Details

| Resource | Value |
|----------|-------|
| Gateway Name | `KnowledgeBaseGateway` |
| Gateway ID | `knowledgebasegateway-z01bbyrzgr` |
| Status | **READY** |
| MCP Endpoint | `https://knowledgebasegateway-z01bbyrzgr.gateway.bedrock-agentcore.us-west-2.amazonaws.com/mcp` |
| Auth Type | AWS_IAM |
| Protocol | MCP v2025-03-26 |

### Gateway Target

| Resource | Value |
|----------|-------|
| Target Name | `KnowledgeBaseProxyTarget` |
| Target ID | `ALALK0U5YE` |
| Status | **READY** |
| Lambda ARN | `arn:aws:lambda:us-west-2:313117444016:function:KnowledgeBaseProxy` |

### Available Tools via MCP

1. **query_knowledge_base** - Semantic search for documents
2. **retrieve_and_generate** - RAG-based Q&A with citations
3. **list_sources** - List data sources

### MCP Client Configuration

```json
{
  "mcpServers": {
    "knowledge-base": {
      "url": "https://knowledgebasegateway-z01bbyrzgr.gateway.bedrock-agentcore.us-west-2.amazonaws.com/mcp",
      "transport": "sse",
      "auth": {
        "type": "aws_iam",
        "region": "us-west-2"
      }
    }
  }
}
```

### AWS Console

[View Gateway](https://console.aws.amazon.com/bedrock/home?region=us-west-2#/agentcore/gateways/knowledgebasegateway-z01bbyrzgr)

