# Governance for Cross-Project Agent-to-Agent (A2A) Communication with Agent Gateway, Agent Registry, and Shared VPC

## 1. Introduction
duration: 5

This Codelab explores enterprise cross-project **Agent-to-Agent (A2A)** governance and dynamic autodiscovery using **Gemini Enterprise Agent Platform** components: **Agent Gateway**, **Agent Registry**, **Agent Identity**, and **Shared VPC Private Service Connect (PSC)**.

In a multi-tenant enterprise architecture, agents frequently run across isolated projects while requiring centralized governance, fine-grained access control, and dynamic service discovery.

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
                  +---------------------------------+---------------------------------+
                  |                                                                   |
+-----------------+-----------------------------------+   +---------------------------+-----------------------+
|          RUNTIME PROJECT (agent-runtime1)           |   |     CENTRAL GOVERNANCE PROJECT                        |
|                                                     |   |     (centralized-governance-project)                  |
|  +-----------------------------------------------+  |   |                                                       |
|  |           Purchasing Concierge Agent          |  |   |  +-------------------------------------------------+  |
|  |           (Identity: AGENT_IDENTITY)          |  |   |  |     Central Agent Gateway (centralized-agw)      |  |
|  +-----------------------+-----------------------+  |   |  +------------------------+------------------------+  |
|                          |                          |   |                           |                           |
|                          |                          |   |  +------------------------v------------------------+  |
|                          | (Egress via AGW)         |   |  |           Central Agent Registry                |  |
|                          v                          |   |  |  +-------------------+   +-------------------+  |  |
|  +-----------------------------------------------+  |   |  |  | Burger Agent (ALLOW) | | Pizza Agent (BLOCK)| |  |
|  |     Burger Agent     |   Pizza Agent          |  |   |  |  +-------------------+   +-------------------+  |  |
|  |   (Seller Agent)     | (Seller Agent)         |  |   |  +-------------------------------------------------+  |
|  +----------------------+------------------------+  |   |                                                       |
+-----------------------------------------------------+   +-------------------------------------------------------+
```

### What you build
In this codelab, you will:
- Set up network infrastructure on a **Shared VPC** (`dev-host-project-505021`) using Private Service Connect (PSC) attachments.
- Deploy a **Centralized Agent Gateway** (`centralized-agw`) in `AGENT_TO_ANYWHERE` egress mode in the `centralized-governance-project`.
- Deploy specialist **Burger Seller Agent** and **Pizza Seller Agent** in the `agent-runtime1` project.
- Register both seller agents in the **Central Agent Registry** in `centralized-governance-project`.
- Enforce **Identity-Aware Proxy (IAP) Egress Policies**:
  - **ALLOW** policy: Grant the Purchasing Concierge permission to invoke the Burger Agent.
  - **BLOCK** policy: Deny the Purchasing Concierge permission to invoke the Pizza Agent.
- Deploy the **Purchasing Concierge Agent** in `agent-runtime1` using `AgentRegistry.list_agents()` for dynamic discovery.
- Perform end-to-end testing to verify that Burger calls succeed and Pizza calls are blocked by Agent Gateway with `HTTP 403 Forbidden`.

### What you learn
- How to configure cross-project service agent IAM permissions for centralized gateways.
- How to route Vertex AI Agent Runtime egress through a central Agent Gateway across Shared VPC networks.
- How to use SPIFFE-based **Agent Identity** (`types.IdentityType.AGENT_IDENTITY`) for fine-grained governance.
- How to configure IAP Egress policies on Agent Registry endpoints to ALLOW or DENY specific inter-agent calls.

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

# 3. Agent Runtime Project (Concierge, Burger, Pizza Agents)
export GOOGLE_CLOUD_PROJECT_RUNTIME="agent-runtime1"

# 4. Regional & Gateway Settings
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
export PROJECT_NUMBER_RUNTIME=$(gcloud projects describe $GOOGLE_CLOUD_PROJECT_RUNTIME --format="value(projectNumber)")

echo "Governance Project Number: $PROJECT_NUMBER_GOVERNANCE"
echo "Runtime Project Number:    $PROJECT_NUMBER_RUNTIME"
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

# Runtime Project APIs
gcloud services enable \
  aiplatform.googleapis.com \
  storage.googleapis.com \
  --project=$GOOGLE_CLOUD_PROJECT_RUNTIME
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

```yaml
name: centralized-agw
protocols:
  - MCP
