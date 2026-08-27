# Gemini Enterprise (GE) Agent Import & Execution Guide

This document is the definitive guide for importing and executing agents from **Agent Registry** into **Gemini Enterprise (Discovery Engine)** through the **Central Agent Gateway**.

---

## Architecture Flow

```
┌──────────────────────────────────────────────────────────────┐
│ Gemini Enterprise Assistant                                  │
│ Identity: principal://.../resources/discoveryengine/...       │
│ Credential: Authorization: Bearer <Google OAuth Token>       │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼ [roles/iap.egressor]
┌──────────────────────────────────────────────────────────────┐
│ Central Agent Gateway / IAP (deepakmichaelprod)             │
│ Evaluates IAP Egressor Policy & Security Policies            │
│ Target: burger-seller-agent (agentregistry-...)              │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼ [roles/aiplatform.user]
┌──────────────────────────────────────────────────────────────┐
│ Vertex AI Reasoning Engine (deepakmichaelstage)              │
│ Endpoint: .../reasoningEngines/1226814733307346944:streamQuery│
└──────────────────────────────────────────────────────────────┘
```

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
  "securitySchemes": {
    "googleOAuth": {
      "type": "oauth2",
      "description": "Google Cloud OAuth 2.0 Authentication",
      "flows": {
        "authorizationCode": {
          "authorizationUrl": "https://accounts.google.com/o/oauth2/v2/auth?access_type=offline&prompt=consent",
          "tokenUrl": "https://oauth2.googleapis.com/token",
          "scopes": {
            "https://www.googleapis.com/auth/cloud-platform": "Access to Google Cloud Platform"
          }
        }
      }
    }
  },
  "security": [
    {
      "googleOAuth": [
        "https://www.googleapis.com/auth/cloud-platform"
      ]
    }
  ],
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

### Critical Specification Requirements:
1. **Target URL (`url`)**:
   * Must point to `:streamQuery` (or `:query`).
   * **Do NOT** use bare `/reasoningEngines/{id}`, which returns `404 Not Found`.
2. **Security Block (`securitySchemes` & `security`)**:
   * Must declare `bearerAuth` so Gemini Enterprise prompts for and attaches an `Authorization: Bearer <token>` header to outbound HTTP calls.
   * Without this, Gemini Enterprise sends unauthenticated requests, triggering `401 CREDENTIALS_MISSING`.
3. **MIME Types**:
   * `defaultInputModes` and `defaultOutputModes` must use IANA MIME types (`text/plain`, `application/json`), not generic `"text"`.
4. **Protocol & Transport**:
   * Must specify `protocolVersion: "0.3.0"` and `preferredTransport: "JSONRPC"`. Top-level `"1.0"` is rejected by Agent Registry for single-agent endpoints.
5. **Skills Schema**:
   * Must use canonical A2A fields: `id`, `name`, `description`, `tags`, `examples`, `inputModes`, `outputModes`.
   * **Do NOT** embed OpenAPI `parameters: { properties: ... }` schemas into skill definitions, which breaks the frontend Angular parser.

---

## 2. Agent Registry Deployment Command

To register or update the agent card in `PROJECT_GOVERNANCE` (`deepakmichaelprod`):

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

## 3. OAuth 2.0 Configuration for Gemini Enterprise

When importing an agent with `securitySchemes`, Gemini Enterprise requires OAuth client details to acquire access tokens for calling Google Cloud APIs:

| Configuration Field | Value | Description |
| :--- | :--- | :--- |
| **Application Type** | `Web application` | OAuth 2.0 Client Type in Google Cloud Console |
| **Authorized Redirect URI** | `https://vertexaisearch.cloud.google.com/oauth-redirect` | Exact redirect URI required by Gemini Enterprise |
| **Client ID** | `<YOUR_OAUTH_CLIENT_ID>` | OAuth 2.0 Web Client ID generated in Google Cloud Console |
| **Client Secret** | `<YOUR_OAUTH_CLIENT_SECRET>` | OAuth 2.0 Web Client Secret generated in Google Cloud Console |
| **Authorization URL** | `https://accounts.google.com/o/oauth2/v2/auth?access_type=offline&prompt=consent` | Google OAuth 2.0 Authorization Endpoint (`access_type=offline` required for refresh token) |
| **Token URL** | `https://oauth2.googleapis.com/token` | Google OAuth 2.0 Token Exchange Endpoint |
| **Scopes** | `https://www.googleapis.com/auth/cloud-platform` | Scope required to invoke Vertex AI APIs |

*(These URLs and scopes are now pre-populated in the Agent Card under `securitySchemes.googleOAuth.flows.authorizationCode`).*

---

## 4. Required IAM & IAP Permissions

### Layer A: Gemini Enterprise Discovery Engine Service Agent
Service Account: `service-114740196141@gcp-sa-discoveryengine.iam.gserviceaccount.com`

