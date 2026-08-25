# Multi-Agent Purchasing Concierge on Agent Runtime (ADK)

This project implements a secure, cross-project multi-agent purchasing concierge system deployed on **Vertex AI Agent Runtime (Reasoning Engines)** using the Google **Agent Development Kit (ADK)**, **Agent Identity**, and **Agent Gateway**.

It demonstrates **A2A (Agent-to-Agent) Multi-Runtime Orchestration** with **Dynamic Autodiscovery via Agent Registry**, allowing a root orchestrator agent in a dedicated concierge project to discover and delegate tasks to specialist agents hosted in separate spoke projects across isolated Reasoning Engine runtimes.

> [!NOTE]
> **Environment Reference Project Mapping (3-Project Setup)**:
> - **Central Governance Project (`PROJECT_GOVERNANCE`)**: `deepakmichaelprod` (Project Number: `114740196141`) — Hosts the Central Agent Gateway (`agw-egress`), Agent Registry, Identity-Aware Proxy (IAP), and Authorization Policies.
> - **Concierge Runtime Project (`PROJECT_CONCIERGE`)**: `deepakmichaelprod` (or dedicated runtime `agent-runtime1`) — Hosts the Purchasing Concierge Root Orchestrator Agent.
> - **Sellers Runtime Project (`PROJECT_SELLERS`)**: `deepakmichaelstage` (Project Number: `439077346891`, `agent-runtime2`) — Hosts the Burger Seller Agent and Pizza Seller Agent.
> - **Region**: `us-central1`

---

## Architecture & Multi-Runtime Flow

```mermaid
sequenceDiagram
    autonumber
    actor Client as User / Console Playground
    participant Concierge as Purchasing Concierge (Root Agent in PROJECT_CONCIERGE)
    participant Gateway as Agent Gateway (agw-egress in PROJECT_GOVERNANCE)
    participant Registry as Agent Registry (Central Governance in PROJECT_GOVERNANCE)
    participant Burger as Burger Seller Agent (Seller in PROJECT_SELLERS)
    participant Pizza as Pizza Seller Agent (Seller in PROJECT_SELLERS)

    Note over Concierge,Registry: Dynamic Autodiscovery via Agent Registry
    Concierge->>Registry: list_agents()
    Registry-->>Concierge: Returns Cross-Project mTLS Endpoint URIs & Reasoning Engine IDs

    Client->>Concierge: query("Order 1 burger and 1 pizza")
    activate Concierge

    par Route via Agent Gateway to Burger Agent (mTLS SPIFFE)
        Concierge->>Gateway: stream_query() via Agent Gateway
        Gateway->>Burger: Forward request with SPIFFE identity & IAP Egress Token
        Burger-->>Concierge: Returns Order ID (b9e08075-ad6f-439f-9648-ad1e5cc4c977)
    and Route via Agent Gateway to Pizza Agent (mTLS SPIFFE)
        Concierge->>Gateway: stream_query() via Agent Gateway
        Gateway->>Pizza: Forward request with SPIFFE identity & IAP Egress Token
        Pizza-->>Concierge: Returns Order ID (1c71a642-7e13-4461-8399-92b623eba9e5)
    end

    Concierge-->>Client: Returns aggregated order response with receipts
    deactivate Concierge
```

---

## Key Features & Best Practices

### 1. Decoupled Multi-Runtime & Package Isolation
Root orchestrators (`PROJECT_CONCIERGE`) and specialist seller agents (`PROJECT_SELLERS`) execute in separate Reasoning Engine containers on Vertex AI Agent Runtime. Each agent is packaged in an isolated subpackage directory (`burger_pkg` and `pizza_pkg`) to prevent Python `cloudpickle` namespace collisions across sibling runtimes.

### 2. Dynamic Autodiscovery via Agent Registry & Cross-Project URLs
The **Purchasing Concierge** dynamically discovers registered seller agents at runtime via the regional **Agent Registry** in `PROJECT_GOVERNANCE`.
- Service URLs in the Agent Registry point across project boundaries:
  `https://us-central1-aiplatform.mtls.googleapis.com/v1/projects/439077346891/locations/us-central1/reasoningEngines/<ENGINE_ID>`
- The concierge parses numeric project numbers (e.g., `439077346891`) back to their GCP project IDs (`deepakmichaelstage`) dynamically.

