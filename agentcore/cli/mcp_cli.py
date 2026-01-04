#!/usr/bin/env python3
"""
MCP Gateway CLI - Command-line interface for testing the Knowledge Base MCP Gateway

Usage:
    ./mcp_cli.py query "your search query"
    ./mcp_cli.py ask "your question"
    ./mcp_cli.py list-tools
    ./mcp_cli.py list-sources
"""

import boto3
import json
import argparse
import sys
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

# Configuration
REGION = 'us-west-2'
GATEWAY_ID = 'knowledgebasegateway-z01bbyrzgr'
GATEWAY_URL = f'https://{GATEWAY_ID}.gateway.bedrock-agentcore.{REGION}.amazonaws.com/mcp'
TARGET_PREFIX = 'KnowledgeBaseProxyTarget___'


def get_credentials():
    session = boto3.Session(region_name=REGION)
    return session.get_credentials()


def send_mcp_request(method: str, params: dict, timeout: int = 120) -> dict:
    """Send an MCP request to the gateway with AWS SigV4 signing"""
    credentials = get_credentials()
    
    mcp_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params
    }
    
    request = AWSRequest(
        method='POST',
        url=GATEWAY_URL,
        data=json.dumps(mcp_request),
        headers={'Content-Type': 'application/json'}
    )
    
    SigV4Auth(credentials, 'bedrock-agentcore', REGION).add_auth(request)
    
    response = requests.post(
        GATEWAY_URL,
        headers=dict(request.headers),
        data=json.dumps(mcp_request),
        timeout=timeout
    )
    
    return response.json()


def parse_lambda_response(result: dict) -> dict:
    """Parse the nested Lambda response from MCP content"""
    if 'result' not in result:
        return {'error': result.get('error', 'Unknown error')}
    
    content = result['result'].get('content', [])
    for item in content:
        if item.get('type') == 'text':
            try:
                data = json.loads(item.get('text', '{}'))
                body = json.loads(data.get('body', '{}'))
                return body
            except:
                return {'error': 'Failed to parse response', 'raw': item.get('text', '')}
    
    return {'error': 'No content in response'}


def cmd_query(args):
    """Search the knowledge base"""
    print(f"\n🔍 Searching: '{args.query}'")
    print(f"   Max results: {args.max_results}\n")
    
    result = send_mcp_request("tools/call", {
        "name": f"{TARGET_PREFIX}query_knowledge_base",
        "arguments": {
            "query": args.query,
            "max_results": args.max_results
        }
    })
    
    body = parse_lambda_response(result)
    
    if body.get('success'):
        results = body.get('data', {}).get('results', [])
        print(f"✅ Found {len(results)} documents:\n")
        
        for i, r in enumerate(results, 1):
            print(f"[{i}] Score: {r.get('score', 0):.4f}")
            print(f"    Source: {r.get('location', 'Unknown')}")
            
            metadata = r.get('metadata', {})
            meta_str = ', '.join([f"{k}={v}" for k, v in metadata.items() 
                                 if not k.startswith('x-amz')])
            if meta_str:
                print(f"    Metadata: {meta_str}")
            
            content = r.get('content', '')[:200]
            print(f"    Content: {content}...")
            print()
    else:
        print(f"❌ Error: {body.get('error', 'Unknown error')}")


def cmd_ask(args):
    """Ask a question (RAG)"""
    print(f"\n🤖 Question: '{args.question}'")
    print("   Generating answer...\n")
    
    result = send_mcp_request("tools/call", {
        "name": f"{TARGET_PREFIX}retrieve_and_generate",
        "arguments": {
            "query": args.question,
            "max_tokens": args.max_tokens
        }
    }, timeout=180)
    
    body = parse_lambda_response(result)
    
    if body.get('success'):
        data = body.get('data', {})
        answer = data.get('answer', 'No answer generated')
        citations = data.get('citations', [])
        
        print("=" * 60)
        print("ANSWER")
        print("=" * 60)
        print(answer)
        print()
        
        if citations:
            print(f"📚 Sources ({len(citations)} citations):")
            seen = set()
            for c in citations:
                loc = c.get('location', '')
                if loc and loc not in seen:
                    seen.add(loc)
                    print(f"   • {loc.split('/')[-1]}")
    else:
        print(f"❌ Error: {body.get('error', 'Unknown error')}")


def cmd_list_tools(args):
    """List available MCP tools"""
    print("\n📋 Fetching available tools...\n")
    
    result = send_mcp_request("tools/list", {})
    
    if 'result' in result:
        tools = result['result'].get('tools', [])
        print(f"Found {len(tools)} tools:\n")
        
        for tool in tools:
            name = tool.get('name', 'Unknown')
            desc = tool.get('description', 'No description')[:70]
            
            # Clean up the name for display
            display_name = name.replace(TARGET_PREFIX, '') if TARGET_PREFIX in name else name
            
            print(f"• {display_name}")
            print(f"  {desc}...")
            print()
    else:
        print(f"❌ Error: {result.get('error', 'Unknown error')}")


def cmd_list_sources(args):
    """List knowledge base data sources"""
    print("\n📁 Fetching data sources...\n")
    
    result = send_mcp_request("tools/call", {
        "name": f"{TARGET_PREFIX}list_sources",
        "arguments": {}
    })
    
    body = parse_lambda_response(result)
    
    if body.get('success'):
        data = body.get('data', {})
        sources = data.get('sources', [])
        kb_id = data.get('knowledge_base_id', 'Unknown')
        
        print(f"Knowledge Base: {kb_id}")
        print(f"Data Sources: {len(sources)}\n")
        
        for s in sources:
            print(f"• {s.get('name', 'Unknown')}")
            print(f"  ID: {s.get('id', 'Unknown')}")
            print(f"  Status: {s.get('status', 'Unknown')}")
            if s.get('updated_at'):
                print(f"  Updated: {s.get('updated_at')}")
            print()
    else:
        print(f"❌ Error: {body.get('error', 'Unknown error')}")


def main():
    parser = argparse.ArgumentParser(
        description='MCP Gateway CLI for Knowledge Base',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s query "seller requirements for US"
  %(prog)s ask "What are the differences between CN and US marketplaces?"
  %(prog)s list-tools
  %(prog)s list-sources
        '''
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Query command
    query_parser = subparsers.add_parser('query', help='Search the knowledge base')
    query_parser.add_argument('query', help='Search query')
    query_parser.add_argument('-n', '--max-results', type=int, default=5,
                             help='Maximum number of results (default: 5)')
    query_parser.set_defaults(func=cmd_query)
    
    # Ask command
    ask_parser = subparsers.add_parser('ask', help='Ask a question (RAG)')
    ask_parser.add_argument('question', help='Question to ask')
    ask_parser.add_argument('-t', '--max-tokens', type=int, default=1024,
                           help='Maximum tokens in response (default: 1024)')
    ask_parser.set_defaults(func=cmd_ask)
    
    # List tools command
    tools_parser = subparsers.add_parser('list-tools', help='List available MCP tools')
    tools_parser.set_defaults(func=cmd_list_tools)
    
    # List sources command
    sources_parser = subparsers.add_parser('list-sources', help='List data sources')
    sources_parser.set_defaults(func=cmd_list_sources)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    print("=" * 60)
    print("MCP GATEWAY CLI - Knowledge Base")
    print(f"Endpoint: {GATEWAY_URL}")
    print("=" * 60)
    
    try:
        args.func(args)
    except requests.exceptions.Timeout:
        print("\n❌ Request timed out. Try again or increase timeout.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    
    print()


if __name__ == '__main__':
    main()

