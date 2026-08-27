# Gemini Enterprise (GE) A2A Agent Deployment & Import Guide

This document is the definitive guide for building, deploying, and importing a **Native A2A (Agent-to-Agent) Protocol Agent** into **Gemini Enterprise (Discovery Engine)** using **Google Cloud Run** and **Agent Registry** in project `deepakmichaelprod`.

---

## Architectural Foundations: A2A, Agent Engine, and Gemini Enterprise

### 1. The Core Rule: Gemini Enterprise Only Supports A2A Agents
A fundamental rule governs **Gemini Enterprise (Discovery Engine Assistant)**:
> **Gemini Enterprise exclusively supports importing agents from Agent Registry that implement the open A2A (Agent-to-Agent) Protocol.** Non-A2A agents cannot be imported into Gemini Enterprise.

* **Why?** Gemini Enterprise is designed as a vendor-neutral orchestrator. It uses an internal **A2A Client** that communicates strictly via the **A2A JSON-RPC 2.0 specification** (`message/stream`, `tasks/send`, `tasks/get`).
* **Agent Registry Filtering**: When Gemini Enterprise queries Agent Registry for available agents, it searches specifically for services registered with `protocols.type == "A2A_AGENT"` containing a valid `A2A_AGENT_CARD`.
* **Non-A2A Incompatibility**: Resources registered in Agent Registry as `CUSTOM` (such as raw Vertex AI Reasoning Engine REST endpoints) lack the A2A JSON-RPC interface and are ignored or rejected by Gemini Enterprise.

---

### 2. Why A2A is Supported with Cloud Run and GKE
The A2A Protocol is an **application-layer HTTP protocol**:
* **Transport**: HTTP/1.1 or HTTP/2 with JSON-RPC 2.0 message semantics.
* **Streaming**: Server-Sent Events (SSE) for streaming token-by-token responses and real-time task status updates (`message/stream`).
* **Endpoint Control**: An A2A server must listen on a network port, inspect arbitrary JSON-RPC methods, maintain session state, and dispatch events.

**Why Cloud Run and GKE are the Ideal A2A Runtimes**:
1. **Full Protocol Control**: Cloud Run and GKE run arbitrary Docker containers. You can run any standard web server (`Starlette`, `FastAPI`, `uvicorn`, Go, or Node.js) running the `a2a-sdk` server stack (`A2AStarletteApplication`).
2. **Server-Sent Events (SSE) Support**: Both Cloud Run and GKE natively support long-lived HTTP streaming connections required for `message/stream`.
3. **Flexible Authentication**: In Cloud Run and GKE, authentication can be handled at the ingress level (IAM `roles/run.invoker`, Cloud Armor, or Agent Gateway) or within the application, decoupling client authentication from underlying Google Cloud APIs.

---

### 3. Why Vertex AI Agent Engine Uses ADK (and Why it is Not A2A)
**Vertex AI Agent Engine (Reasoning Engine)** is a **fully managed Google Cloud PaaS** for deploying ADK agents:
* **The Hosting Model**: When you run `adk deploy agent_engine` or use the Vertex AI Python SDK, Vertex AI packages your Python ADK agent (`LlmAgent`, `Runner`, tools) into an internal microservice container.
* **The API Frontend**: Vertex AI does **not** expose a raw web server or open HTTP ports. Instead, all traffic passes through Google's unified API frontend (`aiplatform.googleapis.com`).
* **The Protocol**: Vertex AI exposes a **Google Cloud Resource API** governed by Protobuf schemas:
  - `POST https://{region}-aiplatform.googleapis.com/v1/.../reasoningEngines/{id}:query`
  - `POST https://{region}-aiplatform.googleapis.com/v1/.../reasoningEngines/{id}:streamQuery`
  - Expected Request Schema:
    ```json
    {
      "input": {
        "message": "What is on the menu?"
      }
    }
    ```
