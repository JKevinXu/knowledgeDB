#!/bin/bash
#
# AgentCore MCP Gateway Deployment Script
# This script deploys the Lambda function and supporting infrastructure
# for the AgentCore MCP Gateway to Knowledge Base integration.
#
# Prerequisites:
# - AWS CLI configured with appropriate permissions
# - Python 3.12+ installed
# - zip command available
#
# Usage: ./deploy_gateway.sh [KNOWLEDGE_BASE_ID] [REGION]

set -e

# Configuration
KNOWLEDGE_BASE_ID="${1:-OYBA7PFNNQ}"
REGION="${2:-us-west-2}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
LAMBDA_FUNCTION_NAME="KnowledgeBaseProxy"
LAMBDA_ROLE_NAME="KnowledgeBaseProxyLambdaRole"
GATEWAY_INVOKE_ROLE_NAME="AgentCoreGatewayInvokeRole"
COGNITO_POOL_NAME="AgentCoreGatewayPool"

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║           AGENTCORE MCP GATEWAY - DEPLOYMENT SCRIPT                   ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Configuration:"
echo "  • Knowledge Base ID: ${KNOWLEDGE_BASE_ID}"
echo "  • Region: ${REGION}"
echo "  • Account ID: ${ACCOUNT_ID}"
echo ""

# Change to script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ============================================
# Step 1: Create Lambda Deployment Package
# ============================================
echo "📦 Step 1: Creating Lambda deployment package..."

cd lambda
rm -f function.zip
zip -r function.zip knowledge_base_proxy.py
cd ..

echo "   ✅ Deployment package created"

# ============================================
# Step 2: Create IAM Role for Lambda
# ============================================
echo ""
echo "🔐 Step 2: Creating IAM role for Lambda..."

# Check if role exists
if aws iam get-role --role-name ${LAMBDA_ROLE_NAME} 2>/dev/null; then
    echo "   ℹ️  Role ${LAMBDA_ROLE_NAME} already exists, updating policies..."
else
    aws iam create-role \
        --role-name ${LAMBDA_ROLE_NAME} \
        --assume-role-policy-document '{
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }]
        }' \
        --region ${REGION}
    echo "   ✅ IAM role created"
    
    # Wait for role to propagate
    echo "   ⏳ Waiting for role to propagate..."
    sleep 10
fi

# Attach basic Lambda execution policy
aws iam attach-role-policy \
    --role-name ${LAMBDA_ROLE_NAME} \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole 2>/dev/null || true

# Create/update Bedrock access policy
aws iam put-role-policy \
    --role-name ${LAMBDA_ROLE_NAME} \
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
                    "bedrock-agent:GetDataSource",
                    "bedrock-agent:GetKnowledgeBase"
                ],
                "Resource": "*"
            }
        ]
    }'

echo "   ✅ IAM policies configured"

# ============================================
# Step 3: Create/Update Lambda Function
# ============================================
echo ""
echo "⚡ Step 3: Deploying Lambda function..."

LAMBDA_ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${LAMBDA_ROLE_NAME}"

# Check if function exists
if aws lambda get-function --function-name ${LAMBDA_FUNCTION_NAME} --region ${REGION} 2>/dev/null; then
    echo "   ℹ️  Function exists, updating code..."
    aws lambda update-function-code \
        --function-name ${LAMBDA_FUNCTION_NAME} \
        --zip-file fileb://lambda/function.zip \
        --region ${REGION} > /dev/null
    
    # Wait for update to complete
    aws lambda wait function-updated \
        --function-name ${LAMBDA_FUNCTION_NAME} \
        --region ${REGION}
    
    # Update configuration
    aws lambda update-function-configuration \
        --function-name ${LAMBDA_FUNCTION_NAME} \
        --environment "Variables={KNOWLEDGE_BASE_ID=${KNOWLEDGE_BASE_ID},MODEL_ARN=arn:aws:bedrock:${REGION}::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0}" \
        --region ${REGION} > /dev/null
else
    # Wait a bit more for role propagation if creating new function
    sleep 5
    
    aws lambda create-function \
        --function-name ${LAMBDA_FUNCTION_NAME} \
        --runtime python3.12 \
        --role ${LAMBDA_ROLE_ARN} \
        --handler knowledge_base_proxy.handler \
        --zip-file fileb://lambda/function.zip \
        --timeout 30 \
        --memory-size 256 \
        --environment "Variables={KNOWLEDGE_BASE_ID=${KNOWLEDGE_BASE_ID},MODEL_ARN=arn:aws:bedrock:${REGION}::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0}" \
        --region ${REGION} > /dev/null
fi

LAMBDA_ARN="arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:${LAMBDA_FUNCTION_NAME}"
echo "   ✅ Lambda function deployed: ${LAMBDA_ARN}"

# ============================================
# Step 4: Create IAM Role for AgentCore Gateway
# ============================================
echo ""
echo "🔐 Step 4: Creating IAM role for AgentCore Gateway..."

if aws iam get-role --role-name ${GATEWAY_INVOKE_ROLE_NAME} 2>/dev/null; then
    echo "   ℹ️  Role ${GATEWAY_INVOKE_ROLE_NAME} already exists, updating policies..."
else
    aws iam create-role \
        --role-name ${GATEWAY_INVOKE_ROLE_NAME} \
        --assume-role-policy-document '{
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }]
        }' \
        --region ${REGION}
    echo "   ✅ Gateway invoke role created"
fi

aws iam put-role-policy \
    --role-name ${GATEWAY_INVOKE_ROLE_NAME} \
    --policy-name LambdaInvokePolicy \
    --policy-document "{
        \"Version\": \"2012-10-17\",
        \"Statement\": [{
            \"Effect\": \"Allow\",
            \"Action\": \"lambda:InvokeFunction\",
            \"Resource\": \"${LAMBDA_ARN}\"
        }]
    }"

