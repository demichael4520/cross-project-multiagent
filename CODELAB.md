# Governance for Cross-Project Agent-to-Agent (A2A) Communication with Agent Gateway and Agent Registry

> **Codelab Metadata**
> - **ID**: `governance-cross-project-a2a-agent-gateway`
> - **Summary**: Governance for Cross-Project Agent-to-Agent (A2A) Communication with Agent Gateway, Agent Registry, and Identity-Aware Proxy
> - **Categories**: Vertex AI, AI Agents, Governance
> - **Author**: Google Cloud
> - **Repository**: https://github.com/demichael4520/cross-project-multiagent

---

## 1. Introduction
**Duration**: 5 minutes

This Codelab explores enterprise cross-project **Agent-to-Agent (A2A)** governance and dynamic autodiscovery using **Gemini Enterprise Agent Platform** components: **Agent Gateway**, **Agent Registry**, and **Agent Identity**.

In a multi-tenant enterprise architecture across **three projects**, agents run in isolated runtime projects while requiring centralized governance, fine-grained access control, and dynamic service discovery.

> **Architecture Best Practice Note**:
> In production enterprise deployments, using a **Shared VPC** with Private Service Connect (PSC) network attachments is the recommended method for Agent Centralization to enforce private network boundary isolation. However, the primary goal of this codelab is to demonstrate **cross-project governance, Identity-Aware Proxy (IAP) access control policies, and dynamic Agent Registry auto-discovery**. To focus on governance without networking overhead, this codelab uses a streamlined 3-project setup.

```
+------------------------------------------------------------------------+
|                      PURCHASING RUNTIME PROJECT                        |
|                           (agent-runtime1)                             |
|  +------------------------------------------------------------------+  |
|  |       Purchasing Concierge Agent (AGENT_IDENTITY)                |  |
|  +-----------------------------------+------------------------------+  |
+--------------------------------------|---------------------------------+
                                       | (Egress via Gateway)
                                       v
+------------------------------------------------------------------------+
|                      CENTRAL GOVERNANCE PROJECT                        |
|                    (centralized-governance-project)                    |
|  +------------------------------------------------------------------+  |
|  |            Central Agent Gateway (centralized-agw)               |  |
|  +-----------------------------------+------------------------------+  |
|                                      |                                 |
|  +-----------------------------------v------------------------------+  |
|  |                       Central Agent Registry                     |  |
|  |  +------------------------------+  +--------------------------+  |  |
|  |  | Burger Agent (ALLOW Egress)  |  | Pizza Agent (DENY Egress)|  |  |
|  |  +------------------------------+  +--------------------------+  |  |
|  +------------------------------------------------------------------+  |
+--------------------------------------|---------------------------------+
                                       | (Target Reasoning Engines)
                                       v
+------------------------------------------------------------------------+
|                        SELLER RUNTIME PROJECT                          |
|                           (agent-runtime2)                             |
|  +---------------------------------+--------------------------------+  |
|  |       Burger Seller Agent       |       Pizza Seller Agent       |  |
|  +---------------------------------+--------------------------------+  |
+------------------------------------------------------------------------+
```

### What you build
In this codelab, you will:
- Deploy a **Centralized Agent Gateway** (`centralized-agw`) in `AGENT_TO_ANYWHERE` egress mode in `centralized-governance-project`.
- Deploy specialist **Burger Seller Agent** and **Pizza Seller Agent** in the `agent-runtime2` project.
- Deploy the **Purchasing Concierge Agent** in the `agent-runtime1` project.
- Manually register all three agents (`purchasing-concierge-adk`, `burger-seller-agent`, `pizza-seller-agent`) in the **Central Agent Registry** (`centralized-governance-project`).
- Enforce **Identity-Aware Proxy (IAP) Egress Policies** using `gcloud beta iap web`:
  - **ALLOW** policy: Grant the Purchasing Concierge permission to invoke the Burger Agent.
  - **BLOCK** policy: Deny/omit permission for the Purchasing Concierge to invoke the Pizza Agent.
- Perform end-to-end testing to verify that Burger calls succeed and Pizza calls are blocked by Agent Gateway with `HTTP 403 Forbidden`.

### What you learn
- How to configure cross-project service agent IAM permissions for centralized gateways.
- How to route Vertex AI Agent Runtime egress through a central Agent Gateway across multi-project environments.
- How to use SPIFFE-based **Agent Identity** (`types.IdentityType.AGENT_IDENTITY`) for fine-grained governance.
- How to manually register agents in Agent Registry (`gcloud agent-registry services create ... --agent-spec-type=no-spec`).
- How to configure IAP Egress policies on Agent Registry resources using `gcloud beta iap web add-iam-policy-binding` with `--agent` resource scope.

---

## 2. Setup and Requirements
**Duration**: 5 minutes