* **The Protobuf Parser Barrier**: When Gemini Enterprise sends an A2A JSON-RPC payload (`{"jsonrpc": "2.0", "id": 1, "method": "message/stream", "params": {...}}`) directly to Vertex AI, Google's Protobuf API gateway cannot parse the fields and immediately aborts:
  ```text
  Invalid JSON payload received. Unknown name "jsonrpc": Cannot find field.
  Invalid JSON payload received. Unknown name "method": Cannot find field.
  Invalid JSON payload received. Unknown name "params": Cannot find field.
  ```

---

### 4. Comprehensive Architectural Comparison

| Dimension | Vertex AI Agent Engine (Reasoning Engine) | Cloud Run / GKE A2A Server |
| :--- | :--- | :--- |
| **Primary Purpose** | Managed code-level execution of ADK Python agents | Open, interoperable Agent-to-Agent web service |
| **Interface Protocol** | **Google Cloud REST / Protobuf** (`aiplatform.googleapis.com`) | **Open A2A JSON-RPC 2.0 over HTTP** (`a2a-sdk`) |
| **Streaming Mechanism** | Google Cloud Protobuf chunk streaming (`:streamQuery`) | Server-Sent Events (SSE) (`message/stream`) |
| **Expected Request** | `{"input": {"message": "..."}}` | `{"jsonrpc": "2.0", "method": "...", "params": {...}}` |
| **Agent Registry Registration** | `type: "CUSTOM"`, `protocolBinding: "HTTP_JSON"` | `type: "A2A_AGENT"`, `card: "A2A_AGENT_CARD"` |
| **Gemini Enterprise Import** | ❌ **Not Supported** (GE requires A2A JSON-RPC) | ✅ **Natively Supported** (Standard A2A flow) |
| **Calling Mechanisms** | Vertex AI Python SDK, gcloud, internal agent-to-agent ADK calls | Gemini Enterprise, external A2A clients, curl |
| **Authentication** | Google Cloud IAM (`roles/aiplatform.user` on caller) | IAM `roles/run.invoker`, Agent Gateway IAP, or Public |

---

### 5. How the Architecture Fits Together

```
┌─────────────────────────────────────────────────────────────┐
│ Gemini Enterprise (Assistant)                               │
│ • Requires: A2A Protocol                                    │
│ • Dispatches: JSON-RPC 2.0 (method: "message/stream")       │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼ [Discovers via Agent Registry (type: A2A_AGENT)]
┌─────────────────────────────────────────────────────────────┐
│ Central Agent Gateway / IAP (deepakmichaelprod)             │
│ • Enforces: Security policies & IAP egressor authorization  │
│ • Routes: To Cloud Run backend                              │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼ [HTTP / JSON-RPC 2.0]
┌─────────────────────────────────────────────────────────────┐
│ Cloud Run A2A Service (burger-seller-a2a)                   │
│ • Runs: A2AStarletteApplication (a2a-sdk)                   │
│ • Translates: A2A JSON-RPC ➔ ADK Runner                     │
│ • Service Account: 114740196141-compute@developer...        │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼ [Native Google Cloud ADC via Service Account]
┌─────────────────────────────────────────────────────────────┐
│ Vertex AI Gemini 2.5 Flash API                              │
│ • Executes: LlmAgent inference & tool execution             │
└─────────────────────────────────────────────────────────────┘
```


---

## #1. Cloud Run Deployment Details

The Cloud Run service uses `google-adk` for agent logic and `a2a-sdk` to serve the A2A JSON-RPC protocol over HTTP with Server-Sent Events (SSE).

### 1.1 Project Structure (`burger_a2a_service/`)
```
burger_a2a_service/
├── Dockerfile
├── requirements.txt
├── agent.py              # ADK Agent definition & tools
├── agent_executor.py     # ADK-to-A2A execution adapter
└── __main__.py           # Starlette A2A application entrypoint
```

