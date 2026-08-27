# Gemini Enterprise (GE) Agent Import Guide

This document details the exact **Working A2A Agent Card JSON** and **IAM Permissions** required to import and execute agents from **Agent Registry** into **Gemini Enterprise (Discovery Engine)** through the **Central Agent Gateway**.

---

## 1. Working A2A Agent Card JSON

Save this configuration as `burger_agent_card.json`.

```json
{
  "name": "Burger Seller Agent",
  "description": "Specialized seller agent for browsing burger menus, checking pricing, and placing orders.",
  "version": "1.0.0",
  "protocolVersion": "0.3.0",
  "preferredTransport": "JSONRPC",
  "url": "https://us-central1-aiplatform.googleapis.com/v1/projects/439077346891/locations/us-central1/reasoningEngines/1226814733307346944:streamQuery",
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

### Critical Rules for the Agent Card:
1. **Omit `securitySchemes`**: Excluding the `securitySchemes` block ensures Gemini Enterprise recognizes that runtime permissions (Google Cloud IAM / Agent Gateway) govern the agent and does not prompt for external OAuth 2.0 Client ID / Secret.
2. **Use IANA MIME Types**: `defaultInputModes` and `defaultOutputModes` must be valid MIME types (e.g. `text/plain`), not informal strings like `"text"`.
3. **Specify `protocolVersion: "0.3.0"` & `preferredTransport: "JSONRPC"`**: Required by the console frontend parser to select the appropriate adapter.
4. **Skills Format**: Keep skills clean using `id`, `name`, `description`, `tags`, and `examples`. Avoid inserting nested OpenAPI schemas (`parameters: { properties: ... }`) directly into skill blocks, as this triggers `Failed to parse agent card` in the client-side validator.

---

## 2. Agent Registry Deployment Command

To apply or update the A2A Agent Card on the Agent Registry service in `PROJECT_GOVERNANCE` (`deepakmichaelprod`):

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

## 3. Required IAM & IAP Permissions

Cross-project agent execution from Gemini Enterprise requires permissions across three layers:

```
┌─────────────────────────────────────────────────────────────┐
│ Gemini Enterprise Assistant                                 │
│ principal://.../resources/discoveryengine/...               │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼ [roles/iap.egressor]
┌─────────────────────────────────────────────────────────────┐
│ Central Agent Gateway / IAP (deepakmichaelprod)            │
│ Target: burger-seller-agent (agentregistry-...)             │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼ [roles/aiplatform.user]
┌─────────────────────────────────────────────────────────────┐
│ Vertex AI Reasoning Engine (deepakmichaelstage)             │
│ Target: 1226814733307346944                                 │
└─────────────────────────────────────────────────────────────┘
```

### Layer A: Gemini Enterprise Discovery Engine Service Agent

The service agent (`service-114740196141@gcp-sa-discoveryengine.iam.gserviceaccount.com`) needs permissions to discover services in the governance project and invoke the runtime in the seller project.

#### 1. Governance Project (`deepakmichaelprod`):
```bash
# Allow Gemini Enterprise to discover agents and read card specifications
gcloud projects add-iam-policy-binding deepakmichaelprod \
  --member="serviceAccount:service-114740196141@gcp-sa-discoveryengine.iam.gserviceaccount.com" \
  --role="roles/agentregistry.viewer"

# Allow Gemini Enterprise to inspect Central Agent Gateway routes and service attachments
gcloud projects add-iam-policy-binding deepakmichaelprod \
  --member="serviceAccount:service-114740196141@gcp-sa-discoveryengine.iam.gserviceaccount.com" \
  --role="roles/networkservices.viewer"
```

#### 2. Seller Runtime Project (`deepakmichaelstage`):
```bash
# Allow Gemini Enterprise to execute the Reasoning Engine container backend
gcloud projects add-iam-policy-binding deepakmichaelstage \
  --member="serviceAccount:service-114740196141@gcp-sa-discoveryengine.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

---

### Layer B: IAP Gateway Egress Authorization (`roles/iap.egressor`)

When Gemini Enterprise dispatches calls through the Central Agent Gateway, IAP evaluates the caller's **SPIFFE machine identity**:

```text
principal://agents.global.org-1015654926499.system.id.goog/resources/discoveryengine/projects/114740196141/locations/global/engines/deepak-ge-app_1787348960235/assistants/default_assistant/agents/registry/*
```

#### 1. Grant Egress on the Burger Agent Service:
```bash
gcloud beta iap web add-iam-policy-binding \
  --project=deepakmichaelprod \
  --region=us-central1 \
  --agent=burger-seller-agent \
  --role="roles/iap.egressor" \
  --member="principal://agents.global.org-1015654926499.system.id.goog/resources/discoveryengine/projects/114740196141/locations/global/engines/deepak-ge-app_1787348960235/assistants/default_assistant/agents/registry/*"
```

#### 2. Grant Egress on the Entire Agent Registry (Recommended):
```bash
gcloud beta iap web add-iam-policy-binding \
  --project=deepakmichaelprod \
  --region=us-central1 \
  --resource-type=agent-registry \
  --role="roles/iap.egressor" \
  --member="principal://agents.global.org-1015654926499.system.id.goog/resources/discoveryengine/projects/114740196141/locations/global/engines/deepak-ge-app_1787348960235/assistants/default_assistant/agents/registry/*"
```

#### 3. Direct REST Policy Binding (if setting policy by Agent Resource ID):
```bash
TOKEN=$(gcloud auth application-default print-access-token)

curl -s -X POST "https://iap.googleapis.com/v1/projects/114740196141/locations/us-central1/iap_web/agentRegistry/agents/agentregistry-00000000-0000-0000-57ab-a823df81404e:setIamPolicy" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "policy": {
      "bindings": [
        {
          "role": "roles/iap.egressor",
          "members": [
            "principal://agents.global.org-1015654926499.system.id.goog/resources/discoveryengine/projects/114740196141/locations/global/engines/deepak-ge-app_1787348960235/assistants/default_assistant/agents/registry/*"
          ]
        }
      ]
    }
  }'
```

---

## 4. Verification in Cloud Logging

To confirm that Gemini Enterprise calls are evaluated and granted by IAP:

```bash
gcloud logging read \
  'logName="projects/deepakmichaelprod/logs/cloudaudit.googleapis.com%2Fdata_access" \
   AND protoPayload.serviceName="iap.googleapis.com" \
   AND protoPayload.authenticationInfo.principalSubject=~"discoveryengine"' \
  --project=deepakmichaelprod \
  --limit=5 \
  --format="table(timestamp.date('%Y-%m-%d %H:%M:%S'):label=TIME, protoPayload.authenticationInfo.principalSubject:label=SPIFFE_IDENTITY, protoPayload.authorizationInfo[0].granted:label=GRANTED, protoPayload.status.message:label=STATUS)"
```