GATEWAY_ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${GATEWAY_INVOKE_ROLE_NAME}"
echo "   ✅ Gateway invoke policies configured"

# ============================================
# Step 5: Create Cognito User Pool (Optional)
# ============================================
echo ""
echo "🔑 Step 5: Creating Cognito User Pool for OAuth..."

# Check if pool exists
EXISTING_POOL=$(aws cognito-idp list-user-pools --max-results 60 --region ${REGION} \
    --query "UserPools[?Name=='${COGNITO_POOL_NAME}'].Id" --output text 2>/dev/null || echo "")

if [ -n "$EXISTING_POOL" ] && [ "$EXISTING_POOL" != "None" ]; then
    USER_POOL_ID="$EXISTING_POOL"
    echo "   ℹ️  User pool already exists: ${USER_POOL_ID}"
else
    USER_POOL_ID=$(aws cognito-idp create-user-pool \
        --pool-name ${COGNITO_POOL_NAME} \
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
        --region ${REGION} \
        --query 'UserPool.Id' --output text)
    echo "   ✅ User pool created: ${USER_POOL_ID}"
    
    # Create resource server
    aws cognito-idp create-resource-server \
        --user-pool-id ${USER_POOL_ID} \
        --identifier agentcore \
        --name "AgentCore Gateway API" \
        --scopes '[{"ScopeName": "invoke", "ScopeDescription": "Invoke AgentCore Gateway tools"}]' \
        --region ${REGION} > /dev/null 2>&1 || true
    
    echo "   ✅ Resource server created"
fi

# Create/get app client
EXISTING_CLIENT=$(aws cognito-idp list-user-pool-clients \
    --user-pool-id ${USER_POOL_ID} \
    --max-results 60 \
    --region ${REGION} \
    --query "UserPoolClients[?ClientName=='AgentCoreGatewayClient'].ClientId" \
    --output text 2>/dev/null || echo "")

if [ -n "$EXISTING_CLIENT" ] && [ "$EXISTING_CLIENT" != "None" ]; then
    CLIENT_ID="$EXISTING_CLIENT"
    echo "   ℹ️  App client already exists: ${CLIENT_ID}"
else
    CLIENT_RESPONSE=$(aws cognito-idp create-user-pool-client \
        --user-pool-id ${USER_POOL_ID} \
        --client-name AgentCoreGatewayClient \
        --generate-secret \
        --allowed-o-auth-flows client_credentials \
        --allowed-o-auth-scopes "agentcore/invoke" \
        --allowed-o-auth-flows-user-pool-client \
        --supported-identity-providers COGNITO \
        --region ${REGION})
    
    CLIENT_ID=$(echo "$CLIENT_RESPONSE" | jq -r '.UserPoolClient.ClientId')
    CLIENT_SECRET=$(echo "$CLIENT_RESPONSE" | jq -r '.UserPoolClient.ClientSecret')
    echo "   ✅ App client created: ${CLIENT_ID}"
fi

# Create domain
DOMAIN_PREFIX="kb-gateway-${ACCOUNT_ID}"
aws cognito-idp create-user-pool-domain \
    --domain ${DOMAIN_PREFIX} \
    --user-pool-id ${USER_POOL_ID} \
    --region ${REGION} 2>/dev/null || true

TOKEN_URL="https://${DOMAIN_PREFIX}.auth.${REGION}.amazoncognito.com/oauth2/token"

# ============================================
# Summary
# ============================================
echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                      ✅ DEPLOYMENT COMPLETE!                          ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "📋 DEPLOYED RESOURCES:"
echo ""
echo "Lambda Function:"
echo "  • Name: ${LAMBDA_FUNCTION_NAME}"
echo "  • ARN: ${LAMBDA_ARN}"
echo ""
echo "IAM Roles:"
echo "  • Lambda Role: ${LAMBDA_ROLE_ARN}"
echo "  • Gateway Invoke Role: ${GATEWAY_ROLE_ARN}"
echo ""
echo "Cognito (OAuth):"
echo "  • User Pool ID: ${USER_POOL_ID}"
echo "  • Client ID: ${CLIENT_ID}"
echo "  • Token URL: ${TOKEN_URL}"
echo ""
echo "📝 NEXT STEPS:"
echo ""
echo "1. Create AgentCore Gateway in the AWS Console:"
echo "   https://console.aws.amazon.com/bedrock/home?region=${REGION}#/agentcore/gateways"
echo ""
echo "2. Add Lambda target with:"
echo "   • Lambda ARN: ${LAMBDA_ARN}"
echo "   • Execution Role: ${GATEWAY_ROLE_ARN}"
echo ""
echo "3. Configure OAuth authorization with:"
echo "   • Token URL: ${TOKEN_URL}"
echo "   • Client ID: ${CLIENT_ID}"
echo ""
echo "4. Get your client secret (if you need it again):"
echo "   aws cognito-idp describe-user-pool-client \\"
echo "     --user-pool-id ${USER_POOL_ID} \\"
echo "     --client-id ${CLIENT_ID} \\"
echo "     --region ${REGION} \\"
echo "     --query 'UserPoolClient.ClientSecret' --output text"
echo ""
echo "5. Test the Lambda function:"
echo "   aws lambda invoke \\"
echo "     --function-name ${LAMBDA_FUNCTION_NAME} \\"
echo "     --payload '{\"tool_name\": \"list_sources\", \"tool_input\": {}}' \\"
echo "     --cli-binary-format raw-in-base64-out \\"
echo "     response.json && cat response.json | jq ."
echo ""
echo "📚 See AGENTCORE_MCP_GATEWAY_GUIDE.md for complete documentation."
echo ""

