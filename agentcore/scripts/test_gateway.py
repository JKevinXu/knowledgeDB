#!/usr/bin/env python3
"""
Test script for AgentCore MCP Gateway
Tests the gateway by invoking tools through the Lambda function directly
and via HTTP with AWS SigV4 signing.
"""

import boto3
import json
import argparse
import sys
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import requests

# Configuration
REGION = 'us-west-2'
GATEWAY_ID = 'knowledgebasegateway-z01bbyrzgr'
GATEWAY_URL = f'https://{GATEWAY_ID}.gateway.bedrock-agentcore.{REGION}.amazonaws.com/mcp'
LAMBDA_FUNCTION = 'KnowledgeBaseProxy'


def test_lambda_direct(tool_name: str, tool_input: dict):
    """Test by invoking the Lambda function directly (bypasses gateway)"""
    print(f"\n🔧 Testing Lambda directly: {tool_name}")
    print(f"   Input: {json.dumps(tool_input)}")
    
    client = boto3.client('lambda', region_name=REGION)
    
    payload = {
        'tool_name': tool_name,
        'tool_input': tool_input
    }
    
    response = client.invoke(
        FunctionName=LAMBDA_FUNCTION,
        InvocationType='RequestResponse',
        Payload=json.dumps(payload)
    )
    
    result = json.loads(response['Payload'].read())
    
    if result.get('statusCode') == 200:
        body = json.loads(result['body'])
        print(f"\n✅ Success!")
        print(json.dumps(body, indent=2))
    else:
        print(f"\n❌ Error: {result}")
    
    return result


def test_gateway_mcp(tool_name: str, tool_input: dict):
    """Test by calling the MCP gateway with SigV4 signing"""
    print(f"\n🌐 Testing MCP Gateway: {tool_name}")
    print(f"   Endpoint: {GATEWAY_URL}")
    print(f"   Input: {json.dumps(tool_input)}")
    
    session = boto3.Session(region_name=REGION)
    credentials = session.get_credentials()
    
    # MCP tool call request
    mcp_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": tool_input
        }
    }
    
    # Create signed request
    request = AWSRequest(
        method='POST',
        url=GATEWAY_URL,
        data=json.dumps(mcp_request),
        headers={
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream'
        }
    )
    
    SigV4Auth(credentials, 'bedrock-agentcore', REGION).add_auth(request)
    
    try:
        response = requests.post(
            GATEWAY_URL,
            headers=dict(request.headers),
            data=json.dumps(mcp_request),
            stream=True,
            timeout=30
        )
        
        print(f"\n   Status: {response.status_code}")
        
        if response.status_code == 200:
            print("\n✅ Gateway Response:")
            # Handle SSE stream
            for line in response.iter_lines():
                if line:
                    decoded = line.decode('utf-8')
                    if decoded.startswith('data:'):
                        data = decoded[5:].strip()
                        if data:
                            try:
                                parsed = json.loads(data)
                                print(json.dumps(parsed, indent=2))
                            except:
                                print(data)
                    else:
                        print(decoded)
        else:
            print(f"\n❌ Error: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"\n❌ Request failed: {e}")


def list_tools():
    """List available tools via MCP"""
    print(f"\n📋 Listing MCP Tools...")
    print(f"   Endpoint: {GATEWAY_URL}")
    
    session = boto3.Session(region_name=REGION)
    credentials = session.get_credentials()
    
    # MCP list tools request
    mcp_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {}
    }
    
    request = AWSRequest(
        method='POST',
        url=GATEWAY_URL,
        data=json.dumps(mcp_request),
        headers={
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream'
        }
    )
    
    SigV4Auth(credentials, 'bedrock-agentcore', REGION).add_auth(request)
    
    try:
        response = requests.post(
            GATEWAY_URL,
            headers=dict(request.headers),
            data=json.dumps(mcp_request),
            stream=True,
            timeout=30
        )
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            for line in response.iter_lines():
                if line:
                    decoded = line.decode('utf-8')
                    if decoded.startswith('data:'):
                        data = decoded[5:].strip()
                        if data:
                            try:
                                parsed = json.loads(data)
                                print(json.dumps(parsed, indent=2))
                            except:
                                print(data)
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Request failed: {e}")


def main():
    parser = argparse.ArgumentParser(description='Test AgentCore MCP Gateway')
    parser.add_argument('--mode', choices=['lambda', 'gateway', 'list'], default='lambda',
                       help='Test mode: lambda (direct), gateway (MCP), or list (tools)')
    parser.add_argument('--tool', default='query_knowledge_base',
                       choices=['query_knowledge_base', 'retrieve_and_generate', 'list_sources'],
                       help='Tool to invoke')
    parser.add_argument('--query', default='What are the seller guidelines?',
                       help='Query string for the tool')
    parser.add_argument('--max-results', type=int, default=3,
                       help='Maximum results for query_knowledge_base')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("AGENTCORE MCP GATEWAY - TEST SCRIPT")
    print("=" * 70)
    
    # Build tool input based on tool type
    if args.tool == 'query_knowledge_base':
        tool_input = {'query': args.query, 'max_results': args.max_results}
    elif args.tool == 'retrieve_and_generate':
        tool_input = {'query': args.query}
    else:
        tool_input = {}
    
    if args.mode == 'lambda':
        test_lambda_direct(args.tool, tool_input)
    elif args.mode == 'gateway':
        test_gateway_mcp(args.tool, tool_input)
    elif args.mode == 'list':
        list_tools()
    
    print("\n" + "=" * 70)


if __name__ == '__main__':
    main()

