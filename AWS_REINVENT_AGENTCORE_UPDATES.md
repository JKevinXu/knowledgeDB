# AWS re:Invent 2025 - AgentCore Updates Summary

## Overview

At **AWS re:Invent 2025**, Amazon Web Services introduced significant enhancements to **Amazon Bedrock AgentCore**, aimed at streamlining the development, deployment, and management of AI agents at enterprise scale.

AgentCore is positioned as a comprehensive platform addressing the critical challenge of moving AI agents from prototype to production.

---

## 🆕 New Features Announced

### 1. 📋 Policy Management (Preview)

**What it does:** Define natural language boundaries for AI agent actions, ensuring agents operate within specified constraints.

**Key capabilities:**
- Define policies in natural language (e.g., "Block all refunds above $1,000 unless reviewed by a human")
- Integrates with AgentCore Gateway for automatic enforcement
- Restrict access to certain APIs or tools
- Require human-in-the-loop for sensitive operations

**Use cases:**
- Financial transaction limits
- Data access controls
- Compliance enforcement
- Safety guardrails

---

### 2. 📊 AgentCore Evaluations

**What it does:** Monitor AI agent performance with 13 pre-built evaluators across multiple dimensions.

**Evaluation dimensions:**
| Dimension | Description |
|-----------|-------------|
| Correctness | Are responses accurate and factual? |
| Safety | Do responses follow safety guidelines? |
| Tool Usage Accuracy | Are tools being used correctly? |
| Relevance | Are responses relevant to the query? |
| Coherence | Is the reasoning logical and coherent? |
| Helpfulness | Are responses useful to the user? |
| Groundedness | Are responses grounded in provided context? |

**Key features:**
- Continuous monitoring in production
- Real-time alerts when performance deviates
- Pre-built evaluators ready to use
- Integration with observability systems

---

### 3. 🧠 AgentCore Memory

**What it does:** Enables agents to learn from past interactions with episodic memory capabilities.

**Memory types:**
- **Episodic Memory**: Remember specific past interactions
- **Semantic Memory**: Store learned facts and knowledge
- **Working Memory**: Maintain context within a session

**SDK Operations (already available):**
```python
# Control plane
client.create_memory(...)
client.list_memories(...)
client.update_memory(...)
client.delete_memory(...)

# Runtime
runtime.batch_create_memory_records(...)
runtime.retrieve_memory_records(...)
runtime.batch_update_memory_records(...)
runtime.batch_delete_memory_records(...)
runtime.list_memory_records(...)
```

**Benefits:**
- Personalized responses based on user history
- Context-aware decision making
- Learning from past successes and failures

---

### 4. 🔐 AgentCore Identity

**What it does:** Provides secure authentication for agents with existing identity providers.

**Supported providers:**
- Amazon Cognito
- Microsoft Entra ID (Azure AD)
- Okta
- Any OIDC-compatible provider

**SDK Operations:**
```python
client.create_workload_identity(...)
client.list_workload_identities(...)
client.update_workload_identity(...)
client.delete_workload_identity(...)
```

**Benefits:**
- Agents access only authorized tools and data
- Seamless integration with enterprise identity systems
- Audit trails for agent actions
- Agent-to-agent authentication

---

### 5. 🌐 AgentCore Gateway (We deployed this!)

**What it does:** Secure interface for agents to discover and utilize tools via MCP protocol.

**Key features:**
- Transform APIs into agent-compatible MCP tools
- Transform Lambda functions into tools
- OAuth and IAM authentication
- Semantic tool search
- Protocol translation (MCP ↔ AWS)

**Our deployment:**
| Gateway | Auth | Endpoint |
|---------|------|----------|
| IAM Gateway | AWS SigV4 | `knowledgebasegateway-z01bbyrzgr` |
| OAuth Gateway | OAuth 2.0 | `knowledgebasegatewayoauth2-pf7rmcexrm` |

---

### 6. 💻 AgentCore Code Interpreter

**What it does:** Execute code securely in sandbox environments.

**Capabilities:**
- Python code execution
- Data analysis and visualization
- Complex calculations
- File processing
- Isolated sandbox per session

**SDK Operations:**
```python
# Control plane
client.create_code_interpreter(...)
client.list_code_interpreters(...)
client.delete_code_interpreter(...)

# Runtime
runtime.start_code_interpreter_session(...)
runtime.invoke_code_interpreter(...)
runtime.list_code_interpreter_sessions(...)
runtime.stop_code_interpreter_session(...)
```

---

### 7. 🌍 AgentCore Browser Tool

**What it does:** Enable agents to interact with websites at scale.

**Capabilities:**
- Web navigation and browsing
- Form completion
- Data extraction
- Screenshot capture
- Multi-tab sessions