### 1.2 `requirements.txt`
```text
a2a-sdk==0.3.0
google-adk>=1.7.0
google-genai>=1.0.0
pydantic>=2.0.0
starlette>=0.40.0
uvicorn>=0.30.0
click>=8.0.0
python-dotenv>=1.0.0
```

### 1.3 `Dockerfile`
```dockerfile
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "__main__.py", "--host", "0.0.0.0", "--port", "8080"]
```

### 1.4 `agent.py` (ADK Agent Logic)
```python
from google.adk.agents import LlmAgent
from pydantic import BaseModel
import uuid

class OrderItem(BaseModel):
    name: str
    quantity: int
    price: int

class Order(BaseModel):
    order_id: str
    status: str
    order_items: list[OrderItem]

def create_burger_order(order_items: list[OrderItem]) -> str:
    """Creates a new burger order with the given order items."""
    try:
        order_id = str(uuid.uuid4())
        order = Order(order_id=order_id, status="created", order_items=order_items)
        return f"Order {order.model_dump()} has been created successfully. Order ID: {order_id}"
    except Exception as e:
        return f"Error creating order: {e}"

def get_burger_menu() -> str:
    """Retrieves the full menu of available burgers and their prices in IDR."""
    return """Available Burger Menu:
- Classic Cheeseburger: IDR 85,000
- Double Cheeseburger: IDR 110,000
- Spicy Chicken Burger: IDR 80,000
- Spicy Cajun Burger: IDR 85,000"""

burger_agent = LlmAgent(
    name="burger_seller_agent",
    model="gemini-2.5-flash",
    instruction="""You are a specialized assistant for a burger store.
Your sole purpose is to answer questions about the burger menu, prices, and order creation.
If the user asks about anything other than the burger menu or ordering, politely decline.

Available burger menu:
- Classic Cheeseburger: IDR 85K
- Double Cheeseburger: IDR 110K
- Spicy Chicken Burger: IDR 80K
- Spicy Cajun Burger: IDR 85K

Rules:
1. Always verify the requested burger item is in the menu.
2. When the user confirms an order, invoke create_burger_order.""",
    tools=[get_burger_menu, create_burger_order]
)
```

### 1.5 `agent_executor.py` (A2A Protocol Adapter)
```python
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import Part, TaskState, TextPart
from a2a.utils import new_agent_text_message, new_task
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

class ADKAgentExecutor(AgentExecutor):
    def __init__(self, agent, status_message='Processing burger order...', artifact_name='response'):
        self.agent = agent
        self.status_message = status_message
        self.artifact_name = artifact_name
        self.runner = Runner(
            app_name=agent.name,
            agent=agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError('Cancellation is not implemented.')

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        if not context.message:
            raise ValueError('Message should be present in request context')

        query = context.get_user_input()
        task = context.current_task or new_task(context.message)
        await event_queue.enqueue_event(task)

        updater = TaskUpdater(event_queue, task.id, task.context_id)
        user_id = 'gemini_enterprise_user'

        try:
            await updater.update_status(
                TaskState.working,
                new_agent_text_message(self.status_message, task.context_id, task.id),
            )

            session = await self.runner.session_service.get_session(
                app_name=self.agent.name,
                user_id=user_id,
                session_id=task.context_id,
            )
            if not session:
                session = await self.runner.session_service.create_session(
                    app_name=self.agent.name,
                    user_id=user_id,
                    state={},
                    session_id=task.context_id,
                )

            content = types.Content(role='user', parts=[types.Part.from_text(text=query)])
            response_text = ''
            async for event in self.runner.run_async(user_id=user_id, session_id=session.id, new_message=content):
                if event.is_final_response() and event.content and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            response_text += part.text + '\n'

            if not response_text:
                response_text = "Task completed."

            await updater.add_artifact([Part(root=TextPart(text=response_text))], name=self.artifact_name)
            await updater.complete()

        except Exception as e:
            await updater.update_status(
                TaskState.failed,
                new_agent_text_message(f'Error: {e!s}', task.context_id, task.id),
                final=True,
            )
```

