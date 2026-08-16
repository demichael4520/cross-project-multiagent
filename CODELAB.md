# Governance for Cross-Project Agent-to-Agent (A2A) Communication with Agent Gateway, Agent Registry, and Shared VPC

## 1. Introduction
duration: 5

This Codelab explores enterprise cross-project **Agent-to-Agent (A2A)** governance and dynamic autodiscovery using **Gemini Enterprise Agent Platform** components: **Agent Gateway**, **Agent Registry**, **Agent Identity**, and **Shared VPC Private Service Connect (PSC)**.

In a multi-tenant enterprise architecture, agents run across isolated runtime projects while requiring centralized governance, fine-grained access control, and dynamic service discovery.

```
                  +-------------------------------------------------------------------+
                  |                   SHARED VPC HOST PROJECT                         |
                  |                (dev-host-project-505021)                          |
                  |  +-------------------------------------------------------------+  |
                  |  |  Shared VPC (spvpc-network) / Subnet / PSC Network Attachment |  |
                  |  +-------------------------------------------------------------+  |
                  +-------------------------------------------------------------------+
                                                    ^
                                                    | (Private Network Attachment)
+---------------------------------------------------+---------------------------------------------------+
|                                                   |                                                   |
|   PURCHASING RUNTIME PROJECT                      |               SELLER RUNTIME PROJECT              |
|        (agent-runtime1)                           |                  (agent-runtime2)                 |
|                                                   |                                                   |
|  +---------------------------------------------+  |  +---------------------------------------------+  |
|  |         Purchasing Concierge Agent          |  |  |     Burger Agent     |   Pizza Agent          |  |
|  |         (Identity: AGENT_IDENTITY)          |  |  |   (Seller Agent)     | (Seller Agent)         |  |
|  +----------------------+----------------------+  |  +----------------------+----------------------+  |
|                         |                         |                         ^                         |
+-------------------------|-------------------------+-------------------------|-------------------------+
                          | (Egress via AGW)                                  | (Target Reasoning Engines)
                          v                                                   |
+-----------------------------------------------------------------------------|-------------------------+
|                                  CENTRAL GOVERNANCE PROJECT                 |                         |
|                               (centralized-governance-project)              |                         |
|                                                                             |                         |
|  +--------------------------------------------------------------------------+----------------------+  |
|  |                             Central Agent Gateway (centralized-agw)                             |  |
|  +--------------------------------------------------+----------------------------------------------+  |
|                                                     |                                                 |
|  +--------------------------------------------------v----------------------------------------------+  |
|  |                                    Central Agent Registry                                       |  |
|  |  +------------------------------------------+  +---------------------------------------------+  |  |
|  |  |  Purchasing Concierge Agent              |  |  | Burger Agent (ALLOW)| Pizza Agent (BLOCK)  |  |  |
|  |  +------------------------------------------+  +---------------------------------------------+  |  |
|  +-------------------------------------------------------------------------------------------------+  |
+-------------------------------------------------------------------------------------------------------+
```

### What you build
In this codelab, you will:
- Set up network infrastructure on a **Shared VPC** (`dev-host-project-505021`) using Private Service Connect (PSC) attachments.
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
- How to route Vertex AI Agent Runtime egress through a central Agent Gateway across Shared VPC networks.
- How to use SPIFFE-based **Agent Identity** (`types.IdentityType.AGENT_IDENTITY`) for fine-grained governance.
- How to manually register agents in Agent Registry (`gcloud agent-registry services create ... --agent-spec-type=no-spec`).
- How to configure IAP Egress policies on Agent Registry resources using `gcloud beta iap web add-iam-policy-binding` with `--agent` resource scope.

---

## 2. Setup and Requirements
duration: 5

### Environment Variables
To make this codelab completely portable and reusable across environments, we define variable names for all project IDs, regions, and resources. **Do not hardcode project IDs or regions.**

Set the environment variables in your terminal:

```bash
# 1. Shared VPC Host Project
export HOST_PROJECT_ID="dev-host-project-505021"

# 2. Centralized Governance Project (Gateway & Registry)
export GOOGLE_CLOUD_PROJECT_GOVERNANCE="centralized-governance-project"

# 3. Concierge Runtime Project (Purchasing Concierge Agent)
export GOOGLE_CLOUD_PROJECT_CONCIERGE="agent-runtime1"

# 4. Sellers Runtime Project (Burger & Pizza Seller Agents)
export GOOGLE_CLOUD_PROJECT_SELLERS="agent-runtime2"

# 5. Regional & Gateway Settings
export REGION="us-central1"
export GATEWAY_NAME="centralized-agw"
export NETWORK_NAME="spvpc-network"
export SUBNET_NAME="agw-subnet"
export ATTACHMENT_NAME="agw-psc-attachment"
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
Grant organization-wide (or project-wide) `roles/iap.egressor` permissions so that all agents routing through Agent Gateway can communicate with core Google APIs:

```bash
# 1. Get Organization ID
export ORGANIZATION_ID=$(gcloud projects describe $GOOGLE_CLOUD_PROJECT_GOVERNANCE --format="value(parent.id)")

# 2. Extract core-gapi-services Endpoint ID
export CORE_GAPI_ENDPOINT_ID=$(gcloud agent-registry services describe core-gapi-services \
  --project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE \
  --location=$REGION \
  --format="value(registryResource)" | awk -F'/' '{print $NF}')

# 3. Grant IAP Egressor Policy
gcloud beta iap web add-iam-policy-binding \
  --resource-type=agent-registry \
  --endpoint=$CORE_GAPI_ENDPOINT_ID \
  --region=$REGION \
  --project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE \
  --role="roles/iap.egressor" \
  --member="principalSet://agents.global.org-${ORGANIZATION_ID}.system.id.goog/*"
```

---

## 3. Configure Shared VPC and Private Service Connect
duration: 10

Agent Gateway in `googleManaged` egress mode connects to target networks using Private Service Connect (PSC) Network Attachments.

### Step 1: Create Subnet and PSC Network Attachment in Shared VPC
In the Shared VPC host project (`$HOST_PROJECT_ID`), create a dedicated `/28` subnet for Agent Gateway egress and create a PSC Network Attachment with `ACCEPT_AUTOMATIC`:

```bash
# Create Subnet for PSC Attachment
gcloud compute networks subnets create $SUBNET_NAME \
  --project=$HOST_PROJECT_ID \
  --network=$NETWORK_NAME \
  --region=$REGION \
  --range=10.100.0.0/28

# Create PSC Network Attachment
gcloud compute network-attachments create $ATTACHMENT_NAME \
  --project=$HOST_PROJECT_ID \
  --region=$REGION \
  --subnets=$SUBNET_NAME \
  --connection-preference=ACCEPT_AUTOMATIC
```

### Step 2: Retrieve Network Attachment Resource Path
```bash
export NETWORK_ATTACHMENT_PATH="projects/$HOST_PROJECT_ID/regions/$REGION/networkAttachments/$ATTACHMENT_NAME"
echo "PSC Attachment Path: $NETWORK_ATTACHMENT_PATH"
```

---

## 4. Deploy Centralized Agent Gateway
duration: 10

Deploy the centralized Agent Gateway (`centralized-agw`) in `AGENT_TO_ANYWHERE` egress mode inside the `$GOOGLE_CLOUD_PROJECT_GOVERNANCE` project.

### Step 1: Define Gateway Configuration Manifest
Create `agw-centralized.yaml`:

```bash
cat <<EOF > agw-centralized.yaml
name: ${GATEWAY_NAME}
protocols:
  - MCP
googleManaged:
  governedAccessPath: AGENT_TO_ANYWHERE
registries:
  - projects/${GOOGLE_CLOUD_PROJECT_GOVERNANCE}/locations/${REGION}
networkConfig:
  egress:
    networkAttachment: ${NETWORK_ATTACHMENT_PATH}
EOF

# Deploy Centralized Agent Gateway
gcloud alpha network-services agent-gateways import ${GATEWAY_NAME} \
  --project=${GOOGLE_CLOUD_PROJECT_GOVERNANCE} \
  --location=${REGION} \
  --source=agw-centralized.yaml
```

### Step 2: Grant Cross-Project Access to Runtime Service Agents
The Vertex AI service agents in both runtime projects (`$GOOGLE_CLOUD_PROJECT_CONCIERGE` and `$GOOGLE_CLOUD_PROJECT_SELLERS`) require cross-project IAM permissions to inspect the Agent Gateway in `$GOOGLE_CLOUD_PROJECT_GOVERNANCE`:

```bash
# 1. Create Custom IAM Role in Governance Project
gcloud iam roles create ar_agw_cross_project_sa \
  --project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE \
  --title="Runtime Agent Gateway Cross-Project SA" \
  --description="Custom role for Runtime Service Agents to inspect Agent Gateway" \
  --permissions="networkservices.agentGateways.get,networkservices.operations.get"

