# AgentCore MCP Gateway

This directory contains the AgentCore MCP Gateway integration for the Knowledge Base.

## Directory Structure

```
agentcore/
├── lambda/                    # Lambda function for KB proxy
│   ├── knowledge_base_proxy.py
│   └── requirements.txt
├── scripts/                   # Deployment and management scripts
│   ├── create_gateway.py      # Create AgentCore Gateway
│   ├── deploy_gateway.sh      # Deploy Lambda and dependencies
│   ├── deploy_policies.py     # Deploy Cedar policies
│   └── test_gateway.py        # Test gateway functionality
├── cli/                       # Command-line tools
│   └── mcp_cli.py             # CLI for querying via MCP
├── policies/                  # Cedar policy files
│   └── knowledge_base_policies.cedar
└── tool_definitions.json      # MCP tool schemas
```

## Quick Start

### 1. Deploy the Lambda Function

```bash
cd scripts
./deploy_gateway.sh
```

### 2. Create the Gateway

```bash
python scripts/create_gateway.py
```

### 3. Test the Gateway

```bash
python scripts/test_gateway.py --mode lambda --query "What are the seller guidelines?"
```

### 4. Use the CLI

```bash
python cli/mcp_cli.py query "seller requirements for US"
python cli/mcp_cli.py ask "What are the differences between CN and US marketplaces?"
```

## Gateway Endpoints

| Gateway | Auth Type | Endpoint |
|---------|-----------|----------|
| IAM | AWS SigV4 | `knowledgebasegateway-z01bbyrzgr` |
| OAuth | OAuth 2.0 | `knowledgebasegatewayoauth2-pf7rmcexrm` |

## Available Tools

- **query_knowledge_base** - Semantic search for documents
- **retrieve_and_generate** - RAG-based Q&A with citations
- **list_sources** - List connected data sources
- **get_knowledge_base_info** - Get KB configuration details

## Documentation

For comprehensive documentation, see [GUIDE_agentcore_gateway.md](../GUIDE_agentcore_gateway.md).