```bash
# 1. Allow Gemini Enterprise to view agents in the Governance Project
gcloud projects add-iam-policy-binding deepakmichaelprod \
  --member="serviceAccount:service-114740196141@gcp-sa-discoveryengine.iam.gserviceaccount.com" \
  --role="roles/agentregistry.viewer"

# 2. Allow Gemini Enterprise to view Central Agent Gateway routes
gcloud projects add-iam-policy-binding deepakmichaelprod \
  --member="serviceAccount:service-114740196141@gcp-sa-discoveryengine.iam.gserviceaccount.com" \
  --role="roles/networkservices.viewer"

# 3. Allow Gemini Enterprise to execute Reasoning Engines in the Seller Project
gcloud projects add-iam-policy-binding deepakmichaelstage \
  --member="serviceAccount:service-114740196141@gcp-sa-discoveryengine.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

---

### Layer B: IAP Gateway Egress Authorization (`roles/iap.egressor`)

IAP evaluates the calling Gemini Enterprise **SPIFFE machine identity**:
```text
principal://agents.global.org-1015654926499.system.id.goog/resources/discoveryengine/projects/114740196141/locations/global/engines/deepak-ge-app_1787348960235/assistants/default_assistant/agents/registry/*
```

```bash
# 1. Grant Egress on the Burger Agent Service
gcloud beta iap web add-iam-policy-binding \
  --project=deepakmichaelprod \
  --region=us-central1 \
  --agent=burger-seller-agent \
  --role="roles/iap.egressor" \
  --member="principal://agents.global.org-1015654926499.system.id.goog/resources/discoveryengine/projects/114740196141/locations/global/engines/deepak-ge-app_1787348960235/assistants/default_assistant/agents/registry/*"

# 2. Grant Egress across the entire Agent Registry
gcloud beta iap web add-iam-policy-binding \
  --project=deepakmichaelprod \
  --region=us-central1 \
  --resource-type=agent-registry \
  --role="roles/iap.egressor" \
  --member="principal://agents.global.org-1015654926499.system.id.goog/resources/discoveryengine/projects/114740196141/locations/global/engines/deepak-ge-app_1787348960235/assistants/default_assistant/agents/registry/*"
```

---

## 5. Troubleshooting & Diagnostics

| Symptom / Error Code | Root Cause | Fix |
| :--- | :--- | :--- |
| **`Failed to parse agent card [object Object]`** in Chrome DevTools | Schema validation failure in the frontend (e.g. invalid MIME type `"text"` instead of `"text/plain"`, or nested `parameters` in `skills`). | Use canonical A2A fields and `text/plain` MIME types. |
| **`invalid top-level protocolVersion "1.0"`** during `gcloud agent-registry services update` | Agent Registry rejects top-level `protocolVersion: "1.0"`. | Use `protocolVersion: "0.3.0"` with `preferredTransport: "JSONRPC"`. |
| **`IAP Permission Denied (Code 7)`** in Cloud Logging | Gemini Enterprise SPIFFE identity (`resources/discoveryengine/...`) lacks `roles/iap.egressor`. | Add `roles/iap.egressor` on the agent resource or entire registry. |
| **`HTTP 404 Not Found`** from Gateway | URL in agent card points to `/reasoningEngines/{id}` directly without a sub-method. | Append `:streamQuery` or `:query` to the URL. |
| **`HTTP 401 UNAUTHENTICATED (CREDENTIALS_MISSING)`** | Agent card omitted `securitySchemes`, causing Gemini Enterprise to send requests without an `Authorization: Bearer` header. | Add `securitySchemes` to the agent card and provide the OAuth Client ID and Secret in Gemini Enterprise. |

---

## 6. Cloud Logging Audit Queries

### IAP Data Access Authorization:
```bash
gcloud logging read \
  'logName="projects/deepakmichaelprod/logs/cloudaudit.googleapis.com%2Fdata_access" \
   AND protoPayload.serviceName="iap.googleapis.com" \
   AND protoPayload.authenticationInfo.principalSubject=~"discoveryengine"' \
  --project=deepakmichaelprod \
  --limit=5 \
  --format="table(timestamp.date('%Y-%m-%d %H:%M:%S'):label=TIME, protoPayload.authenticationInfo.principalSubject:label=CALLER, protoPayload.authorizationInfo[0].granted:label=GRANTED, protoPayload.status.message:label=STATUS)"
```

### Agent Gateway Request Trajectory:
```bash
gcloud logging read \
  'logName="projects/deepakmichaelprod/logs/networkservices.googleapis.com%2Fgateway_requests" \
   AND httpRequest.requestUrl=~"aiplatform"' \
  --project=deepakmichaelprod \
  --limit=5 \
  --format="table(timestamp.date('%Y-%m-%d %H:%M:%S'):label=TIME, httpRequest.requestMethod:label=METHOD, httpRequest.status:label=HTTP_STATUS, httpRequest.requestUrl:label=URL, jsonPayload.authzPolicyInfo.result:label=IAP_AUTHZ, jsonPayload.enforcedGatewaySecurityPolicy.matchedRules[0].action:label=GW_SECURITY)"
```