# 2. Grant Role to Concierge Service Agent
gcloud projects add-iam-policy-binding $GOOGLE_CLOUD_PROJECT_GOVERNANCE \
  --member="serviceAccount:service-${PROJECT_NUMBER_CONCIERGE}@gcp-sa-aiplatform.iam.gserviceaccount.com" \
  --role="projects/${GOOGLE_CLOUD_PROJECT_GOVERNANCE}/roles/ar_agw_cross_project_sa"

# 3. Grant Role to Sellers Service Agent
gcloud projects add-iam-policy-binding $GOOGLE_CLOUD_PROJECT_GOVERNANCE \
  --member="serviceAccount:service-${PROJECT_NUMBER_SELLERS}@gcp-sa-aiplatform.iam.gserviceaccount.com" \
  --role="projects/${GOOGLE_CLOUD_PROJECT_GOVERNANCE}/roles/ar_agw_cross_project_sa"
```

---

## 5. Deploy Seller Agents to agent-runtime2
duration: 15

Deploy both the **Burger Seller Agent** and **Pizza Seller Agent** to Vertex AI Reasoning Engine in `$GOOGLE_CLOUD_PROJECT_SELLERS` (`agent-runtime2`). Both deployments will specify the centralized gateway (`centralized-agw` in `$GOOGLE_CLOUD_PROJECT_GOVERNANCE`) and attach `types.IdentityType.AGENT_IDENTITY`.

### Deploy Seller Agents
```bash
uv run python deploy_sellers_adk.py \
  --project=$GOOGLE_CLOUD_PROJECT_SELLERS \
  --region=$REGION \
  --gateway-name=$GATEWAY_NAME \
  --gateway-project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE
```

> [!NOTE]
> **Understanding Agent Gateway Parameter Resolution**:
> The Python deployment script takes `--gateway-project` (`centralized-governance-project`) and `--gateway-name` (`centralized-agw`) and constructs the full Agent Gateway resource path required by the Vertex AI Agent Engine runtime:
> `projects/centralized-governance-project/locations/us-central1/agentGateways/centralized-agw`

### Extract Reasoning Engine IDs
Upon successful deployment, `deploy_sellers_adk.py` saves the deployed resource IDs into `seller_agents.env`:

```bash
source seller_agents.env
export BURGER_ENGINE_ID=$(echo $BURGER_SELLER_AGENT_ID | awk -F'/' '{print $NF}')
export PIZZA_ENGINE_ID=$(echo $PIZZA_SELLER_AGENT_ID | awk -F'/' '{print $NF}')

echo "Burger Engine ID: $BURGER_ENGINE_ID"
echo "Pizza Engine ID:  $PIZZA_ENGINE_ID"
```

---

## 6. Deploy Purchasing Concierge Agent to agent-runtime1
duration: 10

Deploy the **Purchasing Concierge Agent** to Vertex AI Reasoning Engine in `$GOOGLE_CLOUD_PROJECT_CONCIERGE` (`agent-runtime1`).

```bash
uv run python deploy_concierge_adk.py \
  --project=$GOOGLE_CLOUD_PROJECT_CONCIERGE \
  --region=$REGION \
  --gateway-name=$GATEWAY_NAME \
  --gateway-project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE
```

> [!NOTE]
> **Dynamic Agent Registry Auto-Discovery**:
> The Purchasing Concierge ADK agent dynamically queries the Central Agent Registry in `$GOOGLE_CLOUD_PROJECT_GOVERNANCE` (`GOVERNANCE_PROJECT_ID`) at runtime to auto-discover the registered seller agent endpoints (Pizza Seller Agent and Burger Seller Agent). This eliminates hardcoding agent resource IDs or project numbers, making seller agent discovery completely dynamic.

Extract the Concierge Reasoning Engine ID:
```bash
export CONCIERGE_ENGINE_ID=$(gcloud aiplatform reasoning-engines list \
  --project=$GOOGLE_CLOUD_PROJECT_CONCIERGE \
  --region=$REGION \
  --filter="displayName:purchasing-concierge-adk" \
  --format="value(name)" | awk -F'/' '{print $NF}')