googleManaged:
  governedAccessPath: AGENT_TO_ANYWHERE
registries:
  - projects/centralized-governance-project/locations/us-central1
networkConfig:
  egress:
    networkAttachment: projects/dev-host-project-505021/regions/us-central1/networkAttachments/agw-psc-attachment
```

Create the resource dynamically with variable substitution:

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

### Step 2: Grant Cross-Project Access to Runtime Service Agent
The Agent Runtime service agent in `$GOOGLE_CLOUD_PROJECT_RUNTIME` requires cross-project IAM permissions to describe the Agent Gateway in `$GOOGLE_CLOUD_PROJECT_GOVERNANCE`:

```bash
# 1. Create Custom IAM Role in Governance Project
gcloud iam roles create ar_agw_cross_project_sa \
  --project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE \
  --title="Runtime Agent Gateway Cross-Project SA" \
  --description="Custom role for Runtime Service Agent to inspect Agent Gateway" \
  --permissions="networkservices.agentGateways.get,networkservices.operations.get"

# 2. Grant Role to Runtime Service Agent
gcloud projects add-iam-policy-binding $GOOGLE_CLOUD_PROJECT_GOVERNANCE \
  --member="serviceAccount:service-${PROJECT_NUMBER_RUNTIME}@gcp-sa-aiplatform.iam.gserviceaccount.com" \
  --role="projects/${GOOGLE_CLOUD_PROJECT_GOVERNANCE}/roles/ar_agw_cross_project_sa"
```

---

## 5. Deploy Seller Agents to Vertex AI Agent Runtime
duration: 15

Now deploy both the **Burger Seller Agent** and **Pizza Seller Agent** to Vertex AI Reasoning Engine in `$GOOGLE_CLOUD_PROJECT_RUNTIME`. Both deployments will specify the centralized gateway (`centralized-agw` in `$GOOGLE_CLOUD_PROJECT_GOVERNANCE`) and attach `types.IdentityType.AGENT_IDENTITY`.

### Code Overview (`deploy_sellers_adk.py`)

Deploy the seller agents using the repository script:

```bash
uv run python deploy_sellers_adk.py \
  --project=$GOOGLE_CLOUD_PROJECT_RUNTIME \
  --region=$REGION \
  --gateway-name=$GATEWAY_NAME \
  --gateway-project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE
```

### Verify Seller Agent Deployment Outputs
Upon successful deployment, `deploy_sellers_adk.py` saves the deployed resource IDs into `seller_agents.env`:

```bash
cat seller_agents.env
```

Example Output:
```bash
BURGER_SELLER_AGENT_ID=projects/933480738993/locations/us-central1/reasoningEngines/1234567890123456789
PIZZA_SELLER_AGENT_ID=projects/933480738993/locations/us-central1/reasoningEngines/9876543210987654321
```

Extract the numerical engine IDs:
```bash
source seller_agents.env
export BURGER_ENGINE_ID=$(echo $BURGER_SELLER_AGENT_ID | awk -F'/' '{print $NF}')
export PIZZA_ENGINE_ID=$(echo $PIZZA_SELLER_AGENT_ID | awk -F'/' '{print $NF}')

echo "Burger Engine ID: $BURGER_ENGINE_ID"
echo "Pizza Engine ID:  $PIZZA_ENGINE_ID"
```

---

## 6. Register Seller Agents in Central Agent Registry
duration: 10

Both the Burger and Pizza seller agents must be registered in the **Central Agent Registry** in `$GOOGLE_CLOUD_PROJECT_GOVERNANCE` so that the Agent Gateway and the Purchasing Concierge can discover and govern them.

### Step 1: Register Burger Seller Agent
```bash
export BURGER_SERVICE_NAME="burger-seller-service"

