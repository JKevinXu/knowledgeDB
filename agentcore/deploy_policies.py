#!/usr/bin/env python3
"""
Deploy basic policies to AgentCore Gateway.

Usage:
    python deploy_policies.py         # LOG mode (test)
    python deploy_policies.py --enforce  # ENFORCE mode (production)
"""

import boto3
import sys
from pathlib import Path

REGION = 'us-west-2'
GATEWAY_ID = 'knowledgebasegatewayoauth2-pf7rmcexrm'
POLICY_FILE = Path(__file__).parent / 'policies' / 'knowledge_base_policies.cedar'


def main():
    enforce = '--enforce' in sys.argv
    mode = 'ENFORCE' if enforce else 'LOG'
    
    print(f"Deploying policies ({mode} mode)...")
    
    # Read policy file
    policy_content = POLICY_FILE.read_text()
    print(f"✓ Read policy: {POLICY_FILE}")
    
    client = boto3.client('bedrock-agentcore-control', region_name=REGION)
    
    # Create policy engine
    try:
        resp = client.create_policy_engine(
            name='KnowledgeBasePolicyEngine',
            description='Basic access control for KB Gateway'
        )
        engine_id = resp['policyEngineId']
        print(f"✓ Created policy engine: {engine_id}")
    except client.exceptions.ConflictException:
        # Already exists - get it
        engines = client.list_policy_engines()['policyEngines']
        engine_id = next(e['policyEngineId'] for e in engines 
                        if e['name'] == 'KnowledgeBasePolicyEngine')
        print(f"✓ Using existing policy engine: {engine_id}")
    
    # Create/update policy
    try:
        client.create_policy(
            policyEngineId=engine_id,
            name='BasicAccessPolicy',
            policyType='CEDAR',
            policyContent=policy_content,
            enabled=True
        )
        print("✓ Created policy")
    except client.exceptions.ConflictException:
        # Update existing
        policies = client.list_policies(policyEngineId=engine_id)['policies']
        policy_id = next(p['policyId'] for p in policies 
                        if p['name'] == 'BasicAccessPolicy')
        client.update_policy(
            policyEngineId=engine_id,
            policyId=policy_id,
            policyContent=policy_content
        )
        print("✓ Updated policy")
    
    # Attach to gateway
    client.update_gateway(
        gatewayIdentifier=GATEWAY_ID,
        policyEngineId=engine_id,
        policyEnforcementMode=mode
    )
    print(f"✓ Attached to gateway ({mode})")
    
    print(f"\n✅ Done! Policy is {'active' if enforce else 'logging only'}.")
    if not enforce:
        print("   Run with --enforce when ready for production.")


if __name__ == '__main__':
    main()