### 3. Secure Machine Identity (`AGENT_IDENTITY`) & Agent Gateway Egress
Both the **Seller Agents** and the **Purchasing Concierge** enforce zero-trust multi-agent communication by routing all inter-agent calls through the central **Agent Gateway** (`projects/deepakmichaelprod/locations/us-central1/agentGateways/agw-egress`) in `PROJECT_GOVERNANCE` using SPIFFE/mTLS managed machine identities.

---

## Cross-Project Egress Gateway IAM Configuration

Following the official Google Cloud documentation for [Configuring Cross-Project Egress Gateway Access](https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale/runtime/agent-gateway-runtime-deploy#deploy-an-agent):

### Step 1: Create Custom IAM Role in Gateway Project
```bash
gcloud iam roles create ar_agw_cross_project_sa \
  --project=$PROJECT_GOVERNANCE \
  --title="Runtime Agent Gateway Cross-Project SA" \
  --description="Custom role for the cross-project service agent to access Agent Gateway" \
  --permissions="networkservices.agentGateways.get,networkservices.operations.get"
```

### Step 2: Assign Custom Role to Spoke Runtime Service Agents
```bash
# 1. Derive Runtime Service Agent Emails
export CONCIERGE_AI_SA="service-${PROJECT_NUMBER_CONCIERGE}@gcp-sa-aiplatform.iam.gserviceaccount.com"
export SELLERS_AI_SA="service-${PROJECT_NUMBER_SELLERS}@gcp-sa-aiplatform.iam.gserviceaccount.com"

# 2. Grant Custom Role in Gateway Project
gcloud projects add-iam-policy-binding $PROJECT_GOVERNANCE \
  --member="serviceAccount:${CONCIERGE_AI_SA}" \
  --role="projects/${PROJECT_GOVERNANCE}/roles/ar_agw_cross_project_sa"

gcloud projects add-iam-policy-binding $PROJECT_GOVERNANCE \
  --member="serviceAccount:${SELLERS_AI_SA}" \
  --role="projects/${PROJECT_GOVERNANCE}/roles/ar_agw_cross_project_sa"
```

---

## Summary of IAM Permissions and Roles Used

| Role / Permission | Target Resource | Principal / Subject | Purpose |
| :--- | :--- | :--- | :--- |
| `ar_agw_cross_project_sa` (Custom Role) | `PROJECT_GOVERNANCE` (`networkservices.agentGateways.get`, `networkservices.operations.get`) | Spoke Project Service Agents (`service-${PROJECT_NUMBER}@gcp-sa-aiplatform.iam.gserviceaccount.com`) | Enables cross-project Agent Gateway lookup and operation status validation during agent runtime deployment. |
| `roles/networkservices.viewer` | `PROJECT_GOVERNANCE` | Spoke Project Service Agents | Predefined alternative containing gateway and operation viewer permissions. |
| `roles/iap.egressor` | Agent Registry Agent Resource (`--agent`) in `PROJECT_GOVERNANCE` | Concierge Engine Principal (`principal://agents.global.org-1015654926499...`) | Permits the Agent Gateway to egress traffic and pass authentication tokens securely across IAP boundaries to seller agent runtimes. |
| `roles/aiplatform.user` | Reasoning Engines in `PROJECT_SELLERS` | Concierge Engine Principal & Service Accounts | Grants invocation and user access permissions on spoke reasoning engine runtimes. |
| `roles/agentregistry.viewer` | `PROJECT_GOVERNANCE` | Concierge Service Accounts & PrincipalSet | Enables dynamic auto-discovery of registered agent endpoints from the Agent Registry. |

---

## Deployment Guide

### Prerequisites
1. GCP Projects (`PROJECT_GOVERNANCE`, `PROJECT_CONCIERGE`, `PROJECT_SELLERS`) with Vertex AI, Agent Registry, and Network Services APIs enabled.
2. `uv` installed for dependency management.
3. Central Agent Gateway created in `PROJECT_GOVERNANCE`.

### Export Configuration Variables
```bash
export PROJECT_GOVERNANCE="deepakmichaelprod"
export PROJECT_CONCIERGE="deepakmichaelprod"
export PROJECT_SELLERS="deepakmichaelstage"
export REGION="us-central1"
export GATEWAY_NAME="agw-egress"
```

### Step 1: Deploy Isolated Seller Agents to Spoke Project
Deploy Burger and Pizza seller agents to `$PROJECT_SELLERS`:
```bash
uv run python deploy_burger.py \
  --project=$PROJECT_SELLERS \
  --region=$REGION \
  --governance-project=$PROJECT_GOVERNANCE \
  --gateway=projects/$PROJECT_GOVERNANCE/locations/$REGION/agentGateways/$GATEWAY_NAME

uv run python deploy_pizza.py \
  --project=$PROJECT_SELLERS \
  --region=$REGION \
  --governance-project=$PROJECT_GOVERNANCE \
  --gateway=projects/$PROJECT_GOVERNANCE/locations/$REGION/agentGateways/$GATEWAY_NAME
```

### Step 2: Deploy Purchasing Concierge to Concierge Project
Deploy the root orchestrator to `$PROJECT_CONCIERGE`:
```bash
uv run python deploy_concierge_adk.py \
  --project=$PROJECT_CONCIERGE \
  --region=$REGION \
  --staging-bucket=gs://$PROJECT_GOVERNANCE-shared-staging \
  --gateway-name=$GATEWAY_NAME \
  --gateway-project=$PROJECT_GOVERNANCE
```

---

## Agent Registry Endpoint Updates & Cross-Project URLs

After deploying new reasoning engine instances, update the registered Agent Registry services in `$PROJECT_GOVERNANCE` to point to the new spoke reasoning engine endpoints in `$PROJECT_SELLERS`:

```bash
export SELLERS_PROJECT_NUMBER=$(gcloud projects describe $PROJECT_SELLERS --format="value(projectNumber)")
export BURGER_ENGINE_ID="2715395147641651200"
export PIZZA_ENGINE_ID="5638231305805103104"

# Update Burger Seller Agent Service
gcloud alpha agent-registry services update burger-seller-agent \
  --project=$PROJECT_GOVERNANCE \
  --location=$REGION \
  --interfaces="protocolBinding=JSONRPC,url=https://${REGION}-aiplatform.mtls.googleapis.com/v1/projects/${SELLERS_PROJECT_NUMBER}/locations/${REGION}/reasoningEngines/${BURGER_ENGINE_ID}"

# Update Pizza Seller Agent Service
gcloud alpha agent-registry services update pizza-seller-agent \
  --project=$PROJECT_GOVERNANCE \
  --location=$REGION \
  --interfaces="protocolBinding=JSONRPC,url=https://${REGION}-aiplatform.mtls.googleapis.com/v1/projects/${SELLERS_PROJECT_NUMBER}/locations/${REGION}/reasoningEngines/${PIZZA_ENGINE_ID}"
```

---

## Validation of Agent Runtime Route to Agent Gateway

To verify that deployed reasoning engine instances in `$PROJECT_SELLERS` are correctly configured to route inter-agent traffic through the central Agent Gateway in `$PROJECT_GOVERNANCE`, query their deployment specs via `curl`:

```bash
export TOKEN=$(gcloud auth application-default print-access-token)
export BURGER_ENGINE_ID="2715395147641651200"
export PIZZA_ENGINE_ID="5638231305805103104"

# Validate Burger Agent Gateway Route
curl -s -X GET "https://${REGION}-aiplatform.googleapis.com/v1beta1/projects/${PROJECT_SELLERS}/locations/${REGION}/reasoningEngines/${BURGER_ENGINE_ID}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  | jq '{displayName: .displayName, effectiveIdentity: .spec.effectiveIdentity, agentGatewayConfig: .spec.deploymentSpec.agentGatewayConfig}'

# Validate Pizza Agent Gateway Route
curl -s -X GET "https://${REGION}-aiplatform.googleapis.com/v1beta1/projects/${PROJECT_SELLERS}/locations/${REGION}/reasoningEngines/${PIZZA_ENGINE_ID}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  | jq '{displayName: .displayName, effectiveIdentity: .spec.effectiveIdentity, agentGatewayConfig: .spec.deploymentSpec.agentGatewayConfig}'
```

**Expected Output**:
```json
{
  "displayName": "burger-seller-agent-adk",
  "effectiveIdentity": "agents.global.org-1015654926499.system.id.goog/resources/aiplatform/projects/439077346891/locations/us-central1/reasoningEngines/2715395147641651200",
  "agentGatewayConfig": {
    "agentToAnywhereConfig": {
      "agentGateway": "projects/deepakmichaelprod/locations/us-central1/agentGateways/agw-egress"
    }
  }
}
```

---

## Testing via Google Cloud Console Playground

The deployed agents include the `PlaygroundCompatibleAdkAgent` wrapper, which exposes `register_operations` (`query`, `stream_query`) and parses dictionary payloads sent by the **Google Cloud Console Playground**.

### How to Test in Console UI:
1. Open the [Google Cloud Console](https://console.cloud.google.com/).
2. Navigate to **Vertex AI > Reasoning Engines** in project `$PROJECT_CONCIERGE`.
3. Click on **`purchasing-concierge-adk`**.
4. In the **Playground** chat window on the right side, type:
   > *"I confirm ordering 1 Classic Cheeseburger for IDR 85K from burger seller agent and 1 Pepperoni Pizza for IDR 140K from pizza seller agent. Please place both orders now."*
5. The agent will execute the cross-project A2A workflow via Agent Gateway and return full order confirmation receipts (`Order ID`).

### Testing via REST API (`curl`):
```bash
export CONCIERGE_ENGINE_ID="4485309801198256128"

curl -X POST \
  -H "Authorization: Bearer $(gcloud auth application-default print-access-token)" \
  -H "Content-Type: application/json" \
  https://${REGION}-aiplatform.googleapis.com/v1beta1/projects/${PROJECT_CONCIERGE}/locations/${REGION}/reasoningEngines/${CONCIERGE_ENGINE_ID}:query \
  -d '{
    "input": {
      "input": "I confirm ordering 1 Classic Cheeseburger for IDR 85K from burger seller agent and 1 Pepperoni Pizza for IDR 140K from pizza seller agent. Please place both orders now.",
      "user_id": "console-tester-user"
    }
  }'
```

---

## Cloud Logging Validation

You can audit inter-agent routing, SPIFFE identity verification, and execution logs across governance, concierge, and spoke seller projects using `gcloud logging read`.

### 1. Governance Project Logs (`$PROJECT_GOVERNANCE`)
Audit Agent Gateway routing and egress authorization decisions:
```bash
# Query Agent Gateway Routing & Egress Logs
gcloud logging read \
  'resource.type="networkservices.googleapis.com/AgentGateway" OR logName:"logs/networkservices.googleapis.com"' \
  --project=$PROJECT_GOVERNANCE \
  --limit=20 \
  --format="table(timestamp, jsonPayload.message, severity)"

# Query IAP Policy Audit Logs
gcloud logging read \
  'logName="projects/'$PROJECT_GOVERNANCE'/logs/cloudaudit.googleapis.com%2Fpolicy"' \
  --project=$PROJECT_GOVERNANCE \
  --limit=10 \
  --format="json"
```

### 2. Concierge Project Logs (`$PROJECT_CONCIERGE`)
Audit Purchasing Concierge Reasoning Engine execution logs:
```bash
gcloud logging read \
  'resource.type="aiplatform.googleapis.com/ReasoningEngine" AND resource.labels.reasoning_engine_id="4485309801198256128"' \
  --project=$PROJECT_CONCIERGE \
  --limit=20 \
  --format="table(timestamp, jsonPayload.message, severity)"
```

### 3. Spoke Seller Project Logs (`$PROJECT_SELLERS`)
Audit Burger and Pizza Reasoning Engine execution logs and incoming mTLS SPIFFE requests:
```bash
# Query Burger Seller Agent Execution Logs
gcloud logging read \
  'resource.type="aiplatform.googleapis.com/ReasoningEngine" AND resource.labels.reasoning_engine_id="2715395147641651200"' \
  --project=$PROJECT_SELLERS \
  --limit=20 \
  --format="table(timestamp, jsonPayload.message, severity)"

# Query Pizza Seller Agent Execution Logs
gcloud logging read \
  'resource.type="aiplatform.googleapis.com/ReasoningEngine" AND resource.labels.reasoning_engine_id="5638231305805103104"' \
  --project=$PROJECT_SELLERS \
  --limit=20 \
  --format="table(timestamp, jsonPayload.message, severity)"
```
