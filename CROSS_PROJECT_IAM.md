# Cross-Project IAM & Security Architecture for Gemini Enterprise & Agent Gateway

This document provides a comprehensive reference and implementation guide for configuring cross-project **Identity and Access Management (IAM)**, **Agent Identity (SPIFFE)**, **`principalSet`** container groupings, and **Identity-Aware Proxy (IAP) Egress Policies** across Google Cloud projects.

---

## 1. Architectural Model

In an enterprise multi-agent deployment, responsibilities are split between a **Central Governance Project** and one or more **Spoke / Agent Runtime Projects**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ CENTRAL GOVERNANCE PROJECT (e.g., deepakmichaelprod - 114740196141)         │
│ • Central Agent Gateway (agw-egress)                                        │
│ • Central Agent Registry (core-gapi-services, seller services, mcp tools)   │
│ • Central IAP Egress Policies (roles/iap.egressor)                          │
│ • Shared GCS Staging Bucket (deepakmichaelprod-shared-staging)              │
│ • Model Armor & Security Guardrails                                         │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       ▲
                   Cross-Project Egress & Governance
                                       │
         ┌─────────────────────────────┴─────────────────────────────┐
         │                                                           │
┌────────┴──────────────────────────┐     ┌──────────────────────────┴────────┐
│ SPOKE 1: CONCIERGE / CONSUMER     │     │ SPOKE 2: SELLERS / WORKERS        │
│ (e.g., deepakmichaelprod)         │     │ (e.g., deepakmichaelstage)        │
│ • Purchasing Concierge Agent      │     │ • Burger Seller Agent             │
│ • Gemini Enterprise App (Assoc.)  │     │ • Pizza Seller Agent              │
│ • Agent Identity (SPIFFE URN)     │     │ • Private Tool Runtimes / Cloud Run│
└───────────────────────────────────┘     └───────────────────────────────────┘
```

---

## 2. Identity Constructs & Formats

| Identity Type | Format Pattern | Usage Scope |
| :--- | :--- | :--- |
| **Direct Agent Identity (SPIFFE)** | `principal://agents.global.org-<ORG_ID>.system.id.goog/resources/aiplatform/projects/<PROJECT_NO>/locations/<REGION>/reasoningEngines/<ENGINE_ID>` | Single, explicitly identified Reasoning Engine instance. |
| **Wildcard Agent Identity** | `principal://agents.global.org-<ORG_ID>.system.id.goog/resources/aiplatform/projects/<PROJECT_NO>/locations/<REGION>/reasoningEngines/*` | All Reasoning Engines in a specific project and region. |
| **Platform Container `principalSet`** | `principalSet://agents.global.org-<ORG_ID>.system.id.goog/attribute.platformContainer/aiplatform/projects/<PROJECT_NO>` | Project-level grouping for all Vertex AI Agent Platform containers in a spoke project. |
| **Gemini Enterprise (Discovery Engine)** | `principal://agents.global.org-<ORG_ID>.system.id.goog/resources/discoveryengine/projects/<PROJECT_NO>/locations/global/collections/default_collection/engines/<APP_ID>` | Gemini Enterprise Assistant App instance identity. |
| **Discovery Engine Service Agent** | `serviceAccount:service-<PROJECT_NO>@gcp-sa-discoveryengine.iam.gserviceaccount.com` | Discovery Engine backend crawler and MCP tool importer. |
| **AI Platform Service Agent** | `serviceAccount:service-<PROJECT_NO>@gcp-sa-aiplatform.iam.gserviceaccount.com` | Vertex AI Reasoning Engine provisioning agent. |

---

## 3. Core Google APIs Service Registration (`gapi.core.services`)

To permit agents to communicate with internal Google APIs (e.g., telemetry, IAM credentials, Agent Registry, Vertex AI) through the Agent Gateway, register `core-gapi-services` in the Central Governance Project:

```bash
export REGION="us-central1"
export GOOGLE_CLOUD_PROJECT_GOVERNANCE="deepakmichaelprod"

gcloud agent-registry services create core-gapi-services \
  --project=${GOOGLE_CLOUD_PROJECT_GOVERNANCE} \
  --location=${REGION} \
  --display-name="gapi.core.services" \
  --description="Core Google Cloud APIs and Service Endpoints" \
  --endpoint-spec-type=no-spec \
  --interfaces=protocolBinding=JSONRPC,url=https://telemetry.googleapis.com \
  --interfaces=protocolBinding=JSONRPC,url=https://telemetry.mtls.googleapis.com \
  --interfaces=protocolBinding=JSONRPC,url=https://${REGION}-aiplatform.googleapis.com \
  --interfaces=protocolBinding=JSONRPC,url=https://${REGION}-aiplatform.mtls.googleapis.com \
  --interfaces=protocolBinding=JSONRPC,url=https://cloudresourcemanager.googleapis.com \
  --interfaces=protocolBinding=JSONRPC,url=https://iamcredentials.googleapis.com \
  --interfaces=protocolBinding=JSONRPC,url=https://iamcredentials.mtls.googleapis.com \
  --interfaces=protocolBinding=JSONRPC,url=https://agentregistry.googleapis.com
```

