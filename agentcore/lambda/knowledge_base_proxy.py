"""
Knowledge Base Proxy Lambda Function
Handles MCP tool calls from AgentCore Gateway and proxies to Bedrock Knowledge Base

This Lambda function provides three tools:
1. query_knowledge_base - Semantic search for relevant documents
2. retrieve_and_generate - RAG-based Q&A with citations
3. list_sources - List connected data sources
"""

import json
import boto3
import os
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# Initialize clients
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')
bedrock_agent = boto3.client('bedrock-agent')

# Configuration from environment variables
KNOWLEDGE_BASE_ID = os.environ.get('KNOWLEDGE_BASE_ID', 'OYBA7PFNNQ')
MODEL_ARN = os.environ.get(
    'MODEL_ARN', 
    f"arn:aws:bedrock:{os.environ.get('AWS_REGION', 'us-west-2')}::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0"
)
DEFAULT_MAX_RESULTS = int(os.environ.get('DEFAULT_MAX_RESULTS', '5'))
DEFAULT_MAX_TOKENS = int(os.environ.get('DEFAULT_MAX_TOKENS', '2048'))


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for AgentCore Gateway requests.
    
    The AgentCore Gateway sends requests in the following format:
    {
        "tool_name": "query_knowledge_base",
        "tool_input": {
            "query": "What is the shipping policy?",
            "max_results": 5
        }
    }
    
    Or alternatively:
    {
        "name": "query_knowledge_base",
        "input": {...}
    }
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    try:
        # Handle different event formats from AgentCore Gateway
        tool_name = event.get('tool_name') or event.get('name', '')
        tool_input = event.get('tool_input') or event.get('input', {})
        
        # Also handle direct invocation format
        if not tool_name and 'action' in event:
            tool_name = event['action']
            tool_input = event.get('parameters', {})
        
        logger.info(f"Processing tool: {tool_name} with input: {json.dumps(tool_input)}")
        
        # Route to appropriate handler
        handlers = {
            'query_knowledge_base': query_knowledge_base,
            'retrieve_and_generate': retrieve_and_generate,
            'list_sources': list_sources,
            'get_knowledge_base_info': get_knowledge_base_info,
        }
        
        if tool_name in handlers:
            return handlers[tool_name](tool_input)
        else:
            return error_response(
                f"Unknown tool: '{tool_name}'. Available tools: {list(handlers.keys())}"
            )
            
    except Exception as e:
        logger.exception(f"Error processing request: {str(e)}")
        return error_response(str(e), status_code=500)


def query_knowledge_base(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Retrieve relevant documents from the knowledge base using semantic search.
    
    Parameters:
    - query (str): The search query (required)
    - max_results (int): Maximum number of results to return (default: 5, max: 25)
    - filter (dict): Optional metadata filter for narrowing results
    
    Returns:
    - results: List of matching documents with content, score, and metadata
    - count: Number of results returned
    - query: The original search query
    """
    query = params.get('query', '').strip()
    max_results = min(params.get('max_results', DEFAULT_MAX_RESULTS), 25)
    metadata_filter = params.get('filter')
    
    if not query:
        return error_response("The 'query' parameter is required and cannot be empty")
    
    logger.info(f"Querying knowledge base with: '{query}', max_results: {max_results}")
    
    retrieve_params = {
        'knowledgeBaseId': KNOWLEDGE_BASE_ID,
        'retrievalQuery': {
            'text': query
        },
        'retrievalConfiguration': {
            'vectorSearchConfiguration': {
                'numberOfResults': max_results
            }
        }
    }
    
    # Add metadata filter if provided
    if metadata_filter:
        retrieve_params['retrievalConfiguration']['vectorSearchConfiguration']['filter'] = metadata_filter
        logger.info(f"Applying metadata filter: {json.dumps(metadata_filter)}")
    
    try:
        response = bedrock_agent_runtime.retrieve(**retrieve_params)
        
        results = []
        for item in response.get('retrievalResults', []):
            result = {
                'content': item.get('content', {}).get('text', ''),
                'score': round(item.get('score', 0), 4),
                'location': extract_location(item.get('location', {})),
                'metadata': item.get('metadata', {})
            }
            results.append(result)
        
        logger.info(f"Retrieved {len(results)} results")
        
        return success_response({
            'results': results,
            'count': len(results),
            'query': query,
            'knowledge_base_id': KNOWLEDGE_BASE_ID
        })
        
    except bedrock_agent_runtime.exceptions.ValidationException as e:
        return error_response(f"Invalid request: {str(e)}")
    except bedrock_agent_runtime.exceptions.ResourceNotFoundException as e:
        return error_response(f"Knowledge base not found: {str(e)}")
    except Exception as e:
        logger.exception("Failed to retrieve from knowledge base")
        return error_response(f"Failed to retrieve from knowledge base: {str(e)}")


def retrieve_and_generate(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Query the knowledge base and generate an AI response using RAG.
    
    This function retrieves relevant documents and uses Claude to generate
    a comprehensive answer with citations.
    
    Parameters:
    - query (str): The question to answer (required)
    - model_arn (str): Optional model ARN override
    - max_tokens (int): Maximum tokens in response (default: 2048, max: 4096)
    - temperature (float): Response randomness (default: 0.7)
    
    Returns:
    - answer: The AI-generated response
    - citations: List of source documents used
    - query: The original question
    """
    query = params.get('query', '').strip()
    model_arn = params.get('model_arn', MODEL_ARN)
    max_tokens = min(params.get('max_tokens', DEFAULT_MAX_TOKENS), 4096)
    temperature = params.get('temperature', 0.7)
    
    if not query:
        return error_response("The 'query' parameter is required and cannot be empty")
    
    logger.info(f"Retrieve and generate for: '{query}'")
    
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
                                'temperature': temperature,
                                'topP': 0.9
                            }
                        }
                    }
                }
            }
        )
        
        output_text = response.get('output', {}).get('text', '')
        
        # Extract and format citations
        citations = []
        for citation in response.get('citations', []):
            for ref in citation.get('retrievedReferences', []):
                content_text = ref.get('content', {}).get('text', '')
                citations.append({
                    'content': content_text[:500] + ('...' if len(content_text) > 500 else ''),
                    'location': extract_location(ref.get('location', {})),
                    'metadata': ref.get('metadata', {})
                })
        
        logger.info(f"Generated response with {len(citations)} citations")
        
        return success_response({
            'answer': output_text,
            'citations': citations,
            'citation_count': len(citations),
            'query': query,
            'model': model_arn.split('/')[-1] if '/' in model_arn else model_arn
        })
        
    except bedrock_agent_runtime.exceptions.ValidationException as e:
        return error_response(f"Invalid request: {str(e)}")
    except bedrock_agent_runtime.exceptions.ThrottlingException as e:
        return error_response("Service is busy, please try again in a moment", status_code=429)
    except Exception as e:
        logger.exception("Failed to generate response")
        return error_response(f"Failed to generate response: {str(e)}")