### 1.6 `__main__.py` (Starlette Server Entrypoint)
```python
import asyncio, functools, logging, os, click, uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from agent import burger_agent
from agent_executor import ADKAgentExecutor
from starlette.applications import Starlette

os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

def make_sync(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))
    return wrapper

@click.command()
@click.option('--host', default='0.0.0.0')
@click.option('--port', default=8080, type=int)
@make_sync
async def main(host, port):
    app_url = os.environ.get('APP_URL', f'http://{host}:{port}')

    agent_card = AgentCard(
        name="Burger Seller Agent",
        description="Specialized seller agent for browsing burger menus, checking pricing, and placing orders.",
        version='1.0.0',
        url=app_url,
        default_input_modes=['text', 'text/plain'],
        default_output_modes=['text', 'text/plain'],
        capabilities=AgentCapabilities(streaming=True),
        skills=[
            AgentSkill(
                id='get_burger_menu',
                name='get_burger_menu',
                description='Retrieves the full menu of available burgers and their prices in IDR.',
                tags=['menu', 'food', 'pricing'],
                examples=['What burgers are available?', 'Can I see the burger menu and prices?'],
            ),
            AgentSkill(
                id='create_burger_order',
                name='create_burger_order',
                description='Places an order for one or more burger menu items and returns an order confirmation ID.',
                tags=['order', 'food', 'burger', 'checkout'],
                examples=['Order 1 Classic Cheeseburger', 'I would like to order 2 Double Cheeseburgers'],
            ),
        ],
    )

    request_handler = DefaultRequestHandler(
        agent_executor=ADKAgentExecutor(agent=burger_agent),
        task_store=InMemoryTaskStore(),
    )

    a2a_app = A2AStarletteApplication(agent_card=agent_card, http_handler=request_handler)
    app = Starlette(routes=a2a_app.routes(), middleware=[])

    config = uvicorn.Config(app, host=host, port=port, log_level='info')
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == '__main__':
    main()
```

---

## #2. The Canonical A2A Agent Card

Save this configuration as `burger_agent_card.json`. Replace `https://burger-seller-a2a-114740196141.us-central1.run.app` with your Cloud Run URL.

```json
{
  "name": "Burger Seller Agent",
  "description": "Specialized seller agent for browsing burger menus, checking pricing, and placing orders.",
  "version": "1.0.0",
  "protocolVersion": "0.3.0",
  "preferredTransport": "JSONRPC",
  "url": "https://burger-seller-a2a-114740196141.us-central1.run.app",
  "provider": {
    "organization": "Burger Store",
    "url": "https://burger.example.com"
  },
  "documentationUrl": "https://burger.example.com/docs",
  "capabilities": {
    "streaming": true,
    "pushNotifications": false
  },
  "defaultInputModes": [
    "text/plain"
  ],
  "defaultOutputModes": [
    "text/plain"
  ],
  "skills": [
    {
      "id": "get_burger_menu",
      "name": "get_burger_menu",
      "description": "Retrieves the full menu of available burgers and their prices in IDR.",
      "tags": [
        "menu",
        "food",
        "pricing"
      ],
      "examples": [
        "What burgers are available?",
        "Can I see the burger menu and prices?"
      ],
      "inputModes": [
        "text/plain"
      ],
      "outputModes": [
        "text/plain"
      ]
    },
    {
      "id": "create_burger_order",
      "name": "create_burger_order",
      "description": "Places an order for one or more burger menu items and returns an order confirmation ID.",
      "tags": [
        "order",
        "food",
        "burger",
        "checkout"
      ],
      "examples": [
        "Order 1 Classic Cheeseburger",
        "I would like to order 2 Double Cheeseburgers"
      ],
      "inputModes": [
        "text/plain"
      ],
      "outputModes": [
        "text/plain"
      ]
    }
  ]
}
```