---

## 4. Cross-Project IAM Configuration Commands

### Environment Variables
```bash
export ORG_ID="1015654926499"
export REGION="us-central1"

# Central Governance Project
export GOOGLE_CLOUD_PROJECT_GOVERNANCE="deepakmichaelprod"
export GOVERNANCE_PROJECT_NUMBER="114740196141"

# Spoke Projects
export GOOGLE_CLOUD_PROJECT_CONCIERGE="deepakmichaelprod"
export CONCIERGE_PROJECT_NUMBER="114740196141"

export GOOGLE_CLOUD_PROJECT_SELLERS="deepakmichaelstage"
export SELLERS_PROJECT_NUMBER="439077346891"
```

---

### Step 1: Grant Cross-Project Gateway Resolution Role (`ar_agw_cross_project_sa`)

The Vertex AI service agent in spoke projects requires permissions to resolve Agent Gateways located in the Central Governance Project:

```bash
# 1. Create custom role in Central Governance Project (if not exists)
gcloud iam roles create ar_agw_cross_project_sa \
  --project=${GOOGLE_CLOUD_PROJECT_GOVERNANCE} \
  --title="Agent Registry & Gateway Cross-Project Service Agent" \
  --description="Allows spoke Vertex AI service agents to resolve central Agent Gateway instances" \
  --permissions="networkservices.agentGateways.get,networkservices.agentGateways.use" \
  --stage="GA"

# 2. Grant custom role & network viewer to spoke project service agents
gcloud projects add-iam-policy-binding ${GOOGLE_CLOUD_PROJECT_GOVERNANCE} \
  --member="serviceAccount:service-${SELLERS_PROJECT_NUMBER}@gcp-sa-aiplatform.iam.gserviceaccount.com" \
  --role="projects/${GOOGLE_CLOUD_PROJECT_GOVERNANCE}/roles/ar_agw_cross_project_sa"

gcloud projects add-iam-policy-binding ${GOOGLE_CLOUD_PROJECT_GOVERNANCE} \
  --member="serviceAccount:service-${SELLERS_PROJECT_NUMBER}@gcp-sa-aiplatform.iam.gserviceaccount.com" \
  --role="roles/networkservices.viewer"
```

---

### Step 2: Shared GCS Staging Bucket Access

Grant spoke Vertex AI service agents read/write permissions to the central staging bucket:

```bash
gcloud storage buckets add-iam-policy-binding gs://${GOOGLE_CLOUD_PROJECT_GOVERNANCE}-shared-staging \
  --member="serviceAccount:service-${SELLERS_PROJECT_NUMBER}@gcp-sa-aiplatform.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"

gcloud storage buckets add-iam-policy-binding gs://${GOOGLE_CLOUD_PROJECT_GOVERNANCE}-shared-staging \
  --member="serviceAccount:service-${CONCIERGE_PROJECT_NUMBER}@gcp-sa-aiplatform.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

---

### Step 3: Central Agent Registry Discovery Access (`principalSet`)

Allow agents originating from both `deepakmichaelprod` and `deepakmichaelstage` to discover and list services in the Central Agent Registry:

```bash
# Grant Agent Registry Viewer to deepakmichaelprod agents
gcloud projects add-iam-policy-binding ${GOOGLE_CLOUD_PROJECT_GOVERNANCE} \
  --member="principalSet://agents.global.org-${ORG_ID}.system.id.goog/attribute.platformContainer/aiplatform/projects/${GOVERNANCE_PROJECT_NUMBER}" \
  --role="roles/agentregistry.viewer"

# Grant Agent Registry Viewer to deepakmichaelstage agents
gcloud projects add-iam-policy-binding ${GOOGLE_CLOUD_PROJECT_GOVERNANCE} \
  --member="principalSet://agents.global.org-${ORG_ID}.system.id.goog/attribute.platformContainer/aiplatform/projects/${SELLERS_PROJECT_NUMBER}" \
  --role="roles/agentregistry.viewer"

# Grant Agent Default Access
gcloud projects add-iam-policy-binding ${GOOGLE_CLOUD_PROJECT_GOVERNANCE} \
  --member="principalSet://agents.global.org-${ORG_ID}.system.id.goog/attribute.platformContainer/aiplatform/projects/${SELLERS_PROJECT_NUMBER}" \
  --role="roles/aiplatform.agentDefaultAccess"
```

---

### Step 4: IAP Egress Policy Binding on `core-gapi-services`

```bash
# 1. Retrieve the Endpoint ID of core-gapi-services
ENDPOINT_ID=$(gcloud alpha agent-registry services describe core-gapi-services \
  --project=${GOOGLE_CLOUD_PROJECT_GOVERNANCE} \
  --location=${REGION} \
  --format="value(registryResource)" | awk -F'/' '{print $NF}')