### Google Cloud Project Setup
To complete this codelab, you need **3 Google Cloud projects** with billing enabled. If you need to create new Google Cloud projects, follow the official documentation:
- [Creating and Managing Google Cloud Projects](https://cloud.google.com/resource-manager/docs/creating-managing-projects)
- [Enable Billing for a Project](https://cloud.google.com/billing/docs/how-to/modify-project)

Ensure your Google Cloud user account or service account has `roles/owner` or `roles/resourcemanager.organizationAdmin` + `roles/iam.securityAdmin` across all 3 projects.

### Get the Codelab Source Code
In Google Cloud Shell or your local terminal, clone the codelab repository and navigate to the project directory:

```bash
git clone https://github.com/demichael4520/cross-project-multiagent.git
cd cross-project-multiagent
```

### Project Mapping Reference
This codelab spans **3 standalone Google Cloud projects**. Refer to this table to know exactly which project to run each command against:

| Component / Task | Google Cloud Project Name | Environment Variable |
| :--- | :--- | :--- |
| **Agent Gateway & Agent Registry** | Central Governance Project | `$GOOGLE_CLOUD_PROJECT_GOVERNANCE` (`centralized-governance-project`) |
| **Purchasing Concierge Agent Runtime** | Concierge Runtime Project | `$GOOGLE_CLOUD_PROJECT_CONCIERGE` (`agent-runtime1`) |
| **Burger & Pizza Seller Agent Runtimes** | Sellers Runtime Project | `$GOOGLE_CLOUD_PROJECT_SELLERS` (`agent-runtime2`) |
| **IAP Authorization Audit Logs (Cloud Logging)** | Central Governance Project | `$GOOGLE_CLOUD_PROJECT_GOVERNANCE` (`centralized-governance-project`) |

### Required Google Cloud APIs & Agent Platform Overview
This codelab relies on several key Google Cloud APIs and **Agent Platform** infrastructure services. For more details on API management, see [Enabling and Disabling Google Cloud Services](https://cloud.google.com/service-usage/docs/enable-disable).

| API Name | Service Identifier | Description & Official Documentation |
| :--- | :--- | :--- |
| **Agent Registry API** | `agentregistry.googleapis.com` | Central catalog for multi-agent service discovery and IAP egress policy targets. See [Agent Gateway & Registry Runtime Deployment](https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale/runtime/agent-gateway-runtime-deploy). |
| **Network Services API** | `networkservices.googleapis.com` | Manages Centralized Agent Gateway resources (`agentGateways`) in `AGENT_TO_ANYWHERE` egress mode. See [Deploy Agent Gateway Documentation](https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale/runtime/agent-gateway-runtime-deploy#deploy-agent-gateway). |
| **Identity-Aware Proxy API** | `iap.googleapis.com` | Enforces Zero-Trust IAP egress authorization policies (`roles/iap.egressor`). See [Google Cloud Identity-Aware Proxy (IAP) Overview](https://cloud.google.com/iap/docs/concepts-overview). |
| **Vertex AI API** | `aiplatform.googleapis.com` | Hosts agent code as containerized runtimes in Vertex AI Reasoning Engine (Agent Engine). See [Vertex AI Agent Engine Overview](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/overview). |
| **Cloud Storage API** | `storage.googleapis.com` | Stores Reasoning Engine deployment artifacts (pickles, dependencies, and requirements). See [Google Cloud Storage Documentation](https://cloud.google.com/storage/docs). |

### Environment Variables
To make this codelab completely portable and reusable across environments, we define variable names for all project IDs, regions, and resources across the **three required projects**. **Do not hardcode project IDs or regions.**

Set the environment variables in your terminal:

```bash
# 1. Centralized Governance Project (Gateway & Registry)
export GOOGLE_CLOUD_PROJECT_GOVERNANCE="centralized-governance-project"

# 2. Concierge Runtime Project (Purchasing Concierge Agent)
export GOOGLE_CLOUD_PROJECT_CONCIERGE="agent-runtime1"

# 3. Sellers Runtime Project (Burger & Pizza Seller Agents)
export GOOGLE_CLOUD_PROJECT_SELLERS="agent-runtime2"

# 4. Regional & Gateway Settings
export REGION="us-central1"
export GATEWAY_NAME="centralized-agw"
```

### Get Project Numbers
Retrieve and store the project numbers required for IAM bindings:

```bash
export PROJECT_NUMBER_GOVERNANCE=$(gcloud projects describe $GOOGLE_CLOUD_PROJECT_GOVERNANCE --format="value(projectNumber)")
export PROJECT_NUMBER_CONCIERGE=$(gcloud projects describe $GOOGLE_CLOUD_PROJECT_CONCIERGE --format="value(projectNumber)")
export PROJECT_NUMBER_SELLERS=$(gcloud projects describe $GOOGLE_CLOUD_PROJECT_SELLERS --format="value(projectNumber)")

echo "Governance Project Number: $PROJECT_NUMBER_GOVERNANCE"
echo "Concierge Project Number:  $PROJECT_NUMBER_CONCIERGE"
echo "Sellers Project Number:    $PROJECT_NUMBER_SELLERS"
```

### Enable Required Google Cloud APIs
Enable the necessary APIs across your projects:

```bash
# Governance Project APIs
gcloud services enable \
  networkservices.googleapis.com \
  agentregistry.googleapis.com \
  iap.googleapis.com \
  aiplatform.googleapis.com \
  --project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE

# Concierge Project APIs
gcloud services enable \
  aiplatform.googleapis.com \
  storage.googleapis.com \
  --project=$GOOGLE_CLOUD_PROJECT_CONCIERGE

# Sellers Project APIs
gcloud services enable \
  aiplatform.googleapis.com \
  storage.googleapis.com \
  --project=$GOOGLE_CLOUD_PROJECT_SELLERS
```

### Register Core Google APIs Endpoint Service
Agent Gateway requires Google API URLs to be registered in the Agent Registry so that agents can egress traffic securely to core Google Cloud services (such as Vertex AI, IAM Credentials, and Telemetry):

```bash
gcloud agent-registry services create core-gapi-services \
  --project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE \
  --location=$REGION \
  --display-name="gapi.core.services" \
  --description="core apis and services" \
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

### Grant Egress Access for Core Google APIs Endpoint
Grant `roles/iap.egressor` to the Concierge project's Reasoning Engine SPIFFE identity on the `core-gapi-services` service so it can communicate with Vertex AI and Google APIs through the Agent Gateway:

```bash
export CONCIERGE_SPIFFE_WILDCARD="principal://iam.googleapis.com/projects/${PROJECT_NUMBER_CONCIERGE}/locations/${REGION}/reasoningEngines/*"

gcloud beta iap web add-iam-policy-binding \
  --resource-type=agent-registry \
  --service=core-gapi-services \
  --region=$REGION \
  --project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE \
  --role="roles/iap.egressor" \
  --member="$CONCIERGE_SPIFFE_WILDCARD"
```

---

## 3. Deploy Centralized Agent Gateway
**Duration**: 10 minutes

Deploy the centralized Agent Gateway (`centralized-agw`) in `AGENT_TO_ANYWHERE` egress mode inside the `$GOOGLE_CLOUD_PROJECT_GOVERNANCE` project.

### Step 1: Define Gateway Configuration Manifest
Create `agw-centralized.yaml` for egress traffic governance with custom IAP authorization enabled:

```yaml
name: projects/centralized-governance-project/locations/us-central1/agentGateways/centralized-agw
googleManaged:
  governedAccessPath: AGENT_TO_ANYWHERE
authorizationPolicy:
  iapConfig:
    enabled: true
```

### Step 2: Define Custom IAP Authorization Extension
Create `authz-extension.yaml` referencing `iap.googleapis.com` with `DRY_RUN` enforcement mode for testing and policy evaluation:

```yaml
name: projects/centralized-governance-project/locations/us-central1/authzExtensions/agw-iap-authz-extension
authority: iap.googleapis.com
service: iap.googleapis.com
timeout: 10s
failOpen: false
metadata:
  iapPolicyVersion: "V1"
  iamEnforcementMode: "DRY_RUN"
```

### Step 3: Define Request Authorization Policy
Create `authz-policy.yaml` attaching the Custom Authorization Extension to the Agent Gateway:

```yaml
name: projects/centralized-governance-project/locations/us-central1/authzPolicies/agw-request-authz-policy
targetLocations:
  - agentGateways/centralized-agw
policyProfile: REQUEST_AUTHZ
action: CUSTOM
customProvider:
  authzExtension: projects/centralized-governance-project/locations/us-central1/authzExtensions/agw-iap-authz-extension
```

### Step 4: Import Gateway Resources to Central Governance Project
Import the Agent Gateway, Authorization Extension, and Authorization Policy using `gcloud`:

```bash
# 1. Import Centralized Agent Gateway
gcloud alpha network-services agent-gateways import $GATEWAY_NAME \
  --source=agw-centralized.yaml \
  --location=$REGION \
  --project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE

# 2. Import Service Extension for Custom IAP AuthZ (DRY_RUN mode)
gcloud service-extensions authz-extensions import agw-iap-authz-extension \
  --source=authz-extension.yaml \
  --location=$REGION \
  --project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE

# 3. Import Network Security AuthZ Policy
gcloud network-security authz-policies import agw-request-authz-policy \
  --source=authz-policy.yaml \
  --location=$REGION \
  --project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE
```

Verify Gateway creation:

```bash
gcloud alpha network-services agent-gateways describe $GATEWAY_NAME \
  --location=$REGION \
  --project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE
```

### Step 5: Configure Cross-Project Service Agent IAM Permissions
For agents running in `$GOOGLE_CLOUD_PROJECT_CONCIERGE` and `$GOOGLE_CLOUD_PROJECT_SELLERS` to route egress traffic through `$GOOGLE_CLOUD_PROJECT_GOVERNANCE`, grant the runtime service accounts the `roles/networkservices.agentGatewayUser` role on the Centralized Gateway.

```bash
# 1. Get Vertex AI Service Agent for Concierge Project
export CONCIERGE_SA="service-${PROJECT_NUMBER_CONCIERGE}@gcp-sa-aiplatform.iam.gserviceaccount.com"

# 2. Get Vertex AI Service Agent for Sellers Project
export SELLERS_SA="service-${PROJECT_NUMBER_SELLERS}@gcp-sa-aiplatform.iam.gserviceaccount.com"

# 3. Grant Concierge SA access to Gateway in Governance Project
gcloud projects add-iam-policy-binding $GOOGLE_CLOUD_PROJECT_GOVERNANCE \
  --member="serviceAccount:${CONCIERGE_SA}" \
  --role="roles/networkservices.agentGatewayUser"

# 4. Grant Sellers SA access to Gateway in Governance Project
gcloud projects add-iam-policy-binding $GOOGLE_CLOUD_PROJECT_GOVERNANCE \
  --member="serviceAccount:${SELLERS_SA}" \
  --role="roles/networkservices.agentGatewayUser"
```

---

## 4. Deploy Seller Agents to agent-runtime2
**Duration**: 15 minutes

Deploy both the **Burger Seller Agent** and **Pizza Seller Agent** to Vertex AI Reasoning Engine in `$GOOGLE_CLOUD_PROJECT_SELLERS` (`agent-runtime2`). Both deployments will specify the centralized gateway (`centralized-agw` in `$GOOGLE_CLOUD_PROJECT_GOVERNANCE`) and attach `types.IdentityType.AGENT_IDENTITY`.

### Step 1: Grant Runtime Service Account Access to Gateway
Ensure the default compute service account in `$GOOGLE_CLOUD_PROJECT_SELLERS` has permission to use the Agent Gateway in `$GOOGLE_CLOUD_PROJECT_GOVERNANCE`:

```bash
export SELLERS_COMPUTE_SA="${PROJECT_NUMBER_SELLERS}-compute@developer.gserviceaccount.com"

gcloud projects add-iam-policy-binding $GOOGLE_CLOUD_PROJECT_GOVERNANCE \
  --member="serviceAccount:${SELLERS_COMPUTE_SA}" \
  --role="roles/networkservices.agentGatewayUser"
```

### Step 2: Deploy Burger Seller Agent
Deploy the Burger Agent to Vertex AI Reasoning Engine in `$GOOGLE_CLOUD_PROJECT_SELLERS`:

```bash
uv run python deploy_burger.py \
  --project=$GOOGLE_CLOUD_PROJECT_SELLERS \
  --region=$REGION \
  --governance-project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE \
  --gateway=$GATEWAY_NAME
```

Note down the returned Reasoning Engine resource ID (e.g., `projects/.../locations/us-central1/reasoningEngines/BURGER_ENGINE_ID`).

### Step 3: Deploy Pizza Seller Agent
Deploy the Pizza Agent to Vertex AI Reasoning Engine in `$GOOGLE_CLOUD_PROJECT_SELLERS`:

```bash
uv run python deploy_pizza.py \
  --project=$GOOGLE_CLOUD_PROJECT_SELLERS \
  --region=$REGION \
  --governance-project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE \
  --gateway=$GATEWAY_NAME
```

Note down the returned Reasoning Engine resource ID (e.g., `projects/.../locations/us-central1/reasoningEngines/PIZZA_ENGINE_ID`).

### Step 4: Validate Agent Gateway Routing Post-Deployment
After deploying the Seller agents, retrieve their Reasoning Engine details and verify that `agent_gateway` routing is attached:

```bash
export BURGER_ENGINE_ID="<BURGER_ENGINE_ID>"
export PIZZA_ENGINE_ID="<PIZZA_ENGINE_ID>"

# Inspect Burger Agent deployment
gcloud ai reasoning-engines describe $BURGER_ENGINE_ID \
  --project=$GOOGLE_CLOUD_PROJECT_SELLERS \
  --location=$REGION

# Inspect Pizza Agent deployment
gcloud ai reasoning-engines describe $PIZZA_ENGINE_ID \
  --project=$GOOGLE_CLOUD_PROJECT_SELLERS \
  --location=$REGION
```

Verify that the output contains the `agentGateway` configuration pointing to `projects/centralized-governance-project/locations/us-central1/agentGateways/centralized-agw`.

---

## 5. Deploy Purchasing Concierge Agent to agent-runtime1
**Duration**: 10 minutes

Deploy the **Purchasing Concierge Agent** to Vertex AI Reasoning Engine in `$GOOGLE_CLOUD_PROJECT_CONCIERGE` (`agent-runtime1`).

### Step 1: Deploy Concierge Agent
Deploy the Purchasing Concierge Agent specifying the central gateway and attaching `types.IdentityType.AGENT_IDENTITY`:

```bash
uv run python deploy_concierge.py \
  --project=$GOOGLE_CLOUD_PROJECT_CONCIERGE \
  --region=$REGION \
  --governance-project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE \
  --gateway=$GATEWAY_NAME
```

Note down the returned Reasoning Engine resource ID (e.g., `projects/.../locations/us-central1/reasoningEngines/CONCIERGE_ENGINE_ID`).

### Step 2: Validate Concierge Routing
Verify that the Concierge Agent deployment is attached to the central gateway:

```bash
export CONCIERGE_ENGINE_ID="<CONCIERGE_ENGINE_ID>"

gcloud ai reasoning-engines describe $CONCIERGE_ENGINE_ID \
  --project=$GOOGLE_CLOUD_PROJECT_CONCIERGE \
  --location=$REGION
```

---

## 6. Manually Register Agents in Central Agent Registry
**Duration**: 10 minutes

Register all three agents (`burger-seller-agent`, `pizza-seller-agent`, and `purchasing-concierge-adk`) in the **Central Agent Registry** in `$GOOGLE_CLOUD_PROJECT_GOVERNANCE`.

Using `--agent-spec-type=no-spec` creates a Service resource that Agent Registry automatically projects as a read-only **Agent** resource under `/agents/`.

### Step 1: Register Burger Seller Agent
Register the Burger Agent using its Vertex AI Reasoning Engine resource URL:

```bash
gcloud agent-registry services create burger-seller-agent \
  --project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE \
  --location=$REGION \
  --display-name="Burger Seller Agent" \
  --description="Specialist agent that sells burgers and fries" \
  --endpoint-spec-type=no-spec \
  --interfaces=protocolBinding=JSONRPC,url=https://${REGION}-aiplatform.googleapis.com/v1/projects/${PROJECT_NUMBER_SELLERS}/locations/${REGION}/reasoningEngines/${BURGER_ENGINE_ID}
```

Get the generated Agent Registry ID for the Burger Agent:

```bash
export BURGER_AGENT_ID=$(gcloud agent-registry services describe burger-seller-agent \
  --project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE \
  --location=$REGION \
  --format="value(name)" | awk -F'/' '{print $NF}')
echo "Burger Agent Registry ID: $BURGER_AGENT_ID"
```

### Step 2: Register Pizza Seller Agent
Register the Pizza Agent using its Vertex AI Reasoning Engine resource URL:

```bash
gcloud agent-registry services create pizza-seller-agent \
  --project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE \
  --location=$REGION \
  --display-name="Pizza Seller Agent" \
  --description="Specialist agent that sells pizzas and pasta" \
  --endpoint-spec-type=no-spec \
  --interfaces=protocolBinding=JSONRPC,url=https://${REGION}-aiplatform.googleapis.com/v1/projects/${PROJECT_NUMBER_SELLERS}/locations/${REGION}/reasoningEngines/${PIZZA_ENGINE_ID}
```

Get the generated Agent Registry ID for the Pizza Agent:

```bash
export PIZZA_AGENT_ID=$(gcloud agent-registry services describe pizza-seller-agent \
  --project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE \
  --location=$REGION \
  --format="value(name)" | awk -F'/' '{print $NF}')
echo "Pizza Agent Registry ID: $PIZZA_AGENT_ID"
```

### Step 3: Register Purchasing Concierge Agent
Register the Purchasing Concierge Agent in Agent Registry:

```bash
gcloud agent-registry services create purchasing-concierge-adk \
  --project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE \
  --location=$REGION \
  --display-name="Purchasing Concierge Agent" \
  --description="Orchestrator concierge agent that routes purchasing requests" \
  --endpoint-spec-type=no-spec \
  --interfaces=protocolBinding=JSONRPC,url=https://${REGION}-aiplatform.googleapis.com/v1/projects/${PROJECT_NUMBER_CONCIERGE}/locations/${REGION}/reasoningEngines/${CONCIERGE_ENGINE_ID}
```

Get the generated Agent Registry ID for the Concierge Agent:

```bash
export CONCIERGE_AGENT_ID=$(gcloud agent-registry services describe purchasing-concierge-adk \
  --project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE \
  --location=$REGION \
  --format="value(name)" | awk -F'/' '{print $NF}')
echo "Concierge Agent Registry ID: $CONCIERGE_AGENT_ID"
```

### Step 4: Validate Dynamic Agent Registry Auto-Discovery
The Purchasing Concierge dynamically discovers seller agents by querying the Agent Registry REST API at runtime. The Concierge code implements the following autodiscovery logic:

```python
def autodiscover_agent_services(self):
    """Queries Central Agent Registry via REST API to discover seller agents."""
    headers = {"Authorization": f"Bearer {self._get_auth_token()}"}
    registry_url = f"https://agentregistry.googleapis.com/v1/projects/{self.governance_project}/locations/{self.region}/services"
    
    response = requests.get(registry_url, headers=headers)
    if response.status_code != 200:
        return
        
    services = response.json().get("services", [])
    discovered_agents = {}
    
    for service in services:
        display_name = service.get("displayName", "")
        interfaces = service.get("interfaces", [])
        if not interfaces:
            continue
            
        target_url = interfaces[0].get("url", "")
        re_match = re.search(r"(projects/\d+/locations/[^/]+/reasoningEngines/\d+)", target_url)
        resource_path = re_match.group(1) if re_match else target_url

        combined_str = f"{display_name} {service.get('name', '')}".lower()
        if "burger" in combined_str:
            discovered_agents["burger_seller_agent"] = resource_path
        elif "pizza" in combined_str:
            discovered_agents["pizza_seller_agent"] = resource_path

# Update active agent map dynamically at runtime (no hardcoding)
self.agent_ids.update(discovered_agents)
```

---

## 7. Configure Access Control Policies (Allow Burger / Block Pizza)
**Duration**: 10 minutes

Agent Gateway uses **Identity-Aware Proxy (IAP)** to evaluate authorization decisions. Agent Gateway operates under a **Default Deny** security posture.

### Governance Requirement:
1. **ALLOW Policy**: The Purchasing Concierge Agent can call the Burger Agent.
2. **BLOCK Policy**: The Purchasing Concierge Agent is **DENIED** from calling the Pizza Agent.

### Step 1: Formulate Concierge Agent Identity
The SPIFFE principal identity for the Concierge Agent is:
`principal://iam.googleapis.com/projects/${PROJECT_NUMBER_CONCIERGE}/locations/${REGION}/reasoningEngines/${CONCIERGE_ENGINE_ID}`

```bash
export CONCIERGE_SPIFFE_PRINCIPAL="principal://iam.googleapis.com/projects/${PROJECT_NUMBER_CONCIERGE}/locations/${REGION}/reasoningEngines/${CONCIERGE_ENGINE_ID}"
echo "Concierge SPIFFE Principal: $CONCIERGE_SPIFFE_PRINCIPAL"
```

### Step 2: Grant Egress Access ONLY to Burger Agent
Grant `roles/iap.egressor` on the Burger Agent resource in Agent Registry. This allows the Purchasing Concierge's SPIFFE identity to communicate with the Burger Agent:

```bash
gcloud beta iap web add-iam-policy-binding \
  --resource-type=agent-registry \
  --agent=$BURGER_AGENT_ID \
  --region=$REGION \
  --project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE \
  --role="roles/iap.egressor" \
  --member="$CONCIERGE_SPIFFE_PRINCIPAL"
```

### Step 3: Keep Pizza Agent Unbound (Deny by Default)
Do **NOT** add any IAP policy binding for the Pizza Agent yet. Because Agent Gateway enforces **Deny by Default**, omitting the `roles/iap.egressor` binding for the Pizza Agent ensures that initial egress attempts from Concierge to Pizza Agent will be blocked.

If an IAM policy binding previously existed on the Pizza Agent, remove it explicitly:

```bash
gcloud beta iap web remove-iam-policy-binding \
  --resource-type=agent-registry \
  --agent=$PIZZA_AGENT_ID \
  --region=$REGION \
  --project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE \
  --role="roles/iap.egressor" \
  --member="$CONCIERGE_SPIFFE_PRINCIPAL" || true
```

### Step 4: Validate Initial Agent IAM Policies
Verify that only the Burger Agent has an IAP policy binding, while Pizza Agent has none:

```bash
gcloud beta iap web get-iam-policy \
  --resource-type=agent-registry \
  --agent=$BURGER_AGENT_ID \
  --region=$REGION \
  --project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE

gcloud beta iap web get-iam-policy \
  --resource-type=agent-registry \
  --agent=$PIZZA_AGENT_ID \
  --region=$REGION \
  --project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE
```

---

## 8. Test and Verify Governance Policies via Cloud Logging
**Duration**: 15 minutes

Now verify cross-project A2A communication, inspect Cloud Logging for policy decisions, update policies dynamically, and observe the policy state changes.

> **IMPORTANT - Use `curl` (terminal REST API) for Validation**:
> You **MUST** use the `curl` terminal commands below to validate communication between the Purchasing Concierge and seller agents. **Do NOT use the Vertex AI Agent Engine Playground UI** for validation, as the Playground UI executes queries under the user's browser session rather than invoking the Reasoning Engine REST `:query` endpoint directly with proper authorization tokens.

### Cross-Project Agent-to-Agent Authorization Sequence
The sequence diagram below illustrates how Agent Gateway and Identity-Aware Proxy enforce authorization decisions when the Concierge queries seller agents:

```
+-----------+            +---------------+            +-------------+
| Concierge |            | Agent Gateway |            | Seller Agent|
| (runtime1)|            |  (Governance) |            | (runtime2)  |
+-----+-----+            +-------+-------+            +------+------+
      |                          |                           |
      | 1. Query Burger Agent    |                           |
      |------------------------->|                           |
      |                          | 2. IAP Policy Approved    |
      |                          |    (roles/iap.egressor)   |
      |                          |                           |
      |                          | 3. Forward to Burger      |
      |                          |-------------------------->|
      |                          |                           |
      |                          | 4. Burger Response        |
      |                          |<--------------------------|
      | 5. Order Success (200)   |                           |
      |<-------------------------|                           |
      |                          |                           |
      | 6. Query Pizza Agent     |                           |
      |------------------------->|                           |
      |                          | 7. IAP Policy Denied      |
      |                          |    (Default Deny / 403)   |
      | 8. HTTP 403 Forbidden    |                           |
      |<-------------------------|                           |
```

### Step 1: Query Burger Agent (Expected: SUCCESS / 200 OK)
Obtain an authorization token and query the Purchasing Concierge Agent to order a burger:

```bash
export AUTH_TOKEN=$(gcloud auth print-access-token)

curl -X POST \
  "https://${REGION}-aiplatform.googleapis.com/v1/projects/${GOOGLE_CLOUD_PROJECT_CONCIERGE}/locations/${REGION}/reasoningEngines/${CONCIERGE_ENGINE_ID}:query" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "message": "I would like to order a double cheeseburger with extra fries."
    }
  }'
```

Expected Output:
```json
{
  "output": {
    "response": "Order placed successfully with Burger Seller Agent! Order ID: BURGER-88392. Total: $14.50"
  }
}
```

### Step 2: Query Cloud Logging for Granted Audit Logs in Central Governance Project
In Google Cloud, IAP egress policy evaluations emit audit logs to **Cloud Logging inside the Central Governance Project** (`$GOOGLE_CLOUD_PROJECT_GOVERNANCE`).

Query Cloud Logging in the **Central Governance Project** to view the granted authorization decision:

```bash
gcloud logging read \
  'logName="projects/'$GOOGLE_CLOUD_PROJECT_GOVERNANCE'/logs/cloudaudit.googleapis.com%2Fpolicy"' \
  --project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE \
  --limit=1 \
  --format="json"
```

Expected audit log entry showing `"granted": true` for the Burger Agent resource:

```json
{
  "protoPayload": {
    "@type": "type.googleapis.com/google.cloud.audit.AuditLog",
    "authenticationInfo": {
      "principalEmail": "principal://iam.googleapis.com/projects/111111111111/locations/us-central1/reasoningEngines/CONCIERGE_ENGINE_ID"
    },
    "authorizationInfo": [
      {
        "granted": true,
        "permission": "iap.webServiceVersions.egressViaIAP",
        "resource": "projects/centralized-governance-project/locations/us-central1/agents/agentregistry-00000000-0000-0000-4d81-517ed250cf35"
      }
    ],
    "methodName": "AuthorizeUser",
    "serviceName": "iap.googleapis.com"
  }
}
```

### Step 3: Query Pizza Agent (Expected: BLOCKED / 403 Forbidden)
Now query the Purchasing Concierge Agent to order a pizza:

```bash
curl -X POST \
  "https://${REGION}-aiplatform.googleapis.com/v1/projects/${GOOGLE_CLOUD_PROJECT_CONCIERGE}/locations/${REGION}/reasoningEngines/${CONCIERGE_ENGINE_ID}:query" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "message": "I would like to order a large Pepperoni Pizza."
    }
  }'
```

Expected Output (HTTP 403 / Access Denied):
```json
{
  "error": {
    "code": 403,
    "message": "Permission denied: Concierge SPIFFE identity is not authorized by Agent Gateway IAP egress policy to call target agent resource.",
    "status": "PERMISSION_DENIED"
  }
}
```

### Step 4: Query Cloud Logging for Denied Audit Logs in Central Governance Project
Query Cloud Logging in the **Central Governance Project** (`$GOOGLE_CLOUD_PROJECT_GOVERNANCE`) to verify the denied authorization decision:

```bash
gcloud logging read \
  'logName="projects/'$GOOGLE_CLOUD_PROJECT_GOVERNANCE'/logs/cloudaudit.googleapis.com%2Fpolicy"' \
  --project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE \
  --limit=1 \
  --format="json"
```

Expected audit log entry showing `"granted": false` for the Pizza Agent resource:

```json
{
  "protoPayload": {
    "@type": "type.googleapis.com/google.cloud.audit.AuditLog",
    "authenticationInfo": {
      "principalEmail": "principal://iam.googleapis.com/projects/111111111111/locations/us-central1/reasoningEngines/CONCIERGE_ENGINE_ID"
    },
    "authorizationInfo": [
      {
        "granted": false,
        "permission": "iap.webServiceVersions.egressViaIAP",
        "resource": "projects/centralized-governance-project/locations/us-central1/agents/agentregistry-00000000-0000-0000-8f92-628fd390ef11"
      }
    ],
    "methodName": "AuthorizeUser",
    "serviceName": "iap.googleapis.com"
  }
}
```

### Step 5: Dynamically Grant Egress Access to Pizza Agent
Dynamically update the security policy in `$GOOGLE_CLOUD_PROJECT_GOVERNANCE` to allow the Purchasing Concierge to call the Pizza Agent:

```bash
gcloud beta iap web add-iam-policy-binding \
  --resource-type=agent-registry \
  --agent=$PIZZA_AGENT_ID \
  --region=$REGION \
  --project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE \
  --role="roles/iap.egressor" \
  --member="$CONCIERGE_SPIFFE_PRINCIPAL"
```

### Step 6: Query Pizza Agent Again (Expected: SUCCESS / 200 OK)
Re-run the exact same pizza order request:

```bash
curl -X POST \
  "https://${REGION}-aiplatform.googleapis.com/v1/projects/${GOOGLE_CLOUD_PROJECT_CONCIERGE}/locations/${REGION}/reasoningEngines/${CONCIERGE_ENGINE_ID}:query" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "message": "I would like to order a large Pepperoni Pizza."
    }
  }'
```

Expected Output:
```json
{
  "output": {
    "response": "Order placed successfully with Pizza Seller Agent! Order ID: PIZZA-10492. Total: $18.99"
  }
}
```

### Step 7: Query Cloud Logging for Updated Granted Policy Audit Logs
Verify in Cloud Logging inside `$GOOGLE_CLOUD_PROJECT_GOVERNANCE` that the Pizza Agent request is now granted:

```bash
gcloud logging read \
  'logName="projects/'$GOOGLE_CLOUD_PROJECT_GOVERNANCE'/logs/cloudaudit.googleapis.com%2Fpolicy"' \
  --project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE \
  --limit=1 \
  --format="json"
```

Expected audit log entry showing `"granted": true` for the Pizza Agent resource:

```json
{
  "protoPayload": {
    "@type": "type.googleapis.com/google.cloud.audit.AuditLog",
    "authenticationInfo": {
      "principalEmail": "principal://iam.googleapis.com/projects/111111111111/locations/us-central1/reasoningEngines/CONCIERGE_ENGINE_ID"
    },
    "authorizationInfo": [
      {
        "granted": true,
        "permission": "iap.webServiceVersions.egressViaIAP",
        "resource": "projects/centralized-governance-project/locations/us-central1/agents/agentregistry-00000000-0000-0000-8f92-628fd390ef11"
      }
    ],
    "methodName": "AuthorizeUser",
    "serviceName": "iap.googleapis.com"
  }
}
```

---

## 9. Clean Up
**Duration**: 5 minutes

To prevent incurring ongoing charges to your Google Cloud account, delete the resources created during this Codelab.

### Step 1: Clean Up Reasoning Engine Deployments
Run the cleanup script to remove Reasoning Engines in runtime projects:

```bash
uv run python cleanup_old_deployments.py --project=$GOOGLE_CLOUD_PROJECT_CONCIERGE --region=$REGION
uv run python cleanup_old_deployments.py --project=$GOOGLE_CLOUD_PROJECT_SELLERS --region=$REGION
```

### Step 2: Delete Agent Registry Services
```bash
gcloud agent-registry services delete burger-seller-agent \
  --project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE \
  --location=$REGION --quiet

gcloud agent-registry services delete pizza-seller-agent \
  --project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE \
  --location=$REGION --quiet

gcloud agent-registry services delete purchasing-concierge-adk \
  --project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE \
  --location=$REGION --quiet
```

### Step 3: Delete Agent Gateway
```bash
gcloud alpha network-services agent-gateways delete $GATEWAY_NAME \
  --project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE \
  --location=$REGION --quiet
```

---

## 10. Congratulations!
**Duration**: 1 minute

You have successfully built, deployed, and governed a multi-project **Agent-to-Agent (A2A)** architecture on Google Cloud across three projects using **Agent Gateway**, **Agent Registry**, and **Agent Identity**.

### What you accomplished:
- Built a centralized **Agent Gateway** (`centralized-agw`) in `AGENT_TO_ANYWHERE` mode in `$GOOGLE_CLOUD_PROJECT_GOVERNANCE`.
- Deployed Concierge in `$GOOGLE_CLOUD_PROJECT_CONCIERGE` (`agent-runtime1`) and Seller Agents in `$GOOGLE_CLOUD_PROJECT_SELLERS` (`agent-runtime2`).
- Manually registered all three agents in **Central Agent Registry** (`gcloud agent-registry services create ... --agent-spec-type=no-spec`).
- Demonstrated dynamic **Agent Registry REST API Auto-Discovery** from the Purchasing Concierge.
- Enforced **IAP Egress Governance Policies** using `gcloud beta iap web add-iam-policy-binding` with `--agent` resource flags:
  - Validated initial **403 Forbidden** denial and inspected audit logs in Cloud Logging.
  - Applied access policy and verified **200 OK** approval and granted audit logs.
