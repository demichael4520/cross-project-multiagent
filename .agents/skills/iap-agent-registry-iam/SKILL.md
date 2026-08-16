---
name: iap-agent-registry-iam
description: Comprehensive guide for discovering Agent Registry resources (endpoints, mcp-servers, agents) and managing IAP Web IAM access policies using gcloud CLI.
---

# Managing IAP Web IAM Policies for Agent Registry Resources

This skill provides guidelines and commands for discovering Google Cloud Agent Registry resources and managing Identity-Aware Proxy (IAP) Web IAM access policies (`roles/iap.egressor`).

## 1. Architecture & Resource Types
Access controls in Agent Registry are governed via IAP Web IAM Policies under `--resource-type=agent-registry`.

Agent Registry supports three distinct child resource types:
- **Endpoints (`--endpoint`)**: Governs network and routing endpoints (e.g., Vertex AI Reasoning Engine egress points).
- **MCP Servers (`--mcp-server`)**: Governs registered Model Context Protocol (MCP) server endpoints (e.g., Cloud Run MCP services).
- **Agents (`--agent`)**: Governs registered Agent definitions.

> **CRITICAL**: Use the exact matching resource flag (`--endpoint`, `--mcp-server`, or `--agent`). Passing the wrong flag (e.g. `--endpoint` for an MCP server ID) results in `NOT_FOUND: Requested entity was not found`.

## 2. Resource Discovery Commands

### Create Core Googleapis Endpoint Example
```shell
gcloud agent-registry services create core-gapi-services \
    --location=${REGION} \
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

### List Endpoints (`--endpoint`)
```shell
gcloud alpha agent-registry endpoints list \
    --project=ENDPOINT_PROJECT_ID \
    --location=REGION \
    --format="table(displayName, name.basename():label=ENDPOINT_ID, name)"
```

### List MCP Servers (`--mcp-server`)
```shell
gcloud alpha agent-registry mcp-servers list \
    --project=MCP_PROJECT_ID \
    --location=REGION \
    --format="table(displayName, name.basename():label=MCP_SERVER_ID, name)"
```

### List Agents (`--agent`)
```shell
gcloud alpha agent-registry agents list \
    --project=AGENT_RUNTIME_PROJECT_ID \
    --location=REGION \
    --format="table(displayName, name.basename():label=AGENT_ID, name)"
```

## 3. Principal Member Scopes
When binding permissions (`roles/iap.egressor`), grant access at three granularities:
1. **Single Engine Instance**:
   `principal://agents.global.org-ORG_ID.system.id.goog/resources/aiplatform/projects/RUNTIME_AGENT_PROJECT_NUMBER/locations/us-central1/reasoningEngines/ENGINE_ID`
2. **Project Scope**:
   `principalSet://agents.global.org-ORG_ID.system.id.goog/attribute.platformContainer/aiplatform/projects/RUNTIME_AGENT_PROJECT_NUMBER`
3. **Organization Scope**:
   `principalSet://agents.global.org-ORG_ID.system.id.goog/*`

## 4. Managing Policies (`gcloud beta iap web`)

### Scenario 1: Endpoints (`--endpoint`)
- **View Policy**:
  ```shell
  gcloud beta iap web get-iam-policy \
      --resource-type=agent-registry \
      --endpoint=ENDPOINT_ID \
      --region=REGION \
      --project=ENDPOINT_PROJECT_ID
  ```
- **Add Binding**:
  ```shell
  gcloud beta iap web add-iam-policy-binding \
      --resource-type=agent-registry \
      --endpoint=ENDPOINT_ID \
      --region=REGION \
      --project=AGENT_GATEWAY_PROJECT_ID \
      --role="roles/iap.egressor" \
      --member="principalSet://agents.global.org-ORG_ID.system.id.goog/attribute.platformContainer/aiplatform/projects/RUNTIME_AGENT_PROJECT_NUMBER"
  ```