**SDK Operations:**
```python
# Control plane
client.create_browser(...)
client.list_browsers(...)
client.delete_browser(...)

# Runtime
runtime.start_browser_session(...)
runtime.list_browser_sessions(...)
runtime.update_browser_stream(...)
runtime.stop_browser_session(...)
```

---

### 8. 📈 AgentCore Observability

**What it does:** Real-time visibility into agent operations powered by Amazon CloudWatch.

**Features:**
- Built-in dashboards
- Key metrics telemetry
- OpenTelemetry integration
- Trace agent actions
- Integration with existing observability systems

**Key metrics:**
- Response latency
- Tool usage patterns
- Error rates
- Token consumption
- Session duration

---

### 9. 🤖 AgentCore Runtime

**What it does:** Managed runtime for deploying and executing AI agents.

**SDK Operations:**
```python
# Control plane
client.create_agent_runtime(...)
client.create_agent_runtime_endpoint(...)
client.list_agent_runtimes(...)
client.list_agent_runtime_versions(...)
client.list_agent_runtime_endpoints(...)
client.update_agent_runtime(...)
client.update_agent_runtime_endpoint(...)

# Runtime
runtime.invoke_agent_runtime(...)
runtime.list_sessions(...)
runtime.stop_runtime_session(...)
```

---

## 🔗 Framework Integrations

AgentCore now supports integration with popular agent frameworks:

| Framework | Description |
|-----------|-------------|
| **CrewAI** | Multi-agent orchestration |
| **LangGraph** | Graph-based agent workflows |
| **LlamaIndex** | Data framework for LLM apps |
| **OpenAI Agents SDK** | OpenAI's agent development kit |

---

## 🏗️ Architecture: AgentCore Components

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Amazon Bedrock AgentCore                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Gateway   │  │   Memory    │  │  Identity   │  │   Policy    │        │
│  │   (MCP)     │  │ (Episodic)  │  │   (Auth)    │  │ (Guardrails)│        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │    Code     │  │   Browser   │  │ Evaluations │  │Observability│        │
│  │ Interpreter │  │    Tool     │  │  (13 types) │  │ (CloudWatch)│        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      AgentCore Runtime                               │   │
│  │  • Managed agent execution    • Session management                  │   │
│  │  • Multi-framework support    • Scalable infrastructure             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📚 Available in Your Account

Based on the SDK analysis, the following features are **currently available**:

### ✅ Available Now
- AgentCore Gateway (deployed and tested)
- AgentCore Memory
- AgentCore Code Interpreter
- AgentCore Browser Tool
- AgentCore Identity (Workload Identity)
- Credential Providers (OAuth, API Key)
- AgentCore Runtime

### 🔜 Coming Soon / Preview
- Policy Management (Preview)
- AgentCore Evaluations (13 evaluators)

---

## 🚀 Next Steps for Your Project

### 1. Add Memory to Your Agents

```python
import boto3

# Create a memory store
control = boto3.client('bedrock-agentcore-control', region_name='us-west-2')
memory = control.create_memory(
    name='KnowledgeBaseMemory',
    description='Memory for knowledge base interactions'
)

# Store interaction memories
runtime = boto3.client('bedrock-agentcore', region_name='us-west-2')
runtime.batch_create_memory_records(
    memoryId=memory['memoryId'],
    records=[{
        'content': {'text': 'User asked about US seller fees'},
        'metadata': {'topic': 'fees', 'marketplace': 'US'}
    }]
)

# Retrieve relevant memories
results = runtime.retrieve_memory_records(
    memoryId=memory['memoryId'],
    query={'text': 'What did we discuss about fees?'}
)
```

### 2. Add Code Interpreter

```python
# Create code interpreter
interpreter = control.create_code_interpreter(
    name='DataAnalyzer',
    description='For analyzing knowledge base data'
)

# Start session and run code
session = runtime.start_code_interpreter_session(
    codeInterpreterId=interpreter['codeInterpreterId']
)

result = runtime.invoke_code_interpreter(
    codeInterpreterSessionId=session['sessionId'],
    code='import pandas as pd; print("Hello from sandbox!")'
)
```

### 3. Add Browser Capabilities

```python
# Create browser
browser = control.create_browser(
    name='WebResearcher',
    description='For web research tasks'
)

# Start browser session
session = runtime.start_browser_session(
    browserId=browser['browserId']
)
```

---

## 📖 References

- [AWS re:Invent 2025 AI Announcements](https://www.aboutamazon.com/news/aws/aws-re-invent-2025-ai-news-updates)
- [AWS AgentCore Documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/)
- [TechCrunch Coverage](https://techcrunch.com/2025/12/02/aws-announces-new-capabilities-for-its-ai-agent-builder/)
- [AWS re:Invent 2025 Keynote](https://www.youtube.com/watch?v=q3Sb9PemsSo)

---

**Created**: December 27, 2025  
**Based on**: AWS re:Invent 2025 announcements  
**SDK Version**: boto3 with bedrock-agentcore support