gcloud agent-registry services create $BURGER_SERVICE_NAME \
  --project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE \
  --location=$REGION \
  --display-name="Burger Seller Agent Service" \
  --endpoint-spec-type=no-spec \
  --interfaces=url="https://${REGION}-aiplatform.mtls.googleapis.com/v1/projects/${PROJECT_NUMBER_RUNTIME}/locations/${REGION}/reasoningEngines/${BURGER_ENGINE_ID}",protocolBinding="jsonrpc"
```

### Step 2: Register Pizza Seller Agent
```bash
export PIZZA_SERVICE_NAME="pizza-seller-service"

gcloud agent-registry services create $PIZZA_SERVICE_NAME \
  --project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE \
  --location=$REGION \
  --display-name="Pizza Seller Agent Service" \
  --endpoint-spec-type=no-spec \
  --interfaces=url="https://${REGION}-aiplatform.mtls.googleapis.com/v1/projects/${PROJECT_NUMBER_RUNTIME}/locations/${REGION}/reasoningEngines/${PIZZA_ENGINE_ID}",protocolBinding="jsonrpc"
```

### Step 3: Extract Registry Endpoint IDs
Extract the endpoint IDs from the registry output:

```bash
export BURGER_ENDPOINT_ID=$(gcloud agent-registry services describe $BURGER_SERVICE_NAME \
  --project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE \
  --location=$REGION \
  --format="value(name)" | awk -F'/' '{print $NF}')

export PIZZA_ENDPOINT_ID=$(gcloud agent-registry services describe $PIZZA_SERVICE_NAME \
  --project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE \
  --location=$REGION \
  --format="value(name)" | awk -F'/' '{print $NF}')

echo "Burger Endpoint ID: $BURGER_ENDPOINT_ID"
echo "Pizza Endpoint ID:  $PIZZA_ENDPOINT_ID"
```

---

## 7. Configure Access Control Policies (Allow Burger / Block Pizza)
duration: 10

Agent Gateway uses **Identity-Aware Proxy (IAP)** to evaluate authorization decisions. Agent Gateway operates under a **Default Deny** security posture.

### Governance Requirement:
1. **ALLOW Policy**: The Purchasing Concierge Agent can call the Burger Agent.
2. **BLOCK Policy**: The Purchasing Concierge Agent is **DENIED** from calling the Pizza Agent.

### Step 1: Deploy Purchasing Concierge Agent (To Obtain Identity SPIFFE URI)
Deploy the Purchasing Concierge in `$GOOGLE_CLOUD_PROJECT_RUNTIME` using `deploy_concierge_adk.py`:

```bash
uv run python deploy_concierge_adk.py \
  --project=$GOOGLE_CLOUD_PROJECT_RUNTIME \
  --region=$REGION \
  --gateway-name=$GATEWAY_NAME \
  --gateway-project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE
```

Extract the Concierge Reasoning Engine ID:
```bash
export CONCIERGE_ENGINE_ID=$(gcloud aiplatform reasoning-engines list \
  --project=$GOOGLE_CLOUD_PROJECT_RUNTIME \
  --region=$REGION \
  --filter="displayName:purchasing-concierge-adk" \
  --format="value(name)" | awk -F'/' '{print $NF}')

echo "Concierge Engine ID: $CONCIERGE_ENGINE_ID"
```

### Step 2: Formulate Concierge Agent SPIFFE Identity
The SPIFFE principal identity for the Concierge Agent is:
`principal://iam.googleapis.com/projects/${PROJECT_NUMBER_RUNTIME}/locations/${REGION}/reasoningEngines/${CONCIERGE_ENGINE_ID}`

```bash
export CONCIERGE_SPIFFE_PRINCIPAL="principal://iam.googleapis.com/projects/${PROJECT_NUMBER_RUNTIME}/locations/${REGION}/reasoningEngines/${CONCIERGE_ENGINE_ID}"
echo "Concierge SPIFFE Principal: $CONCIERGE_SPIFFE_PRINCIPAL"
```