# 2. Grant IAP Egress to deepakmichaelprod agents
gcloud beta iap web add-iam-policy-binding \
  --resource-type=agent-registry \
  --endpoint=${ENDPOINT_ID} \
  --region=${REGION} \
  --project=${GOOGLE_CLOUD_PROJECT_GOVERNANCE} \
  --role="roles/iap.egressor" \
  --member="principalSet://agents.global.org-${ORG_ID}.system.id.goog/attribute.platformContainer/aiplatform/projects/${GOVERNANCE_PROJECT_NUMBER}" \
  --quiet

# 3. Grant IAP Egress to deepakmichaelstage agents
gcloud beta iap web add-iam-policy-binding \
  --resource-type=agent-registry \
  --endpoint=${ENDPOINT_ID} \
  --region=${REGION} \
  --project=${GOOGLE_CLOUD_PROJECT_GOVERNANCE} \
  --role="roles/iap.egressor" \
  --member="principalSet://agents.global.org-${ORG_ID}.system.id.goog/attribute.platformContainer/aiplatform/projects/${SELLERS_PROJECT_NUMBER}" \
  --quiet
```

---

### Step 5: Inter-Agent Authorization (`roles/iap.egressor` on Target Services)

When the Concierge agent (in `deepakmichaelprod`) queries the Burger Seller agent (deployed in `deepakmichaelstage`):

```bash
# Authorize the Concierge principal on the Burger Seller Service in Agent Registry
gcloud beta iap web add-iam-policy-binding \
  --project=${GOOGLE_CLOUD_PROJECT_GOVERNANCE} \
  --resource-type="agent-registry-service" \
  --service="burger-seller-service" \
  --member="principalSet://agents.global.org-${ORG_ID}.system.id.goog/attribute.platformContainer/aiplatform/projects/${CONCIERGE_PROJECT_NUMBER}" \
  --role="roles/iap.egressor"

# Grant the Concierge project permissions to invoke the target Reasoning Engine directly
gcloud projects add-iam-policy-binding ${GOOGLE_CLOUD_PROJECT_SELLERS} \
  --member="principalSet://agents.global.org-${ORG_ID}.system.id.goog/attribute.platformContainer/aiplatform/projects/${CONCIERGE_PROJECT_NUMBER}" \
  --role="roles/aiplatform.user"
```

---

### Step 6: Gemini Enterprise (Discovery Engine) IAM Configuration

To allow a Gemini Enterprise App to route queries through Agent Gateway to custom MCP or A2A services:

```bash
# 1. Grant Discovery Engine Service Agent invoker permissions on Cloud Run MCP backends
gcloud run services add-iam-policy-binding <mcp-service-name> \
  --member="serviceAccount:service-${GOVERNANCE_PROJECT_NUMBER}@gcp-sa-discoveryengine.iam.gserviceaccount.com" \
  --role="roles/run.invoker" \
  --region=${REGION} \
  --project=${GOOGLE_CLOUD_PROJECT_GOVERNANCE}

# 2. Grant IAP Egress on the Agent Registry target service for Gemini Enterprise
gcloud beta iap web add-iam-policy-binding \
  --project=${GOOGLE_CLOUD_PROJECT_GOVERNANCE} \
  --resource-type="agent-registry-service" \
  --service="burger-seller-agent" \
  --member="principal://agents.global.org-${ORG_ID}.system.id.goog/resources/discoveryengine/projects/${GOVERNANCE_PROJECT_NUMBER}/locations/global/collections/default_collection/engines/${APP_ID}" \
  --role="roles/iap.egressor"
```

---

## 5. Fine-Grained CEL Condition Policy Template

For strict tool-level filtering and MCP discovery handshakes:

```json
{
  "role": "roles/iap.egressor",
  "members": [
    "principalSet://agents.global.org-1015654926499.system.id.goog/attribute.platformContainer/aiplatform/projects/114740196141",
    "principalSet://agents.global.org-1015654926499.system.id.goog/attribute.platformContainer/aiplatform/projects/439077346891"
  ],
  "condition": {
    "title": "allow_tools_and_discovery",
    "description": "Permits MCP discovery handshake (tools/list) and specified operational tools",
    "expression": "api.getAttribute('iap.googleapis.com/mcp.toolName', '') == '' || api.getAttribute('iap.googleapis.com/mcp.toolName', '') in ['order_burger', 'get_menu', 'add', 'subtract']"
  }
}
```

---

## 6. Verification & Cloud Logging Queries

To inspect live authorization verdicts and audit policy decisions:

```bash
# Query Agent Gateway IAP authorization activity in Central Governance project
gcloud logging read 'resource.type="audited_resource" AND protoPayload.serviceName="agentgateway.googleapis.com"' \
  --project=${GOOGLE_CLOUD_PROJECT_GOVERNANCE} \
  --limit=20 \
  --format="table(timestamp, protoPayload.authenticationInfo.principalEmail, protoPayload.authorizationInfo[0].permission, protoPayload.authorizationInfo[0].granted)"

# Verify reasoning engine execution logs in Spoke project
gcloud logging read 'logName:"reasoning_engine"' \
  --project=${GOOGLE_CLOUD_PROJECT_SELLERS} \
  --limit=20 \
  --format="value(textPayload)"
```