echo "Concierge Engine ID: $CONCIERGE_ENGINE_ID"
```

---

## 7. Manually Register Agents in Central Agent Registry
duration: 10

Register all three agents (`burger-seller-agent`, `pizza-seller-agent`, and `purchasing-concierge-adk`) in the **Central Agent Registry** in `$GOOGLE_CLOUD_PROJECT_GOVERNANCE`.

Using `--agent-spec-type=no-spec` creates a Service resource that Agent Registry automatically projects as a read-only **Agent** resource under `/agents/`.

### Step 1: Register Pizza Seller Agent
```bash
gcloud agent-registry services create pizza-seller-agent \
  --project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE \
  --location=$REGION \
  --display-name="Pizza Seller Agent" \
  --description="Pizza Seller Agent reasoning engine in agent-runtime2" \
  --agent-spec-type=no-spec \
  --interfaces="protocolBinding=JSONRPC,url=https://${REGION}-aiplatform.mtls.googleapis.com/v1/projects/${PROJECT_NUMBER_SELLERS}/locations/${REGION}/reasoningEngines/${PIZZA_ENGINE_ID}"
```

### Step 2: Register Burger Seller Agent
```bash
gcloud agent-registry services create burger-seller-agent \
  --project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE \
  --location=$REGION \
  --display-name="Burger Seller Agent" \
  --description="Burger Seller Agent reasoning engine in agent-runtime2" \
  --agent-spec-type=no-spec \
  --interfaces="protocolBinding=JSONRPC,url=https://${REGION}-aiplatform.mtls.googleapis.com/v1/projects/${PROJECT_NUMBER_SELLERS}/locations/${REGION}/reasoningEngines/${BURGER_ENGINE_ID}"
```

### Step 3: Register Purchasing Concierge ADK Agent
```bash
gcloud agent-registry services create purchasing-concierge-adk \
  --project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE \
  --location=$REGION \
  --display-name="Purchasing Concierge ADK" \
  --description="Purchasing Concierge ADK reasoning engine in agent-runtime1" \
  --agent-spec-type=no-spec \
  --interfaces="protocolBinding=JSONRPC,url=https://${REGION}-aiplatform.mtls.googleapis.com/v1/projects/${PROJECT_NUMBER_CONCIERGE}/locations/${REGION}/reasoningEngines/${CONCIERGE_ENGINE_ID}"
```

### Step 4: Extract Projected Agent Resource IDs
List the registered Agent resources and extract their projected Agent IDs (`agentregistry-...`):

```bash
gcloud alpha agent-registry agents list \
  --project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE \
  --location=$REGION \
  --format="table(displayName, name.basename():label=AGENT_ID, protocols[0].interfaces[0].url)"
```

Extract each Agent ID for IAM policy binding:
```bash
export BURGER_AGENT_ID=$(gcloud alpha agent-registry agents list --project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE --location=$REGION --filter="displayName='Burger Seller Agent'" --format="value(name.basename())")
export PIZZA_AGENT_ID=$(gcloud alpha agent-registry agents list --project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE --location=$REGION --filter="displayName='Pizza Seller Agent'" --format="value(name.basename())")
export CONCIERGE_AGENT_ID=$(gcloud alpha agent-registry agents list --project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE --location=$REGION --filter="displayName='Purchasing Concierge ADK'" --format="value(name.basename())")

echo "Burger Projected Agent ID:    $BURGER_AGENT_ID"
echo "Pizza Projected Agent ID:     $PIZZA_AGENT_ID"
echo "Concierge Projected Agent ID: $CONCIERGE_AGENT_ID"
```

---

## 8. Configure Access Control Policies (Allow Burger / Block Pizza)
duration: 10

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

### Step 2: Grant ALLOW Policy for Burger Agent
Grant the Concierge Agent the `roles/iap.egressor` role on the Burger Agent in Central Agent Registry using `gcloud beta iap web add-iam-policy-binding`:

```bash
gcloud beta iap web add-iam-policy-binding \
  --resource-type=agent-registry \
  --agent=$BURGER_AGENT_ID \
  --region=$REGION \
  --project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE \
  --role="roles/iap.egressor" \
  --member="$CONCIERGE_SPIFFE_PRINCIPAL"