### Step 3: Grant ALLOW Policy for Burger Agent Endpoint
Grant the Concierge Agent the `roles/iap.egressor` role on the Burger Agent endpoint in the Central Agent Registry:

```bash
gcloud iap web add-iam-policy-binding \
  --resource-type=agent-registry \
  --endpoint=$BURGER_ENDPOINT_ID \
  --region=$REGION \
  --project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE \
  --member="$CONCIERGE_SPIFFE_PRINCIPAL" \
  --role=roles/iap.egressor
```

### Step 4: Enforce BLOCK Policy for Pizza Agent Endpoint
Because Agent Gateway enforces **Default Deny**, omitting the `roles/iap.egressor` binding for the Pizza Agent endpoint ensures that any invocation attempted by the Concierge Agent to the Pizza Agent will be rejected by Agent Gateway with **HTTP 403 Forbidden**.

If an IAM binding previously existed, remove it explicitly:

```bash
gcloud iap web remove-iam-policy-binding \
  --resource-type=agent-registry \
  --endpoint=$PIZZA_ENDPOINT_ID \
  --region=$REGION \
  --project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE \
  --member="$CONCIERGE_SPIFFE_PRINCIPAL" \
  --role=roles/iap.egressor || true
```

---

## 8. Test and Verify Governance Policies
duration: 10

Now verify that cross-project A2A communication properly obeys the IAP access control policies enforced by Agent Gateway.

### Test 1: Query Burger Agent (Expected: SUCCESS)
Query the Purchasing Concierge to order a Burger:

```bash
export AUTH_TOKEN=$(gcloud auth print-access-token)

curl -X POST \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  "https://${REGION}-aiplatform.googleapis.com/v1/projects/${GOOGLE_CLOUD_PROJECT_RUNTIME}/locations/${REGION}/reasoningEngines/${CONCIERGE_ENGINE_ID}:query" \
  -d '{
    "input": {
      "message": "Order a double cheeseburger with extra bacon from the burger agent",
      "user_id": "codelab-user-1"
    }
  }' | jq .
```

#### Expected Result:
The query routes through Agent Gateway, IAP evaluates the ALLOW policy for the Burger endpoint, approves the request, and returns a successful order confirmation:
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
  "https://${REGION}-aiplatform.googleapis.com/v1/projects/${GOOGLE_CLOUD_PROJECT_RUNTIME}/locations/${REGION}/reasoningEngines/${CONCIERGE_ENGINE_ID}:query" \
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
    "message": "Permission denied: Agent Gateway blocked egress call to pizza-seller-service due to IAP policy constraint.",
    "status": "PERMISSION_DENIED"
  }
}
```

---

## 9. Clean Up
duration: 5

To prevent incurring ongoing charges to your Google Cloud account, delete the resources created during this Codelab.

### Step 1: Clean Up Reasoning Engine Deployments
Run the cleanup script to remove Reasoning Engines in `$GOOGLE_CLOUD_PROJECT_RUNTIME`:

```bash
uv run python cleanup_old_deployments.py
```

### Step 2: Delete Agent Registry Services
```bash
gcloud agent-registry services delete $BURGER_SERVICE_NAME \
  --project=$GOOGLE_CLOUD_PROJECT_GOVERNANCE \
  --location=$REGION --quiet

gcloud agent-registry services delete $PIZZA_SERVICE_NAME \
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

## 10. Congratulations!
duration: 1

You have successfully built, deployed, and governed a multi-project **Agent-to-Agent (A2A)** architecture on Google Cloud using **Agent Gateway**, **Agent Registry**, **Agent Identity**, and **Shared VPC Private Service Connect**.

### What you accomplished:
- Configured cross-project Shared VPC networking and Private Service Connect attachments.
- Built a centralized **Agent Gateway** (`centralized-agw`) in `AGENT_TO_ANYWHERE` mode.
- Deployed seller agents and registered them in a central **Agent Registry**.
- Enforced **IAP Egress Governance Policies**:
  - **ALLOWED** Concierge -> Burger Agent.
  - **BLOCKED** Concierge -> Pizza Agent with HTTP `403 Forbidden`.
- Verified policy enforcement live using REST calls.