> [!NOTE]
> When deployed with `--allow-unauthenticated` on Cloud Run, the `securitySchemes` block is completely omitted. Gemini Enterprise will import and execute the agent with **zero OAuth prompts, zero consent screens, and no corporate account blocks**.

---

## #3. Agent Registry Deployment

Update the service entry in `PROJECT_GOVERNANCE` (`deepakmichaelprod`):

```bash
CARD_CONTENT=$(cat burger_agent_card.json)

gcloud alpha agent-registry services update burger-seller-agent \
  --project=deepakmichaelprod \
  --location=us-central1 \
  --agent-spec-type=a2a-agent-card \
  --agent-spec-content="${CARD_CONTENT}" \
  --clear-interfaces
```

---

## #4. IAM & Security Configuration

### Layer 1: Cloud Run Service Account (Runtime Permissions)
The service account running Cloud Run (`114740196141-compute@developer.gserviceaccount.com`) needs access to invoke Vertex AI Gemini models:

```bash
gcloud projects add-iam-policy-binding deepakmichaelprod \
  --member="serviceAccount:114740196141-compute@developer.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

### Layer 2: Gemini Enterprise Discovery Engine Service Agent
```bash
# Allow Gemini Enterprise to discover registered agents
gcloud projects add-iam-policy-binding deepakmichaelprod \
  --member="serviceAccount:service-114740196141@gcp-sa-discoveryengine.iam.gserviceaccount.com" \
  --role="roles/agentregistry.viewer"

# Allow Gemini Enterprise to view Central Agent Gateway routes
gcloud projects add-iam-policy-binding deepakmichaelprod \
  --member="serviceAccount:service-114740196141@gcp-sa-discoveryengine.iam.gserviceaccount.com" \
  --role="roles/networkservices.viewer"
```

### Layer 3: IAP Egressor Role (Agent Gateway)
```bash
gcloud beta iap web add-iam-policy-binding \
  --project=deepakmichaelprod \
  --region=us-central1 \
  --resource-type=agent-registry \
  --role="roles/iap.egressor" \
  --member="principal://agents.global.org-1015654926499.system.id.goog/resources/discoveryengine/projects/114740196141/locations/global/engines/deepak-ge-app_1787348960235/assistants/default_assistant/agents/registry/*"
```

---

## #5. Deploy in `deepakmichaelprod` Project

### Build and Deploy Command:
```bash
gcloud run deploy burger-seller-a2a \
  --source=burger_a2a_service \
  --region=us-central1 \
  --project=deepakmichaelprod \
  --allow-unauthenticated \
  --service-account=114740196141-compute@developer.gserviceaccount.com
```

### Verification with `curl`:
Once deployed, retrieve the service URL and test the A2A `message/stream` JSON-RPC endpoint directly:

```bash
SERVICE_URL=$(gcloud run services describe burger-seller-a2a --project=deepakmichaelprod --region=us-central1 --format='value(status.url)')

# Send A2A JSON-RPC 2.0 Request
curl -X POST "${SERVICE_URL}" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "message/stream",
    "params": {
      "message": {
        "parts": [
          {
            "text": "What burgers do you have on the menu and what are the prices?"
          }
        ]
      }
    }
  }'
```

---

## #6. Verification & Observability in Central Agent Gateway

When Gemini Enterprise invokes the imported A2A agent, traffic is routed through the Central Agent Gateway (`agw-egress`). The gateway performs IAP authentication, enforces security policies, logs the JSON-RPC method, and streams the response.

### 6.1 Gcloud Logging Commands for Agent Gateway

#### Command 1: Formatted Table View (Quick Status Check)
```bash
gcloud logging read \
  'logName="projects/deepakmichaelprod/logs/networkservices.googleapis.com%2Fgateway_requests" AND (httpRequest.requestUrl=~"run.app" OR jsonPayload.enforcedGatewaySecurityPolicy.hostname=~"run.app")' \
  --project=deepakmichaelprod \
  --limit=5 \
  --format="table(timestamp.date('%H:%M:%S'):label=TIME, httpRequest.status:label=STATUS, jsonPayload.agentGatewayInfo.mcpInfo.method:label=METHOD, jsonPayload.authzPolicyInfo.result:label=IAP_AUTHZ, httpRequest.latency:label=LATENCY)"