def list_sources(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    List all data sources connected to the knowledge base.
    
    Returns information about each data source including:
    - Data source ID
    - Name
    - Status
    - Last updated timestamp
    """
    logger.info("Listing data sources")
    
    try:
        response = bedrock_agent.list_data_sources(
            knowledgeBaseId=KNOWLEDGE_BASE_ID
        )
        
        sources = []
        for source in response.get('dataSourceSummaries', []):
            updated_at = source.get('updatedAt')
            sources.append({
                'id': source.get('dataSourceId'),
                'name': source.get('name'),
                'status': source.get('status'),
                'updated_at': updated_at.isoformat() if updated_at else None,
                'description': source.get('description', '')
            })
        
        return success_response({
            'knowledge_base_id': KNOWLEDGE_BASE_ID,
            'sources': sources,
            'count': len(sources)
        })
        
    except Exception as e:
        logger.exception("Failed to list sources")
        return error_response(f"Failed to list sources: {str(e)}")


def get_knowledge_base_info(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get information about the knowledge base configuration.
    
    Returns:
    - Knowledge base details (name, description, status)
    - Storage configuration
    - Embedding model information
    """
    logger.info("Getting knowledge base info")
    
    try:
        response = bedrock_agent.get_knowledge_base(
            knowledgeBaseId=KNOWLEDGE_BASE_ID
        )
        
        kb = response.get('knowledgeBase', {})
        
        return success_response({
            'id': kb.get('knowledgeBaseId'),
            'name': kb.get('name'),
            'description': kb.get('description'),
            'status': kb.get('status'),
            'created_at': kb.get('createdAt').isoformat() if kb.get('createdAt') else None,
            'updated_at': kb.get('updatedAt').isoformat() if kb.get('updatedAt') else None,
            'storage_type': kb.get('storageConfiguration', {}).get('type'),
            'embedding_model': kb.get('knowledgeBaseConfiguration', {})
                               .get('vectorKnowledgeBaseConfiguration', {})
                               .get('embeddingModelArn', '').split('/')[-1]
        })
        
    except Exception as e:
        logger.exception("Failed to get knowledge base info")
        return error_response(f"Failed to get knowledge base info: {str(e)}")


def extract_location(location: Dict[str, Any]) -> str:
    """Extract a readable location string from the location object."""
    if 's3Location' in location:
        return location['s3Location'].get('uri', '')
    elif 'webLocation' in location:
        return location['webLocation'].get('url', '')
    elif 'confluenceLocation' in location:
        return location['confluenceLocation'].get('url', '')
    elif 'salesforceLocation' in location:
        return location['salesforceLocation'].get('url', '')
    elif 'sharePointLocation' in location:
        return location['sharePointLocation'].get('url', '')
    return str(location)


def success_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format a successful response for the AgentCore Gateway.
    
    The response follows a standard format that the gateway can parse
    and return to the MCP client.
    """
    return {
        'statusCode': 200,
        'body': json.dumps({
            'success': True,
            'data': data,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }),
        'headers': {
            'Content-Type': 'application/json'
        }
    }


def error_response(message: str, status_code: int = 400) -> Dict[str, Any]:
    """
    Format an error response for the AgentCore Gateway.
    
    Error responses include a descriptive message and appropriate
    HTTP status code.
    """
    logger.error(f"Error response ({status_code}): {message}")
    
    return {
        'statusCode': status_code,
        'body': json.dumps({
            'success': False,
            'error': message,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }),
        'headers': {
            'Content-Type': 'application/json'
        }
    }


# For local testing
if __name__ == '__main__':
    # Test query_knowledge_base
    test_event = {
        'tool_name': 'query_knowledge_base',
        'tool_input': {
            'query': 'What is the return policy?',
            'max_results': 3
        }
    }
    
    print("Testing query_knowledge_base:")
    result = handler(test_event, None)
    print(json.dumps(json.loads(result['body']), indent=2))