- **Remove Binding**:
  ```shell
  gcloud beta iap web remove-iam-policy-binding \
      --resource-type=agent-registry \
      --endpoint=ENDPOINT_ID \
      --region=REGION \
      --project=AGENT_GATEWAY_PROJECT_ID \
      --role="roles/iap.egressor" \
      --member="principalSet://agents.global.org-ORG_ID.system.id.goog/attribute.platformContainer/aiplatform/projects/RUNTIME_AGENT_PROJECT_NUMBER"
  ```

### Scenario 2: MCP Servers (`--mcp-server`)
- **View Policy**:
  ```shell
  gcloud beta iap web get-iam-policy \
      --resource-type=agent-registry \
      --mcp-server=MCP_ENDPOINT_ID \
      --region=REGION \
      --project=MCP_PROJECT_ID
  ```
- **Add Binding (Org-wide)**:
  ```shell
  gcloud beta iap web add-iam-policy-binding \
      --resource-type=agent-registry \
      --mcp-server=MCP_ENDPOINT_ID \
      --region=REGION \
      --project=AGENT_GATEWAY_PROJECT_ID \
      --role="roles/iap.egressor" \
      --member="principalSet://agents.global.org-ORG_ID.system.id.goog/*"
  ```
- **Remove Binding**:
  ```shell
  gcloud beta iap web remove-iam-policy-binding \
      --resource-type=agent-registry \
      --mcp-server=MCP_ENDPOINT_ID \
      --region=REGION \
      --project=AGENT_GATEWAY_PROJECT_ID \
      --role="roles/iap.egressor" \
      --member="principalSet://agents.global.org-ORG_ID.system.id.goog/*"
  ```

### Scenario 3: Agents (`--agent`)
- **View Policy**:
  ```shell
  gcloud beta iap web get-iam-policy \
      --resource-type=agent-registry \
      --agent=AGENT_ENDPOINT_ID \
      --region=REGION \
      --project=AGENT_GATEWAY_PROJECT_ID
  ```
- **Add Binding (Project Scope)**:
  ```shell
  gcloud beta iap web add-iam-policy-binding \
      --resource-type=agent-registry \
      --agent=AGENT_ENDPOINT_ID \
      --region=REGION \
      --project=AGENT_GATEWAY_PROJECT_ID \
      --role="roles/iap.egressor" \
      --member="principalSet://agents.global.org-ORG_ID.system.id.goog/resources/aiplatform/projects/RUNTIME_AGENT_PROJECT_NUMBER"
  ```
- **Remove Binding**:
  ```shell
  gcloud beta iap web remove-iam-policy-binding \
      --resource-type=agent-registry \
      --agent=AGENT_ENDPOINT_ID \
      --region=REGION \
      --project=AGENT_GATEWAY_PROJECT_ID \
      --role="roles/iap.egressor" \
      --member="principalSet://agents.global.org-ORG_ID.system.id.goog/resources/aiplatform/projects/RUNTIME_AGENT_PROJECT_NUMBER"
  ```

## 5. Troubleshooting Common Errors
1. **`NOT_FOUND: Requested entity was not found`**:
   - **Root Cause**: You passed `--endpoint` for an MCP Server resource ID or `--mcp-server` for an Endpoint resource ID.
   - **Resolution**: Check the full resource path from `list` output:
     - If path contains `/mcpServers/`, use `--mcp-server`.
     - If path contains `/endpoints/`, use `--endpoint`.
     - If path contains `/agents/`, use `--agent`.
2. **`PERMISSION_DENIED`**:
   - **Root Cause**: The caller lacks `iap.web.setIamPolicy` or `resourcemanager.projects.setIamPolicy` on project `AGENT_GATEWAY_PROJECT_ID`.
   - **Resolution**: Ensure active account has `roles/iap.admin` or `roles/owner` on `AGENT_GATEWAY_PROJECT_ID`.