```

### Step 3: Enforce BLOCK Policy for Pizza Agent
Because Agent Gateway enforces **Default Deny**, omitting the `roles/iap.egressor` binding for the Pizza Agent ensures that any invocation attempted by the Concierge Agent to the Pizza Agent will be rejected by Agent Gateway with **HTTP 403 Forbidden**.

If an IAM binding previously existed, remove it explicitly:

```bash
gcloud beta iap web remove-iam-policy-binding \
  --resource-type=agent-registry \
  --agent=$PIZZA_AGENT_ID \
  --region=$REGION \
  --project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE \
  --role="roles/iap.egressor" \
  --member="$CONCIERGE_SPIFFE_PRINCIPAL" || true
```

### Step 4: Validate Agent IAM Policies
Verify the updated IAP IAM policies for all agents:

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

## 9. Test and Verify Governance Policies
duration: 10

Now verify that cross-project A2A communication properly obeys the IAP access control policies enforced by Agent Gateway.

### Test 1: Query Burger Agent (Expected: SUCCESS)
Query the Purchasing Concierge to order a Burger:

```bash
export AUTH_TOKEN=$(gcloud auth print-access-token)

curl -X POST \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  "https://${REGION}-aiplatform.googleapis.com/v1/projects/${GOOGLE_CLOUD_PROJECT_CONCIERGE}/locations/${REGION}/reasoningEngines/${CONCIERGE_ENGINE_ID}:query" \
  -d '{
    "input": {
      "message": "Order a double cheeseburger with extra bacon from the burger agent",
      "user_id": "codelab-user-1"
    }
  }' | jq .
```

#### Expected Result:
The query routes through Agent Gateway, IAP evaluates the ALLOW policy for the Burger Agent, approves the request, and returns a successful order confirmation:
```json
{
  "output": "Burger order placed successfully! Order ID: BURGER-8821"
}
```

---

### Test 2: Query Pizza Agent (Expected: BLOCKED / 403 FORBIDDEN)
Query the Purchasing Concierge to order a Pizza:

```bash
curl -X POST \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  "https://${REGION}-aiplatform.googleapis.com/v1/projects/${GOOGLE_CLOUD_PROJECT_CONCIERGE}/locations/${REGION}/reasoningEngines/${CONCIERGE_ENGINE_ID}:query" \
  -d '{
    "input": {
      "message": "Order a large pepperoni pizza from the pizza agent",
      "user_id": "codelab-user-1"
    }
  }' | jq .
```

#### Expected Result:
Agent Gateway intercepts the outbound request from Concierge to Pizza Agent, evaluates IAP authorization, finds **NO** `roles/iap.egressor` binding, and **BLOCKS** the communication:
```json
{
  "error": {
    "code": 403,
    "message": "Permission denied: Agent Gateway blocked egress call to pizza-seller-agent due to IAP policy constraint.",
    "status": "PERMISSION_DENIED"
  }
}
```

---

## 10. Clean Up
duration: 5

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

### Step 4: Delete PSC Network Attachment & Subnet
```bash
gcloud compute network-attachments delete $ATTACHMENT_NAME \
  --project=$HOST_PROJECT_ID \
  --region=$REGION --quiet

gcloud compute networks subnets delete $SUBNET_NAME \
  --project=$HOST_PROJECT_ID \
  --region=$REGION --quiet
```

---

## 11. Congratulations!
duration: 1

You have successfully built, deployed, and governed a multi-project **Agent-to-Agent (A2A)** architecture on Google Cloud using **Agent Gateway**, **Agent Registry**, **Agent Identity**, and **Shared VPC Private Service Connect**.

### What you accomplished:
- Configured cross-project Shared VPC networking and Private Service Connect attachments.
- Built a centralized **Agent Gateway** (`centralized-agw`) in `AGENT_TO_ANYWHERE` mode.
- Deployed Concierge in `agent-runtime1` and Seller Agents in `agent-runtime2`.
- Manually registered all three agents in **Central Agent Registry** (`gcloud agent-registry services create ... --agent-spec-type=no-spec`).
- Enforced **IAP Egress Governance Policies** using `gcloud beta iap web add-iam-policy-binding` with `--agent` resource flags:
  - **ALLOWED** Concierge -> Burger Agent.
  - **BLOCKED** Concierge -> Pizza Agent with HTTP `403 Forbidden`.
- Verified policy enforcement live using REST calls.