```

#### Command 2: Detailed JSON View (Full Policy Evaluation & Tracing)
```bash
gcloud logging read \
  'logName="projects/deepakmichaelprod/logs/networkservices.googleapis.com%2Fgateway_requests" AND (httpRequest.requestUrl=~"run.app" OR jsonPayload.enforcedGatewaySecurityPolicy.hostname=~"run.app")' \
  --project=deepakmichaelprod \
  --limit=1 \
  --format="json"
```

#### Command 3: Cloud Run Execution Logs (Model Inference & ADK Runner)
```bash
gcloud logging read \
  'resource.type="cloud_run_revision" AND resource.labels.service_name="burger-seller-a2a"' \
  --project=deepakmichaelprod \
  --limit=10 \
  --format="table(timestamp.date('%H:%M:%S'):label=TIME, severity, textPayload)"
```

---

### 6.2 Verified Real Production Gateway Log Entry

```json
{
  "resource": {
    "type": "networkservices.googleapis.com/Gateway",
    "labels": {
      "gateway_name": "agw-egress",
      "gateway_type": "SECURE_WEB_GATEWAY",
      "location": "us-central1",
      "network_name": "projects/y9a058415cac84448p-tp/global/networks/uk1-25feb-2-vpc4",
      "resource_container": "114740196141"
    }
  },
  "httpRequest": {
    "latency": "1.147154s",
    "protocol": "HTTP/1.1",
    "requestMethod": "POST",
    "requestUrl": "https://burger-seller-a2a-114740196141.us-central1.run.app/",
    "responseSize": "2006",
    "serverIp": "34.143.75.2:443",
    "status": 200,
    "userAgent": "python-httpx/0.26.0"
  },
  "jsonPayload": {
    "@type": "type.googleapis.com/google.cloud.loadbalancing.type.LoadBalancerLogEntry",
    "agentGatewayInfo": {
      "agentRegistryResource": "projects/114740196141/locations/us-central1/agents/agentregistry-00000000-0000-0000-4c41-4c6ec39e5f39",
      "mcpInfo": {
        "method": "message/stream"
      }
    },
    "authzPolicyInfo": {
      "policies": [
        {
          "name": "projects/978983713504/locations/us-central1/authzPolicies/agw-egress-iap-authzpolicy",
          "result": "ALLOWED"
        }
      ],
      "result": "ALLOWED"
    },
    "enforcedGatewaySecurityPolicy": {
      "hostname": "burger-seller-a2a-114740196141.us-central1.run.app",
      "matchedRules": [
        {
          "action": "ALLOWED",
          "name": "default_denied"
        }
      ]
    }
  },
  "logName": "projects/deepakmichaelprod/logs/networkservices.googleapis.com%2Fgateway_requests",
  "severity": "INFO",
  "status": 200
}
```

### Key Verification Highlights:
1. **`httpRequest.status: 200`** — Confirms successful execution without network or application failures.
2. **`agentGatewayInfo.mcpInfo.method: "message/stream"`** — Confirms Gemini Enterprise is using open A2A JSON-RPC streaming.
3. **`authzPolicyInfo.result: "ALLOWED"`** — Confirms Identity-Aware Proxy (IAP) successfully authorized the Discovery Engine assistant's SPIFFE identity (`principal://agents.global.org-1015654926499...`).
4. **`agentGatewayInfo.agentRegistryResource`** — Confirms routing was dynamically resolved via Google Cloud Agent Registry.

