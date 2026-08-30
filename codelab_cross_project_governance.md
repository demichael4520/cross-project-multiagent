---
id: agw-cuj-arun-manual-multiproject
authors: Deepak Michael, Michael Larson
description: Implement manual cross-project centralized governance and dynamic Agent Registry autodiscovery with Agent Gateway, Agent Registry, and Agent Identity in Gemini Enterprise Agent Platform.
feedback_link: https://github.com/googlecodelabs/feedback/issues/new?title=[agw-cuj-arun-manual-multiproject]
project: /devsite/_project.yaml
book: /devsite/_book.yaml
keywords: docType:Codelab,product:AgentPlatform,product:AgentRegistry,api:NetworkServicesApi
---
{# disableFinding(HEADING_NO_ID_H2) #}
{# disableFinding(HEADING_NO_ID_H3) #}
{# disableFinding("authz") #}

## Introduction
Duration: 05:00

As enterprise organizations adopt generative AI, architectures are rapidly
evolving from standalone, monolithic chatbots into **distributed multi-agent
systems (Agent-to-Agent / A2A)**. In these modern topologies, high-level
orchestrator agents coordinate complex business workflows by delegating tasks
to specialized domain worker agents, Model Context Protocol (MCP) tool servers,
and backend enterprise databases across independent Google Cloud projects.

However, operating multi-agent systems at scale introduces critical security,
governance, and operational challenges:
- **Shadow Agent & Tool Sprawl:** When development teams deploy agents in
  isolated projects without a centralized catalog, organizations lose
  visibility into which tools and subagents exist.
- **Unmonitored Cross-Project Egress:** Allowing agents direct, uninspected
  network routes creates data exfiltration risks and bypasses security
  perimeters.
- **Fragile Hardcoded Integrations:** Hardcoding downstream agent URLs and
  Reasoning Engine IDs creates brittle dependencies that break during upgrades
  or redeployments.
- **Lack of Least-Privilege Identity:** Shared service accounts fail to provide
  cryptographic non-repudiation at the individual agent instance level.

To solve these challenges, the **[Gemini Enterprise Agent Platform][01-01]**
provides a unified governance and connectivity control plane composed of four
core pillars:

1. **[Agent Gateway (`networkservices.googleapis.com`)][01-02]:**
   A managed, regional network and policy enforcement proxy. Operating in
   `AGENT_TO_ANYWHERE` egress mode, it intercepts outbound agent traffic,
   delegates authorization evaluations to security extensions, and routes
   requests across project perimeters.
2. **[Agent Registry (`agentregistry.googleapis.com`)][01-03]:**
   The single enterprise service catalog. It provides a centralized, vetted
   directory of all available tools, MCP servers, and peer agents across the
   organization, enabling dynamic runtime autodiscovery with zero hardcoded endpoints.
3. **[Agent Identity & IAP Governance (`iap.googleapis.com`)][01-04]:**
   A cryptographic identity framework that issues unique, container-level
   SPIFFE URNs (`principal://...`) to executing agents. Identity-Aware Proxy
   (IAP) evaluates fine-grained IAM policies (`roles/iap.egressor`) before
   traffic is permitted to leave the gateway.
4. **[Vertex AI Agent Runtime (Reasoning Engines)][01-09]:**
   A fully managed, serverless execution platform for Python-based agentic
   applications, featuring native configuration bindings (`agent_gateway_config`)
   to central gateways.

### The Codelab Business Scenario: Multi-Project Food & Beverage Purchasing
In this codelab, you will build and govern a real-world multi-project purchasing
ecosystem spanning three distinct Google Cloud projects:

- **Central Governance Project (`PROJECT_GOVERNANCE`):** Owned by Central IT and
  SecOps, hosting the Central Agent Gateway, Central Agent Registry, and IAP
  authorization policies.
- **Consumer Orchestrator Project (`PROJECT_CONCIERGE`):** Owned by the
  procurement team, hosting the *Purchasing Concierge Agent* which dynamically
  discovers vendors and routes customer orders.
- **Domain Vendor Project (`PROJECT_SELLERS`):** Owned by external or departmental
  vendors, hosting the *Burger Seller Agent* and *Pizza Seller Agent*.

> aside positive
> **Architecture Best Practice Note:** In production enterprise deployments,
> using a Shared VPC with [Private Service Connect (PSC) network
> attachments][01-05] is the recommended method for Agent Centralization to
> enforce private network boundary isolation. However, the primary goal of this
> codelab is to demonstrate cross-project governance, Identity-Aware Proxy (IAP)
> access control policies, and dynamic Agent Registry auto-discovery without
> networking dependencies.

![figure1](img/figure1.svg)

*Fig 1. Multi-project centralized governance architecture*

### Why Cross-Project Centralized Governance?
In large enterprise organizations, product teams and data science groups build
AI agents across dozens of independent Google Cloud projects. Giving each team
direct control over tool registration, egress network routes, and security
guardrails creates unvetted tool sprawl, inconsistent DLP policies, unmonitored
VPC egress, and fragmented audit logs.

**Cross-project centralized governance** separates policy authoring from agent
execution:
- **Central IT & SecOps** author security policies, vet tools, and monitor egress
  within a single **Centralized Governance Project**.
- **Product & Application Teams** focus purely on business logic in their
  independent **Agent Runtime Projects**, binding directly to the central
  gateway without the operational overhead of managing local VPCs,
  interconnects, or fragmented policy engines.

### Three-Tier Project Architecture & Boundaries

![Three-Tier Cross-Project Governance Architecture](img/three_tier_cross_project_governance.jpg)

*Fig 2. Three-tier cross-project governance architecture and boundaries*

### Two-Tier Identity Scoping Model
When agents communicate through the Central Agent Gateway, Identity-Aware Proxy
(IAP) authorization policies evaluate access based on the caller's **Agent
Identity**—a cryptographically attested, SPIFFE-based identity issued
automatically to the runtime container:

- **Tier 1: Baseline Google Cloud APIs (Coarse-Grained via `principalSet://`):**
  Project-wide access allowing all agent runtimes in a spoke project to reach
  standard Google APIs (`aiplatform`, `iamcredentials`, `telemetry`,
  `agentregistry`) for discovery, token generation, and inference.

  > aside negative
  > **CRITICAL MULTI-PROJECT REQUIREMENT:** **All 3 projects** (`PROJECT_GOVERNANCE`,
  > `PROJECT_CONCIERGE`, and `PROJECT_SELLERS`) must have their project-level
  > `principalSet://` explicitly granted `roles/iap.egressor` on the central
  > `core-gapi-services` endpoint. If any project's `principalSet` is omitted,
  > agents executing in or routing through that project will fail during
  > container startup, token minting, or telemetry streaming with an immediate
  > `HTTP 403 Forbidden` from the Central Agent Gateway.

- **Tier 2: Business Tools & A2A Services (Fine-Grained via `principal://`):**
  Strict least-privilege access bound to individual Reasoning Engine instances,
  optionally enforced with Common Expression Language (CEL) conditions (for
  example, permitting read-only operations while denying mutations).

### What you build
- Centralized Agent Gateway (`centralized-agw`) in `PROJECT_GOVERNANCE`
- IAP Authorization Service Extension and Authz Policy in `DRY_RUN` mode
- Cross-project service agent IAM permissions (`ar_agw_cross_project_sa`)
- Shared central Google Cloud Storage (GCS) staging bucket
- Isolated Burger and Pizza Seller Agents in `PROJECT_SELLERS`
- Purchasing Concierge Agent with dynamic REST autodiscovery in `PROJECT_CONCIERGE`
- Service registrations in Central Agent Registry with cross-project mTLS URLs
- Dynamic IAP Egress access policies with live verification and Cloud Logging audits

![figure2](img/figure2.svg)

*Fig 2. Step-by-step implementation sequence*

### What you learn
- How to configure cross-project service agent IAM permissions for centralized gateways
- How to route Vertex AI Agent Runtime egress through a central Agent Gateway across multi-project environments
- How to use SPIFFE-based Agent Identity for fine-grained governance
- How to register cross-project agent endpoints in Agent Registry
- How to configure and dynamically update IAP Egress policies on Agent Registry resources
- How to audit granted and denied policy verdicts in Cloud Logging

### What you need
- Three Google Cloud projects with billing enabled:
  - `PROJECT_GOVERNANCE`: Hosts the Central Agent Gateway and Agent Registry.
  - `PROJECT_CONCIERGE`: Hosts the Purchasing Concierge orchestrator agent.
  - `PROJECT_SELLERS`: Hosts the Burger and Pizza seller worker agents.
- IAM permissions across all three projects:
  - `roles/owner` or `roles/resourcemanager.organizationAdmin`
  - `roles/iam.securityAdmin`
- A POSIX-compatible shell (`bash` or `zsh`) with Google Cloud CLI (`gcloud`) installed
- Command-line tools: `git`, `curl`, `jq`, Python 3.10+, and [`uv`][01-08]

This concludes the concepts portion... next on to the *Setup & Environment* section.

[01-01]: https://docs.cloud.google.com/gemini-enterprise-agent-platform/agents#platform_architecture
[01-02]: https://docs.cloud.google.com/gemini-enterprise-agent-platform/govern/gateways/agent-gateway-overview
[01-03]: https://docs.cloud.google.com/agent-registry/overview
[01-04]: https://docs.cloud.google.com/gemini-enterprise-agent-platform/govern/agent-identity-overview
[01-05]: https://docs.cloud.google.com/vpc/docs/about-private-service-connect-interfaces
[01-06]: https://github.com/demichael4520/cross-project-multiagent
[01-07]: https://docs.cloud.google.com/gemini-enterprise-agent-platform/govern/policies/assign-identity-iam
[01-08]: https://docs.astral.sh/uv/getting-started/installation/
[01-09]: https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/overview
[01-10]: https://cloud.google.com/network-security/docs/authz-policies

---

## Setup & Environment
Duration: 10:00

### Architecture & Single-Terminal Deployment Workflow
Although this architecture spans 3 distinct Google Cloud projects, you can
execute 100% of the terminal deployment commands, repository downloads, and
staging operations from a single Cloud Shell terminal set to
`PROJECT_GOVERNANCE`. Every deployment script and `gcloud` command explicitly
targets the appropriate destination project via CLI flags (`--project`).

Start by accessing your Google Cloud project command line:
- Cloud Shell at [`shell.cloud.google.com`][02-01], or
- A local terminal with `gcloud` CLI [installed][02-02]

#### Set your project context

```bash
# set terminal project context to Central Governance Project
gcloud config set project SET_YOUR_GOVERNANCE_PROJECT_ID_HERE
```

```bash
# login to gcloud cli
gcloud auth login
```

```bash
# login for application default credentials
gcloud auth application-default login
```

#### Set shell environment variables

```bash
# 1. Project Identifiers
export PROJECT_GOVERNANCE="SET_YOUR_GOVERNANCE_PROJECT_ID_HERE"
export PROJECT_CONCIERGE="SET_YOUR_CONCIERGE_PROJECT_ID_HERE"
export PROJECT_SELLERS="SET_YOUR_SELLERS_PROJECT_ID_HERE"

# 2. Regional & Gateway Settings
export REGION="us-central1"
export AGW_NAME="centralized-agw"

# 3. Retrieve Project Numbers
export PROJECT_NUMBER_GOVERNANCE=$(gcloud projects describe ${PROJECT_GOVERNANCE} --format="value(projectNumber)")
export PROJECT_NUMBER_CONCIERGE=$(gcloud projects describe ${PROJECT_CONCIERGE} --format="value(projectNumber)")
export PROJECT_NUMBER_SELLERS=$(gcloud projects describe ${PROJECT_SELLERS} --format="value(projectNumber)")

# 4. Obtain Organization ID
export ORG_ID=$(gcloud projects get-ancestors ${PROJECT_GOVERNANCE} --format="value(id, type)" | grep organization | awk '{print $1}')

# 5. Set Application Default Credentials (ADC) Quota Project
gcloud auth application-default set-quota-project ${PROJECT_GOVERNANCE}

echo "Governance Project: ${PROJECT_GOVERNANCE} (${PROJECT_NUMBER_GOVERNANCE})"
echo "Concierge Project:  ${PROJECT_CONCIERGE} (${PROJECT_NUMBER_CONCIERGE})"
echo "Sellers Project:    ${PROJECT_SELLERS} (${PROJECT_NUMBER_SELLERS})"
echo "Organization ID:    ${ORG_ID}"
```

#### Enable required Google Cloud APIs

```bash
# enable google apis (agent platform bundle, part 1)
for PROJ in ${PROJECT_GOVERNANCE} ${PROJECT_CONCIERGE} ${PROJECT_SELLERS}; do
  gcloud services enable \
    agentregistry.googleapis.com \
    aiplatform.googleapis.com \
    apphub.googleapis.com \
    apptopology.googleapis.com \
    cloudapiregistry.googleapis.com \
    cloudtrace.googleapis.com \
    compute.googleapis.com \
    dataform.googleapis.com \
    iam.googleapis.com \
    iamconnectors.googleapis.com \
    iap.googleapis.com \
    logging.googleapis.com \
    modelarmor.googleapis.com \
    monitoring.googleapis.com \
    networksecurity.googleapis.com \
    networkservices.googleapis.com \
    notebooks.googleapis.com \
    observability.googleapis.com \
    --project=${PROJ}
done
```

```bash
# enable google apis (agent platform bundle, part 2)
for PROJ in ${PROJECT_GOVERNANCE} ${PROJECT_CONCIERGE} ${PROJECT_SELLERS}; do
  gcloud services enable \
    securitycenter.googleapis.com \
    saasservicemgmt.googleapis.com \
    storage.googleapis.com \
    telemetry.googleapis.com \
    texttospeech.googleapis.com \
    --project=${PROJ}
done
```

```bash
# enable google apis (foundational & agent runtime build bundle, part 3)
for PROJ in ${PROJECT_GOVERNANCE} ${PROJECT_CONCIERGE} ${PROJECT_SELLERS}; do
  gcloud services enable \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    cloudresourcemanager.googleapis.com \
    iamcredentials.googleapis.com \
    serviceusage.googleapis.com \
    run.googleapis.com \
    --project=${PROJ}
done
```

#### Update `gcloud` CLI (recommended)

```bash
# update gcloud components
gcloud components update --quiet
```

> aside negative
> **NOTE:** Some features use `gcloud beta` or `gcloud alpha` commands. If not
> installed, run `gcloud components install beta alpha` to enable.

This concludes the setup portion... next on to the *Register Core Google APIs* section.

[02-01]: https://shell.cloud.google.com/
[02-02]: https://cloud.google.com/sdk/gcloud#download_and_install_the

---

## Register Core Google APIs Endpoint Service
Duration: 10:00

Agent Gateway requires Google API URLs to be registered in the Central Agent
Registry so that agents configured with `agent_gateway_config` can route egress
traffic securely to core Google Cloud backend services (such as `aiplatform`,
IAM Credentials, and Telemetry).

### Create `core-gapi-services` in Agent Registry

```bash
# register core google api endpoints in agent registry
gcloud agent-registry services create core-gapi-services \
  --project=${PROJECT_GOVERNANCE} \
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

### Understanding `principalSet` vs `principal` in Agent Identity

In Google Cloud IAM and the [Gemini Enterprise Agent Platform][03-01], machine identities issued to executing agent containers use **cryptographically attested SPIFFE URNs** evaluated by Identity-Aware Proxy (IAP). When configuring IAM policies with `roles/iap.egressor`, you can target either a specific single **`principal`** or an attribute-based **`principalSet`**:

| Dimension | `principal://` (Single Machine Identity) | `principalSet://` (Attribute-Based Group) |
| :--- | :--- | :--- |
| **IAM Syntax** | `principal://...` | `principalSet://...` |
| **Granularity** | **Fine-Grained (Instance-level):** Identifies a single, specific Reasoning Engine container instance. | **Coarse-Grained (Project-level):** Identifies all reasoning engines sharing a common project attribute. |
| **URN Pattern** | `principal://agents.global.org-${ORG_ID}.system.id.goog/attribute.platformContainer/aiplatform/projects/${PROJECT_NUMBER}/locations/${REGION}/reasoningEngines/${ENGINE_ID}` | `principalSet://agents.global.org-${ORG_ID}.system.id.goog/attribute.platformContainer/aiplatform/projects/${PROJECT_NUMBER}` |
| **Use Case in Agent Platform** | **Tier 2 (Business Tools & A2A):** Authorizing specific orchestrator agents to invoke target domain tools (e.g., Purchasing Concierge $\rightarrow$ Burger Seller). | **Tier 1 (Foundational Infrastructure):** Granting all agents in a project egress access to Google Cloud APIs (`core-gapi-services`). |
| **Lifecycle Impact** | If an agent is deleted and recreated, its new Engine ID requires an updated IAM policy binding. | Automatically applies to newly deployed agents in that project without additional IAM updates. |

#### Why use `principalSet` for Core Google APIs?
Every Vertex AI Reasoning Engine instance—regardless of its business logic or domain—requires outbound access through the Central Agent Gateway to reach foundational Google Cloud endpoints (such as `aiplatform.googleapis.com` for LLM inference, `iamcredentials.googleapis.com` for OAuth token generation, and `agentregistry.googleapis.com` for dynamic autodiscovery).

Using `principalSet://` allows Central IT and SecOps to authorize an entire project's agent workload with a single policy binding, ensuring that any current or future agent deployed in that project can reach essential Google Cloud control planes out-of-the-box.

For deeper technical details on principal identifiers and workload identity mechanics, see:
- [Google Cloud IAM: Principal Identifiers & Principal Sets][03-02]
- [Vertex AI Agent Identity & SPIFFE Attestation Overview][03-03]
- [Configuring IAP Egress Authorization for Agent Gateway][03-04]

### Grant Egress Access for Core Google APIs Endpoint
To enable agents across **all 3 projects** (`PROJECT_GOVERNANCE`,
`PROJECT_CONCIERGE`, and `PROJECT_SELLERS`) to communicate with Core Google APIs
via the Central Agent Gateway, assign the `roles/iap.egressor` role on
`core-gapi-services` for each project's `principalSet`:

> aside negative
> **COMMON MULTI-PROJECT PITFALL:** A common failure occurs when
> `core-gapi-services` is authorized only for the orchestrator project
> (`PROJECT_CONCIERGE`). When worker agents in `PROJECT_SELLERS` or governance
> agents in `PROJECT_GOVERNANCE` initialize, their outbound calls to `aiplatform`
> or `iamcredentials` fail with `HTTP 403 Permission Denied`. Always ensure
> **all 3 projects'** `principalSet`s are bound.

```bash
# 1. get the underlying Agent Registry endpoint ID
ENDPOINT_ID=$(gcloud alpha agent-registry services describe core-gapi-services \
  --project=${PROJECT_GOVERNANCE} \
  --location=${REGION} \
  --format="value(registryResource)" | awk -F'/' '{print $NF}')
echo "Core APIs Endpoint ID: ${ENDPOINT_ID}"
```

```bash
# 2. grant IAP Egress to Governance Project principalSet
gcloud beta iap web add-iam-policy-binding \
  --resource-type=agent-registry \
  --endpoint=${ENDPOINT_ID} \
  --region=${REGION} \
  --project=${PROJECT_GOVERNANCE} \
  --role="roles/iap.egressor" \
  --member="principalSet://agents.global.org-${ORG_ID}.system.id.goog/attribute.platformContainer/aiplatform/projects/${PROJECT_NUMBER_GOVERNANCE}" \
  --quiet
```

```bash
# 3. grant IAP Egress to Concierge Project principalSet
gcloud beta iap web add-iam-policy-binding \
  --resource-type=agent-registry \
  --endpoint=${ENDPOINT_ID} \
  --region=${REGION} \
  --project=${PROJECT_GOVERNANCE} \
  --role="roles/iap.egressor" \
  --member="principalSet://agents.global.org-${ORG_ID}.system.id.goog/attribute.platformContainer/aiplatform/projects/${PROJECT_NUMBER_CONCIERGE}" \
  --quiet
```

```bash
# 4. grant IAP Egress to Sellers Project principalSet
gcloud beta iap web add-iam-policy-binding \
  --resource-type=agent-registry \
  --endpoint=${ENDPOINT_ID} \
  --region=${REGION} \
  --project=${PROJECT_GOVERNANCE} \
  --role="roles/iap.egressor" \
  --member="principalSet://agents.global.org-${ORG_ID}.system.id.goog/attribute.platformContainer/aiplatform/projects/${PROJECT_NUMBER_SELLERS}" \
  --quiet
```

### Validate Core Google APIs IAM Policy

Validate that all 3 project `principalSet`s are bound to `roles/iap.egressor` on the `core-gapi-services` endpoint:

```bash
# 5. validate IAP IAM policy on Core APIs endpoint
gcloud beta iap web get-iam-policy \
  --resource-type=agent-registry \
  --endpoint=${ENDPOINT_ID} \
  --region=${REGION} \
  --project=${PROJECT_GOVERNANCE}
```

#### Sample Output:

```yaml
bindings:
- members:
  - principalSet://agents.global.org-123456789012.system.id.goog/attribute.platformContainer/aiplatform/projects/112233445566
  - principalSet://agents.global.org-123456789012.system.id.goog/attribute.platformContainer/aiplatform/projects/998877665544
  - principalSet://agents.global.org-123456789012.system.id.goog/attribute.platformContainer/aiplatform/projects/987654321098
  role: roles/iap.egressor
etag: BwZaNIkxFhI=
version: 1
```

This concludes the Core APIs registration... next on to the *Deploy Centralized Agent Gateway* section.

[03-01]: https://docs.cloud.google.com/gemini-enterprise-agent-platform/govern/agent-identity-overview
[03-02]: https://cloud.google.com/iam/docs/principal-identifiers
[03-03]: https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/agent-identity
[03-04]: https://cloud.google.com/service-extensions/docs/configure-authz-iap

---

## Deploy Centralized Agent Gateway
Duration: 10:00

Deploy the centralized Agent Gateway (`centralized-agw`) in
`AGENT_TO_ANYWHERE` egress mode inside the `$PROJECT_GOVERNANCE` project.

### Create local directory for config files

```bash
# create config folder
mkdir -p cfg
```

### Define Gateway Configuration Manifest
Create `cfg/${AGW_NAME}.yaml` for egress traffic governance with custom IAP
authorization enabled:

```bash
# generate agent gateway config yaml
cat > cfg/${AGW_NAME}.yaml << EOF
name: ${AGW_NAME}
protocols:
  - MCP
googleManaged:
  governedAccessPath: AGENT_TO_ANYWHERE
registries:
  - "//agentregistry.googleapis.com/projects/${PROJECT_GOVERNANCE}/locations/${REGION}"
EOF
```

### Import Agent Gateway Configuration

```bash
# import and create agent gateway
gcloud network-services agent-gateways import ${AGW_NAME} \
  --source="cfg/${AGW_NAME}.yaml" \
  --location=${REGION} \
  --project=${PROJECT_GOVERNANCE}
```

### Verify Agent Gateway Details

```bash
# show agent gateway status
gcloud network-services agent-gateways describe ${AGW_NAME} \
  --location=${REGION} \
  --project=${PROJECT_GOVERNANCE}
```

#### Sample Output:

```yaml
agentGatewayCard:
  mtlsEndpoint: projects/m0ecc0ce3d34b8b76p-tp/regions/us-central1/serviceAttachments/unitkind1-swp-mtls-psc-sa
  rootCertificates:
  - |
    -----BEGIN CERTIFICATE-----
    MIIDwzCCAqugAwIBAgITNQuWGopdOZaHdcK7r7AYFhonqDANBgkqhkiG9w0BAQsF
    ADBfMSUwIwYDVQQKExxHb29nbGUgQ2xvdWQgTWFuYWdlZCBTZXJ2aWNlMTYwNAYD
    VQQDEy1BZ2VudCBHYXRld2F5IFRMUyBJbnNwZWN0aW9uIENBICh1cy1jZW50cmFs
    MSkwHhcNMjYwODI4MDUxNDM0WhcNMzYwODI1MDUxNDMzWjBfMSUwIwYDVQQKExxH
    ...
    -----END CERTIFICATE-----
  serviceExtensionsServiceAccount: service-123456789012@gcp-sa-dep.iam.gserviceaccount.com
createTime: '2026-08-29T19:31:25.728711850Z'
googleManaged:
  governedAccessPath: AGENT_TO_ANYWHERE
name: projects/my-governance-project/locations/us-central1/agentGateways/centralized-agw
protocols:
- MCP
registries:
- //agentregistry.googleapis.com/projects/my-governance-project/locations/us-central1
updateTime: '2026-08-29T19:33:11.739408083Z'
```

This concludes the gateway deployment... next on to the *Configure Authorization* section.

---

## Configure Agent Gateway Authorization
Duration: 10:00

The Agent Gateway authorization extension for Identity-Aware Proxy (IAP) is a
type of [Service Extension][04-01] used to delegate authorization decisions for
all Agent Platform communications:

1. **Delegation Flow:** When an agent invokes an external endpoint or subagent,
   it routes the request to Agent Gateway. The gateway uses the authorization
   extension to send a callout to the IAP evaluation service. IAP evaluates the
   caller's SPIFFE machine identity against the IAM policy of the target resource
   in Agent Registry.
2. **Enforcement Modes:** In `DRY_RUN` mode, IAP evaluates requests and logs
   decisions in Cloud Logging without blocking traffic. In `ENFORCE` mode, any
   request from an unauthorized agent is immediately blocked with HTTP 403.
3. **Binding Layer:** The authorization extension is attached to Agent Gateway
   using an authorization policy configured with the `REQUEST_AUTHZ` profile.

### Create Authorization Extension

```bash
# create authz extension config file in dry run mode
cat > cfg/${AGW_NAME}-svc-ext-authz-iap-dryrun.yaml << EOF
name: ${AGW_NAME}-svc-ext-authz-iap-dryrun
service: iap.googleapis.com
failOpen: true
timeout: 1s
metadata:
  iamEnforcementMode: "DRY_RUN"
  iapPolicyVersion: "V1"
EOF
```

```bash
# import authz extension
gcloud service-extensions authz-extensions import ${AGW_NAME}-svc-ext-authz-iap-dryrun \
  --source=cfg/${AGW_NAME}-svc-ext-authz-iap-dryrun.yaml \
  --location=${REGION} \
  --project=${PROJECT_GOVERNANCE}
```

```bash
# verify authz extension state
gcloud service-extensions authz-extensions describe ${AGW_NAME}-svc-ext-authz-iap-dryrun \
  --location=${REGION} \
  --project=${PROJECT_GOVERNANCE}
```

### Understanding the Purpose of the Custom Authorization Policy

In Google Cloud Network Security, an **Authorization Policy (`authz-policies`)** serves as the **enforcement binding** between the Agent Gateway data plane and the Identity-Aware Proxy (IAP) evaluation service.

While the **[Authz Extension][04-02]** defines *how* authorization decisions are evaluated (via `iap.googleapis.com` in `DRY_RUN` or `ENFORCE` mode), the **Authz Policy** defines *where* and *when* that evaluation occurs.

#### Key Manifest Fields Explained:

| Manifest Field | Configured Value | Purpose & Operational Impact |
| :--- | :--- | :--- |
| `target.resources` | `projects/.../agentGateways/${AGW_NAME}` | Attaches the security policy directly to the Central Agent Gateway instance. |
| `policyProfile` | `REQUEST_AUTHZ` | Instructs the gateway to execute an authorization callout for **every outbound HTTP/RPC request** initiated by an agent container before allowing egress. |
| `action` | `CUSTOM` | Delegates access decisions to an external security provider rather than evaluating static IP/CIDR rules. |
| `customProvider.authzExtension.resources` | `projects/.../authzExtensions/${AGW_NAME}-svc-ext-authz-iap-dryrun` | Binds the policy to the specific IAP Authz Extension created in the preceding step. |

#### The 3-Way Policy Enforcement Handshake:

```
[Agent Runtime Container Egress]
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. Agent Gateway (networkservices.googleapis.com)           │
│    • Intercepts outbound RPC / HTTP call                    │
└──────────────────────────────┬──────────────────────────────┘
                               │ Governed by
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Authz Policy (networksecurity.googleapis.com)            │
│    • Profile: REQUEST_AUTHZ, Action: CUSTOM                 │
└──────────────────────────────┬──────────────────────────────┘
                               │ Dispatches callout to
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Authz Extension & IAP (service-extensions & IAP)         │
│    • Evaluates caller SPIFFE URN vs target IAM policy       │
│    • Returns ALLOW / DENY verdict                           │
└─────────────────────────────────────────────────────────────┘
```

### Create Authorization Policy

```bash
# create authz policy manifest
cat > cfg/${AGW_NAME}-authz-policy-profile-iap.yaml << EOF
name: ${AGW_NAME}-authz-policy-profile-iap
target:
  resources:
    - "projects/${PROJECT_GOVERNANCE}/locations/${REGION}/agentGateways/${AGW_NAME}"
policyProfile: REQUEST_AUTHZ
action: CUSTOM
customProvider:
  authzExtension:
    resources:
      - "projects/${PROJECT_GOVERNANCE}/locations/${REGION}/authzExtensions/${AGW_NAME}-svc-ext-authz-iap-dryrun"
EOF
```

```bash
# import and enable authz policy
gcloud beta network-security authz-policies import ${AGW_NAME}-authz-policy-profile-iap \
  --source=cfg/${AGW_NAME}-authz-policy-profile-iap.yaml \
  --location=${REGION} \
  --project=${PROJECT_GOVERNANCE}
```

```bash
# show authz policy details
gcloud beta network-security authz-policies describe ${AGW_NAME}-authz-policy-profile-iap \
  --location=${REGION} \
  --project=${PROJECT_GOVERNANCE}
```

#### Sample Output:

```yaml
action: CUSTOM
createTime: '2026-08-29T19:37:00.000000000Z'
customProvider:
  authzExtension:
    resources:
    - projects/my-governance-project/locations/us-central1/authzExtensions/centralized-agw-svc-ext-authz-iap-dryrun
name: projects/my-governance-project/locations/us-central1/authzPolicies/centralized-agw-authz-policy-profile-iap
policyProfile: REQUEST_AUTHZ
target:
  resources:
  - projects/my-governance-project/locations/us-central1/agentGateways/centralized-agw
updateTime: '2026-08-29T19:37:00.000000000Z'
```

This concludes the authorization setup... next on to the *Cross-Project IAM Permissions* section.

[04-01]: https://docs.cloud.google.com/service-extensions/docs/overview
[04-02]: https://cloud.google.com/service-extensions/docs/configure-authz-iap
[04-03]: https://cloud.google.com/network-security/docs/authz-policies
[04-04]: https://cloud.google.com/iap/docs

---

## Configure Cross-Project IAM Permissions
Duration: 05:00

In Google Cloud, each project acts as an isolated security perimeter. When you
deploy an **Agent Runtime** in a spoke project (`PROJECT_CONCIERGE` or
`PROJECT_SELLERS`) and configure its `agent_gateway_config` to point to a
gateway in `PROJECT_GOVERNANCE`, the deployment is provisioned by the spoke
project's **Agent Runtime Service Agent** (`service-<PROJECT_NUMBER>@gcp-sa-aiplatform.iam.gserviceaccount.com`).

By default, this service agent has **zero permissions** in `PROJECT_GOVERNANCE`.
Without explicit cross-project IAM delegation, Agent Runtime cannot resolve,
validate, or attach to the central gateway during agent container creation,
resulting in immediate deployment errors.

### Understanding Control Plane vs. Data Plane Identity

To master cross-project agent governance, it is essential to distinguish between
the two different identities at play:

1. **Control Plane (Service Agent Identity):**
   * **Who:** The Google-managed service account (`service-<PROJECT_NUMBER>@gcp-sa-aiplatform.iam.gserviceaccount.com`).
   * **When:** During **deployment and container initialization**.
   * **Role:** Needs permissions in `PROJECT_GOVERNANCE` to discover the gateway,
     validate its state, and attach the runtime's outbound networking route.
   * **Required Permissions:** `roles/networkservices.viewer` and the custom role
     `ar_agw_cross_project_sa`.

2. **Data Plane (Agent SPIFFE Identity):**
   * **Who:** The container's cryptographic SPIFFE identity (`principal://...` or `principalSet://...`).
   * **When:** During **live query and tool execution**.
   * **Role:** Evaluated by Identity-Aware Proxy (IAP) on the Agent Gateway to
     determine whether the agent is authorized to call `core-gapi-services` or
     downstream peer agents.

### Why We Use a Custom Role (`ar_agw_cross_project_sa`)

Following enterprise least-privilege security principles, we create a dedicated
custom role in `PROJECT_GOVERNANCE` with only the exact permissions needed for
gateway attachment:

* `networkservices.agentGateways.get`: Validates the existence and configuration of the central gateway.
* `networkservices.agentGateways.use`: Authorizes the runtime container to route outbound traffic through the gateway.
* `networkservices.operations.get`: Polls asynchronous network binding and attachment operations during provisioning.

### Cross-Project IAM Requirements Matrix

To enable cross-project Agent-to-Agent (A2A) communication, dynamic service discovery, and central gateway egress routing, specific IAM roles must be granted across the 3 projects:

| Target Project | Member / Identity | Role | Purpose & Permissions |
| :--- | :--- | :--- | :--- |
| **`PROJECT_GOVERNANCE`** | `service-${PROJECT_NUMBER_CONCIERGE}@gcp-sa-aiplatform...`<br/>`service-${PROJECT_NUMBER_SELLERS}@gcp-sa-aiplatform...` | `projects/${PROJECT_GOVERNANCE}/roles/ar_agw_cross_project_sa` | **Custom Gateway Attachment Role:** Grants `networkservices.agentGateways.get`, `networkservices.agentGateways.use`, and `networkservices.operations.get` to resolve and attach to the central gateway. |
| **`PROJECT_GOVERNANCE`** | `service-${PROJECT_NUMBER_CONCIERGE}@gcp-sa-aiplatform...`<br/>`service-${PROJECT_NUMBER_SELLERS}@gcp-sa-aiplatform...` | `roles/networkservices.viewer` | **Network Services Viewer:** Enables reading gateway topology and network configurations. |
| **`PROJECT_GOVERNANCE`** | Concierge Service Accounts & SAs (`gcp-sa-aiplatform`, `gcp-sa-aiplatform-re`, Compute SA) | `roles/viewer` | **Project Metadata Viewer:** Allows cross-project metadata lookup and project ID to project number resolution. |
| **`PROJECT_GOVERNANCE`** | Concierge & Sellers Service Agents, Compute SAs, and Workload `principalSet://` | `roles/agentregistry.viewer` | **Central Service Autodiscovery:** Allows runtime agent containers and service accounts to list and describe registered services (`agentregistry.services.list`, `agentregistry.services.get`). |
| **`PROJECT_SELLERS`** | Concierge Service Agents, Compute SA, and Workload `principalSet://` | `roles/aiplatform.user` | **Cross-Project Agent Invocation:** Authorizes the Concierge agent to invoke target Reasoning Engine instances (`aiplatform.reasoningEngines.query`) in `PROJECT_SELLERS`. |
| **`PROJECT_GOVERNANCE`** (Agent Registry IAP) | `principalSet://agents.global.org-${ORG_ID}.system.id.goog/attribute.platformContainer/aiplatform/projects/${PROJECT_NUMBER_*}` | `roles/iap.egressor` on `core-gapi-services` | **Foundational Egress Gate:** Authorizes agent runtimes in spoke projects to route traffic through the gateway to Google APIs (`telemetry`, `aiplatform`, `agentregistry`). |
| **`PROJECT_GOVERNANCE`** (Agent Registry IAP) | `principal://agents.global.org-${ORG_ID}.system.id.goog/resources/aiplatform/projects/${PROJECT_NUMBER_CONCIERGE}/.../reasoningEngines/${CONCIERGE_ENGINE_ID}` | `roles/iap.egressor` on `burger-seller-agent` | **Targeted A2A Egress Authorization:** Fine-grained policy allowing only the Concierge agent instance to invoke the Burger Seller service via the Central Gateway. |

### Create Custom IAM Role in `PROJECT_GOVERNANCE`

```bash
# create custom role in central governance project
gcloud iam roles create ar_agw_cross_project_sa \
  --project=${PROJECT_GOVERNANCE} \
  --title="Runtime Agent Gateway Cross-Project SA" \
  --description="Custom role for cross-project service agents to access Central Agent Gateway" \
  --permissions="networkservices.agentGateways.get,networkservices.agentGateways.use,networkservices.operations.get" \
  --stage="GA"
```

### Assign Custom Role to Agent Runtime Service Agents

> aside positive
> **SERVICE AGENT PROVISIONING NOTE:** In Google Cloud, Google-managed service agents
> (`service-<PROJECT_NUMBER>@gcp-sa-aiplatform.iam.gserviceaccount.com` and
> `service-<PROJECT_NUMBER>@gcp-sa-aiplatform-re.iam.gserviceaccount.com`) are lazily
> provisioned when an API is first used. Calling `gcloud beta services identity create`
> ensures the service accounts exist in IAM before attaching cross-project bindings.

```bash
# 1. ensure vertex ai service identities are provisioned across all projects
for PROJ in ${PROJECT_GOVERNANCE} ${PROJECT_CONCIERGE} ${PROJECT_SELLERS}; do
  gcloud beta services identity create --service=aiplatform.googleapis.com --project=${PROJ}
done
```

```bash
# 2. derive vertex ai service agent emails
export CONCIERGE_AI_SA="service-${PROJECT_NUMBER_CONCIERGE}@gcp-sa-aiplatform.iam.gserviceaccount.com"
export CONCIERGE_RE_SA="service-${PROJECT_NUMBER_CONCIERGE}@gcp-sa-aiplatform-re.iam.gserviceaccount.com"
export CONCIERGE_COMPUTE_SA="${PROJECT_NUMBER_CONCIERGE}-compute@developer.gserviceaccount.com"

export SELLERS_AI_SA="service-${PROJECT_NUMBER_SELLERS}@gcp-sa-aiplatform.iam.gserviceaccount.com"
export SELLERS_RE_SA="service-${PROJECT_NUMBER_SELLERS}@gcp-sa-aiplatform-re.iam.gserviceaccount.com"
export SELLERS_COMPUTE_SA="${PROJECT_NUMBER_SELLERS}-compute@developer.gserviceaccount.com"

# 3. grant custom role & network viewer to Concierge and Sellers Service Agents
for SA in ${CONCIERGE_AI_SA} ${SELLERS_AI_SA}; do
  gcloud projects add-iam-policy-binding ${PROJECT_GOVERNANCE} \
    --member="serviceAccount:${SA}" \
    --role="projects/${PROJECT_GOVERNANCE}/roles/ar_agw_cross_project_sa" \
    --condition=None

  gcloud projects add-iam-policy-binding ${PROJECT_GOVERNANCE} \
    --member="serviceAccount:${SA}" \
    --role="roles/networkservices.viewer" \
    --condition=None
done

# 4. grant agent registry viewer & project viewer on Governance Project for dynamic autodiscovery
for MEMBER in "serviceAccount:${CONCIERGE_AI_SA}" "serviceAccount:${CONCIERGE_RE_SA}" "serviceAccount:${CONCIERGE_COMPUTE_SA}" "serviceAccount:${SELLERS_AI_SA}" "serviceAccount:${SELLERS_RE_SA}" "serviceAccount:${SELLERS_COMPUTE_SA}" "principalSet://agents.global.org-${ORG_ID}.system.id.goog/attribute.platformContainer/aiplatform/projects/${PROJECT_NUMBER_CONCIERGE}" "principalSet://agents.global.org-${ORG_ID}.system.id.goog/attribute.platformContainer/aiplatform/projects/${PROJECT_NUMBER_SELLERS}"; do
  gcloud projects add-iam-policy-binding ${PROJECT_GOVERNANCE} \
    --member="${MEMBER}" \
    --role="roles/agentregistry.viewer" \
    --condition=None
done

for SA in ${CONCIERGE_COMPUTE_SA} ${CONCIERGE_AI_SA}; do
  gcloud projects add-iam-policy-binding ${PROJECT_GOVERNANCE} \
    --member="serviceAccount:${SA}" \
    --role="roles/viewer" \
    --condition=None
done

# 5. grant vertex ai user on Sellers project to Concierge for cross-project A2A invocation
for MEMBER in "serviceAccount:${CONCIERGE_AI_SA}" "serviceAccount:${CONCIERGE_RE_SA}" "serviceAccount:${CONCIERGE_COMPUTE_SA}" "principalSet://agents.global.org-${ORG_ID}.system.id.goog/attribute.platformContainer/aiplatform/projects/${PROJECT_NUMBER_CONCIERGE}"; do
  gcloud projects add-iam-policy-binding ${PROJECT_SELLERS} \
    --member="${MEMBER}" \
    --role="roles/aiplatform.user" \
    --condition=None
done
```

This concludes the cross-project IAM setup... next on to the *Deploy Seller & Concierge Agents* section.

---

## Deploy Seller & Concierge Agents
Duration: 15:00

Clone the multi-agent application codebase and install dependencies:

```bash
# clone multi-agent repository
git clone https://github.com/demichael4520/cross-project-multiagent.git
cd cross-project-multiagent
uv sync
```

### Create Shared Central Staging Bucket

#### Why Use a Centralized Shared Staging Bucket?
When deploying Vertex AI Reasoning Engines (`agent_engines.create`), the Vertex AI SDK packages your Python application code, dependencies, and serialized agent instances into build artifacts and uploads them to a Cloud Storage **staging bucket** before container provisioning begins.

In this multi-project architecture, we host the staging bucket centrally in **`PROJECT_GOVERNANCE`** and grant cross-project access to the spoke service agents for three key architectural reasons:

1. **Centralized Artifact Auditing & Governance:** Central IT and SecOps maintain complete visibility and provenance over all agent codebase bundles and serialized packages deployed across the enterprise, preventing untracked shadow binaries.
2. **Simplified Spoke Project Footprint:** Spoke projects (`PROJECT_CONCIERGE` and `PROJECT_SELLERS`) remain lightweight execution environments without needing to provision, maintain, and secure individual storage buckets in every spoke project.
3. **Unified Lifecycle Management:** Central IT can enforce centralized object retention and auto-deletion policies (such as purging temporary deployment archives after 7 days) in a single bucket.

To enable the Vertex AI Service Agents in `PROJECT_CONCIERGE` and `PROJECT_SELLERS` to write and retrieve deployment bundles during container initialization, we assign `roles/storage.objectAdmin` on the shared bucket:

```bash
# create shared central staging bucket
gcloud storage buckets create gs://${PROJECT_GOVERNANCE}-shared-staging \
  --project=${PROJECT_GOVERNANCE} \
  --location=${REGION}
```

```bash
# grant cross-project read/write access to runtime service agents
gcloud storage buckets add-iam-policy-binding gs://${PROJECT_GOVERNANCE}-shared-staging \
  --member="serviceAccount:service-${PROJECT_NUMBER_CONCIERGE}@gcp-sa-aiplatform.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"

gcloud storage buckets add-iam-policy-binding gs://${PROJECT_GOVERNANCE}-shared-staging \
  --member="serviceAccount:service-${PROJECT_NUMBER_SELLERS}@gcp-sa-aiplatform.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

### How Cross-Project Agent Gateway Binding Works

In this step, you will deploy the Seller Agents into the spoke project
(`PROJECT_SELLERS`) while configuring them to route egress through the Central
Agent Gateway in `PROJECT_GOVERNANCE`.

This is the first time you are specifying `--governance-project` and `--gateway`
across project boundaries. Behind the scenes, the deployment script
(`deploy_burger.py`) configures the Vertex AI Agent Runtime using the Python SDK:

```python
# snippet from deploy_burger.py
burger_config = {
    "identity_type": "AGENT_IDENTITY",
    "agent_gateway_config": {
        "agent_to_anywhere_config": {
            "agent_gateway": f"projects/{args.governance_project}/locations/{args.region}/agentGateways/{args.gateway}"
        }
    },
    # ...
}
deployed_burger = client.agent_engines.create(agent=burger_playground, config=burger_config)
```

#### Key Mechanics of Cross-Project Binding:
1. **Cross-Project Resource URI:** The `agent_gateway` parameter explicitly
   points to the gateway in the Central Governance Project:
   `projects/${PROJECT_GOVERNANCE}/locations/${REGION}/agentGateways/${AGW_NAME}`.
2. **Control Plane Resolution:** During deployment, the Sellers project's Vertex
   AI Service Agent utilizes the `ar_agw_cross_project_sa` role granted earlier
   to resolve, validate, and bind to the central gateway across project boundaries.
3. **Transparent Egress Redirection:** Once the container is running, 100% of
   its outbound network requests (calls to `aiplatform`, IAM credentials, and
   peer agents) are transparently proxied through the Central Agent Gateway.
   The spoke project requires **no local VPC, NAT gateways, or private interconnects**.
4. **Agent Identity Attestation:** Setting `"identity_type": "AGENT_IDENTITY"`
   ensures the container is issued a cryptographically attested SPIFFE identity
   (`principal://...`), which is evaluated by IAP on the Central Gateway for
   all egress traffic.

### Deploy Burger & Pizza Seller Agents to `PROJECT_SELLERS`

```bash
# 1. deploy Burger Seller Agent to PROJECT_SELLERS
uv run python deploy_burger.py \
  --project=${PROJECT_SELLERS} \
  --region=${REGION} \
  --governance-project=${PROJECT_GOVERNANCE} \
  --gateway=projects/${PROJECT_GOVERNANCE}/locations/${REGION}/agentGateways/${AGW_NAME}
```

```bash
# 2. deploy Pizza Seller Agent to PROJECT_SELLERS
uv run python deploy_pizza.py \
  --project=${PROJECT_SELLERS} \
  --region=${REGION} \
  --governance-project=${PROJECT_GOVERNANCE} \
  --gateway=projects/${PROJECT_GOVERNANCE}/locations/${REGION}/agentGateways/${AGW_NAME}
```

### Validate Seller Gateway Routing

```bash
# 1. retrieve deployed seller reasoning engine IDs from generated environment files
export BURGER_ENGINE_ID=$(grep BURGER_SELLER_AGENT_ID burger_agent.env | awk -F'/' '{print $NF}')
export PIZZA_ENGINE_ID=$(grep PIZZA_SELLER_AGENT_ID pizza_agent.env | awk -F'/' '{print $NF}')

echo "Burger Engine ID: ${BURGER_ENGINE_ID}"
echo "Pizza Engine ID:  ${PIZZA_ENGINE_ID}"
```

```bash
# 2. inspect runtime configuration for both Seller Agents
for ENGINE_ID in ${BURGER_ENGINE_ID} ${PIZZA_ENGINE_ID}; do
  curl -s -X GET "https://${REGION}-aiplatform.googleapis.com/v1beta1/projects/${PROJECT_SELLERS}/locations/${REGION}/reasoningEngines/${ENGINE_ID}" \
    -H "Authorization: Bearer $(gcloud auth application-default print-access-token)" \
    -H "Content-Type: application/json" \
    | jq '{displayName: .displayName, identityType: .spec.identityType, effectiveIdentity: .spec.effectiveIdentity, agentGatewayConfig: .spec.deploymentSpec.agentGatewayConfig}'
done
```

#### Sample Output:

```json
{
  "displayName": "burger-seller-agent-adk",
  "identityType": "AGENT_IDENTITY",
  "effectiveIdentity": "agents.global.org-123456789012.system.id.goog/resources/aiplatform/projects/987654321098/locations/us-central1/reasoningEngines/7422958580011106304",
  "agentGatewayConfig": {
    "agentToAnywhereConfig": {
      "agentGateway": "projects/my-governance-project/locations/us-central1/agentGateways/centralized-agw"
    }
  }
}
{
  "displayName": "pizza-seller-agent-adk",
  "identityType": "AGENT_IDENTITY",
  "effectiveIdentity": "agents.global.org-123456789012.system.id.goog/resources/aiplatform/projects/987654321098/locations/us-central1/reasoningEngines/1451185474117828608",
  "agentGatewayConfig": {
    "agentToAnywhereConfig": {
      "agentGateway": "projects/my-governance-project/locations/us-central1/agentGateways/centralized-agw"
    }
  }
}
```

> aside positive
> **CRITICAL CROSS-PROJECT BINDING VALIDATION:** This output confirms that cross-project
> binding is successful because `agentGatewayConfig.agentToAnywhereConfig.agentGateway`
> is populated with the Central Agent Gateway resource name in `PROJECT_GOVERNANCE`.
> If this field is `null` or missing, cross-project binding was not successful (typically
> caused by missing `ar_agw_cross_project_sa` or `roles/networkservices.viewer` permissions
> on the spoke project's Vertex AI Service Agent).

### Deploy Purchasing Concierge Agent to `PROJECT_CONCIERGE`

```bash
# deploy Purchasing Concierge to PROJECT_CONCIERGE
uv run python deploy_concierge_adk.py \
  --project=${PROJECT_CONCIERGE} \
  --region=${REGION} \
  --staging-bucket=gs://${PROJECT_GOVERNANCE}-shared-staging \
  --gateway-name=${AGW_NAME} \
  --gateway-project=${PROJECT_GOVERNANCE}
```

```bash
# retrieve Concierge engine ID from generated environment file
export CONCIERGE_ENGINE_ID=$(grep CONCIERGE_AGENT_ID concierge_agent.env | awk -F'/' '{print $NF}')
echo "Concierge Engine ID: ${CONCIERGE_ENGINE_ID}"
```

```bash
# inspect runtime configuration for Purchasing Concierge
curl -s -X GET "https://${REGION}-aiplatform.googleapis.com/v1beta1/projects/${PROJECT_CONCIERGE}/locations/${REGION}/reasoningEngines/${CONCIERGE_ENGINE_ID}" \
  -H "Authorization: Bearer $(gcloud auth application-default print-access-token)" \
  -H "Content-Type: application/json" \
  | jq '{displayName: .displayName, identityType: .spec.identityType, effectiveIdentity: .spec.effectiveIdentity, agentGatewayConfig: .spec.deploymentSpec.agentGatewayConfig}'
```

#### Sample Output:

```json
{
  "displayName": "purchasing-concierge-adk",
  "identityType": "AGENT_IDENTITY",
  "effectiveIdentity": "agents.global.org-123456789012.system.id.goog/resources/aiplatform/projects/112233445566/locations/us-central1/reasoningEngines/3569530964470136832",
  "agentGatewayConfig": {
    "agentToAnywhereConfig": {
      "agentGateway": "projects/my-governance-project/locations/us-central1/agentGateways/centralized-agw"
    }
  }
}
```

> aside positive
> **CRITICAL CROSS-PROJECT BINDING VALIDATION:** This confirms that the Purchasing
> Concierge runtime in `PROJECT_CONCIERGE` is also successfully bound to the Central
> Agent Gateway in `PROJECT_GOVERNANCE`. If `agentGatewayConfig` is `null`, ensure
> that the Concierge Service Agent was granted `roles/ar_agw_cross_project_sa` and
> `roles/networkservices.viewer` in `PROJECT_GOVERNANCE`.

This concludes the agent deployments... next on to the *Register Agents in Central Agent Registry* section.

---

## Register Agents in Central Agent Registry
Duration: 10:00

Register all three agents in the Central Agent Registry in `PROJECT_GOVERNANCE`
using cross-project regional mTLS endpoints and numeric project numbers.

### Why Numeric Project Numbers and Regional mTLS Are Required

When registering agent endpoints in Agent Registry, two naming conventions are
critical for cross-project autodiscovery and security policy evaluation:

1. **Numeric Project Numbers (`projects/${PROJECT_NUMBER_...}/...`):**
   * **IAM & SPIFFE Canonical Alignment:** Google Cloud Identity-Aware Proxy
     (IAP) and SPIFFE Agent Identity attestations evaluate resource permissions
     using canonical numeric project numbers (e.g., `projects/987654321098/...`),
     rather than alphanumeric project IDs (e.g., `cosmopup-sellers-prod`).
   * **Auto-Discovery Regex Parsing:** The Purchasing Concierge's dynamic
     discovery logic uses regex matching against `projects/\d+/locations/.../reasoningEngines/\d+`.
     Registering with alphanumeric IDs breaks regex extraction and leads to
     `403 Forbidden` policy mismatches during runtime query routing.

2. **Regional mTLS Endpoints (`https://${REGION}-aiplatform.mtls.googleapis.com`):**
   * **Mutual TLS Authentication:** Cross-project Agent-to-Agent (A2A) traffic
     routed through Agent Gateway requires mTLS for cryptographic client identity
     attestation.
   * **Regional Data Locality:** Regional endpoints ensure traffic remains within
     the designated region (`us-central1`), minimizing cross-region latency and
     maintaining compliance.

### Register Services in Agent Registry

```bash
# 1. register Burger Seller Agent
gcloud agent-registry services create burger-seller-agent \
  --project=${PROJECT_GOVERNANCE} \
  --location=${REGION} \
  --display-name="Burger Seller Agent" \
  --description="Specialist agent that sells burgers and fries" \
  --endpoint-spec-type=no-spec \
  --interfaces=protocolBinding=JSONRPC,url=https://${REGION}-aiplatform.mtls.googleapis.com/v1/projects/${PROJECT_NUMBER_SELLERS}/locations/${REGION}/reasoningEngines/${BURGER_ENGINE_ID}
```

```bash
# 2. register Pizza Seller Agent
gcloud agent-registry services create pizza-seller-agent \
  --project=${PROJECT_GOVERNANCE} \
  --location=${REGION} \
  --display-name="Pizza Seller Agent" \
  --description="Specialist agent that sells pizzas and pasta" \
  --endpoint-spec-type=no-spec \
  --interfaces=protocolBinding=JSONRPC,url=https://${REGION}-aiplatform.mtls.googleapis.com/v1/projects/${PROJECT_NUMBER_SELLERS}/locations/${REGION}/reasoningEngines/${PIZZA_ENGINE_ID}
```

```bash
# 3. register Purchasing Concierge Agent
gcloud agent-registry services create purchasing-concierge-adk \
  --project=${PROJECT_GOVERNANCE} \
  --location=${REGION} \
  --display-name="Purchasing Concierge Agent" \
  --description="Orchestrator concierge agent that routes purchasing requests" \
  --endpoint-spec-type=no-spec \
  --interfaces=protocolBinding=JSONRPC,url=https://${REGION}-aiplatform.mtls.googleapis.com/v1/projects/${PROJECT_NUMBER_CONCIERGE}/locations/${REGION}/reasoningEngines/${CONCIERGE_ENGINE_ID}
```

### Describe and Validate Agent Registry Endpoints

Inspect the configuration of each registered agent in the Central Agent Registry:

```bash
# 1. describe each registered agent service
for SERVICE in burger-seller-agent pizza-seller-agent purchasing-concierge-adk; do
  echo "=== Describing Service: ${SERVICE} ==="
  gcloud agent-registry services describe ${SERVICE} \
    --project=${PROJECT_GOVERNANCE} \
    --location=${REGION}
done
```

#### Sample Output:

```yaml
=== Describing Service: burger-seller-agent ===
createTime: '2026-08-29T20:36:02.513184940Z'
description: Specialist agent that sells burgers and fries
displayName: Burger Seller Agent
endpointSpec:
  type: NO_SPEC
interfaces:
- protocolBinding: JSONRPC
  url: https://us-central1-aiplatform.mtls.googleapis.com/v1/projects/987654321098/locations/us-central1/reasoningEngines/7422958580011106304
name: projects/my-governance-project/locations/us-central1/services/burger-seller-agent
registryResource: projects/998877665544/locations/us-central1/endpoints/agentregistry-00000000-0000-0000-c457-663abd948503
updateTime: '2026-08-29T20:36:02.769964359Z'
```

#### Key Fields Breakdown:

| Output Field | Purpose & Significance |
| :--- | :--- |
| `name` | The canonical path of the service registered in `PROJECT_GOVERNANCE`. |
| `registryResource` | The underlying **Agent Registry Endpoint ID** (`projects/.../endpoints/agentregistry-...`). This endpoint is the target evaluated by IAP for `roles/iap.egressor` policies. |
| `interfaces[0].url` | The regional mTLS destination URL targeting the spoke project's Reasoning Engine using its **numeric project number**. |
| `interfaces[0].protocolBinding` | Specifies `JSONRPC` communication protocol over mTLS. |

```bash
# 2. capture underlying Agent Registry endpoint IDs
export BURGER_ENDPOINT_ID=$(gcloud agent-registry services describe burger-seller-agent --project=${PROJECT_GOVERNANCE} --location=${REGION} --format="value(registryResource)" | awk -F'/' '{print $NF}')
export PIZZA_ENDPOINT_ID=$(gcloud agent-registry services describe pizza-seller-agent --project=${PROJECT_GOVERNANCE} --location=${REGION} --format="value(registryResource)" | awk -F'/' '{print $NF}')
export CONCIERGE_ENDPOINT_ID=$(gcloud agent-registry services describe purchasing-concierge-adk --project=${PROJECT_GOVERNANCE} --location=${REGION} --format="value(registryResource)" | awk -F'/' '{print $NF}')

echo "Burger Endpoint ID:    ${BURGER_ENDPOINT_ID}"
echo "Pizza Endpoint ID:     ${PIZZA_ENDPOINT_ID}"
echo "Concierge Endpoint ID: ${CONCIERGE_ENDPOINT_ID}"
```

### The Architectural Importance of Agent Registry

A critical innovation of this multi-agent architecture is the **complete elimination
of hardcoded agent IDs, project numbers, and endpoint URLs** inside the client
application code.

In naive multi-agent implementations, developers often hardcode downstream
agent endpoints or pass them via static environment variables (e.g.,
`BURGER_AGENT_ID=projects/987654321098/...`). In an enterprise ecosystem with
hundreds of agents across independent business units, hardcoding creates severe
operational and security liabilities:

| Dimension | Hardcoded Agent Architecture (Anti-Pattern) | Agent Registry-Driven Architecture (Best Practice) |
| :--- | :--- | :--- |
| **Coupling & Lifecycles** | **Tight coupling.** Redeploying a worker agent generates a new Reasoning Engine ID, forcing updates and redeployments of every consumer orchestrator. | **Decoupled lifecycles.** Worker teams redeploy independently in spoke projects. Updating the registry pointer instantly updates all consumers. |
| **Operational Scalability** | **Brittle configuration.** Adding new domain agents (e.g., Taco Seller, Dessert Seller) requires modifying code across all client agents. | **Zero-touch onboarding.** New agents publish to the Central Registry; orchestrators auto-discover new capabilities dynamically at runtime. |
| **Security Governance** | **Invisible shadow connections.** SecOps has no centralized visibility or policy control point over inter-agent communications. | **Centralized audit & policy plane.** Every agent is a managed registry resource governed by Identity-Aware Proxy (IAP) IAM policies. |
| **Environment Portability** | **Environment-locked.** Configuration must be manually rewritten when promoting across dev, stage, and prod environments. | **Fully portable.** The agent queries its environment's Central Registry and self-configures routing dynamically based on regional discovery. |

### Central Registry Placement: "If It Is Not in the Registry, It Does Not Exist to Agents"

In this centralized governance architecture, the Agent Registry resides
exclusively in the **Centralized Governance Project (`PROJECT_GOVERNANCE`)**
alongside the Agent Gateway. Spoke projects (`PROJECT_SELLERS` and
`PROJECT_CONCIERGE`) do not host their own decentralized registries.

> aside negative
> **THE CENTRAL GOVERNANCE RULE:** **If a resource is not registered in the
> Central Agent Registry, it is completely invisible and unreachable to agents.**
>
> 1. **Discovery Isolation:** Even if a Reasoning Engine, MCP server on Cloud
>    Run, or API endpoint is active in a spoke project, client agents cannot
>    discover or route to it until it is published in `PROJECT_GOVERNANCE`.
> 2. **Gateway Egress Blocking:** The Agent Gateway configuration references
>    only the Central Registry (`//agentregistry.googleapis.com/projects/${PROJECT_GOVERNANCE}/locations/${REGION}`).
>    Any outbound call to an uncataloged destination lacks route definitions and
>    IAP authorization policies, resulting in an immediate network or policy block.

### Supported Registry Asset Categories & Interaction Paradigms

The Central Agent Registry acts as the single catalog for three distinct asset types:
- **Peer Agents & Subagents:** Containerized Reasoning Engines publishing regional mTLS endpoints (e.g., `burger-seller-agent`, `pizza-seller-agent`).
- **Model Context Protocol (MCP) Servers:** Enterprise tool servers (e.g., Cloud Run, GKE) publishing tool specifications and `/mcp` endpoints.
- **Core Google Cloud Endpoints & APIs:** Infrastructure endpoints (e.g., `core-gapi-services`) enabling secure egress to `aiplatform`, IAM credentials, and telemetry.

#### Defining Interaction Attributes: A2A vs. Non-A2A Services

When registering services in Agent Registry, endpoints are categorized based on their **interaction paradigm**:

| Attribute | A2A (Agent-to-Agent) Services | Non-A2A (Tools & API Endpoints) |
| :--- | :--- | :--- |
| **Definition** | **Autonomous conversational agents** that possess internal reasoning loops, handle natural language goals, and manage multi-turn conversational state. | **Deterministic, passive endpoints** (e.g., MCP tool servers, REST microservices, Google Cloud APIs) that execute specific procedural actions. |
| **Specification Type** | `--endpoint-spec-type=agent-card` or `--endpoint-spec-type=no-spec` with Reasoning Engine mTLS endpoints. | `--mcp-server-spec-type=tool-spec` or `--endpoint-spec-type=no-spec` with standard JSONRPC/HTTP interfaces. |
| **Invocation Pattern** | **Agent Delegation:** The orchestrator delegates natural language task prompts (`agent.query(message="...")`) to the peer agent. | **Tool Invocation:** The agent invokes structured schemas with strict typed arguments (`mcp.call_tool(name="...", args={...})`). |
| **Examples in this Codelab** | `burger-seller-agent`, `pizza-seller-agent`, `purchasing-concierge-adk`. | `core-gapi-services` (Cloud APIs: `aiplatform`, `telemetry`, `iamcredentials`). |

### How Dynamic Auto-Discovery Works at Runtime

Instead of maintaining static URLs, the Purchasing Concierge performs **dynamic
runtime autodiscovery** during session initialization: 

1. **Query Central Catalog:** The Concierge calls the Agent Registry REST API
   (`https://agentregistry.googleapis.com/v1/projects/${PROJECT_GOVERNANCE}/locations/${REGION}/services`)
   using its authenticated runtime credentials.
2. **Inspect Service Interfaces:** It enumerates all published services,
   filtering by `displayName` and parsing the underlying mTLS regional endpoints.
3. **Extract Canonical Resource Paths:** It uses regular expressions to extract
   the canonical Reasoning Engine resource paths (`projects/<NUM>/locations/<LOC>/reasoningEngines/<ID>`).
4. **Populate Active Dispatch Map:** The agent dynamically binds the discovered
   endpoints to its internal dispatch routing table (`self.agent_ids`).

#### Auto-Discovery Code Implementation (from `concierge_adk/agent.py`)

```python
def autodiscover_agent_services(self):
    """Queries Central Agent Registry via REST API to discover seller agents dynamically."""
    headers = {"Authorization": f"Bearer {self._get_auth_token()}"}
    registry_url = f"https://agentregistry.googleapis.com/v1/projects/{self.governance_project}/locations/{self.region}/services"
    
    # 1. Fetch all registered services from Central Governance Project
    response = requests.get(registry_url, headers=headers)
    if response.status_code != 200:
        return
        
    services = response.json().get("services", [])
    discovered_agents = {}
    
    # 2. Iterate through published service definitions and interfaces
    for service in services:
        display_name = service.get("displayName", "")
        interfaces = service.get("interfaces", [])
        if not interfaces:
            continue
            
        target_url = interfaces[0].get("url", "")
        
        # 3. Extract canonical numeric project reasoning engine path
        re_match = re.search(r"(projects/\d+/locations/[^/]+/reasoningEngines/\d+)", target_url)
        resource_path = re_match.group(1) if re_match else target_url
        combined_str = f"{display_name} {service.get('name', '')}".lower()
        
        # 4. Map discovered services to logical capability keys
        if "burger" in combined_str:
            discovered_agents["burger_seller_agent"] = resource_path
        elif "pizza" in combined_str:
            discovered_agents["pizza_seller_agent"] = resource_path

    # 5. Update runtime routing table in-memory (zero hardcoded configuration)
    self.agent_ids.update(discovered_agents)
```

This concludes the registry configuration... next on to the *Configure IAP Access Policies* section.

---

## Configure IAP Access Policies in PROJECT_GOVERNANCE
Duration: 10:00

Agent Gateway uses Identity-Aware Proxy (IAP) to evaluate authorization
decisions under a **Default Deny** security posture:

1. **ALLOW Policy:** The Purchasing Concierge Agent is granted access to call the Burger Agent.
2. **BLOCK Policy:** The Purchasing Concierge Agent is initially left unassigned on the Pizza Agent (denied by default with HTTP 403).
3. **DYNAMIC GRANT:** The policy is updated live to attach `roles/iap.egressor` on the Pizza Agent and verified with immediate 200 OK success.

### Formulate Concierge Agent Identity

```bash
# formulate the exact SPIFFE identity for the Concierge Agent
export CONCIERGE_SPIFFE_PRINCIPAL="principal://agents.global.org-${ORG_ID}.system.id.goog/resources/aiplatform/projects/${PROJECT_NUMBER_CONCIERGE}/locations/${REGION}/reasoningEngines/${CONCIERGE_ENGINE_ID}"
echo "Concierge SPIFFE Principal: ${CONCIERGE_SPIFFE_PRINCIPAL}"
```

### Grant Egress Access only to the Burger Agent

#### What is Happening Here?
You are binding the `roles/iap.egressor` role on the `burger-seller-agent` service in **Agent Registry**, granting invocation permission specifically to the Purchasing Concierge's attested SPIFFE machine identity (`${CONCIERGE_SPIFFE_PRINCIPAL}`).

When the Concierge Agent initiates a query to the Burger Agent:
1. The request is intercepted by the **Central Agent Gateway**.
2. The gateway's **Authz Extension** queries Identity-Aware Proxy (IAP) with the caller's SPIFFE principal and the target destination.
3. IAP evaluates the IAM policy attached to `burger-seller-agent` in **Agent Registry**.
4. Finding the Concierge's SPIFFE identity in the `roles/iap.egressor` binding list, IAP returns an **`ALLOW`** verdict.

#### The Architectural Importance of Agent Registry in Policy Governance:
* **Centralized Security Anchor:** In distributed enterprise multi-agent systems, worker agents are deployed across dozens of independent spoke projects. Agent Registry acts as the **central catalog and policy enforcement anchor** in `PROJECT_GOVERNANCE`. SecOps manages and audits all cross-agent access rules in a single project rather than maintaining fragmented IAM policies across scattered projects.
* **Agent-to-Agent (A2A) Least Privilege:** Standard Cloud IAM often grants broad service-account-level permissions. With Agent Registry and SPIFFE identities, authorization is enforced at the **exact agent instance level** (`principal://.../reasoningEngines/<ENGINE_ID>`), ensuring strict workload isolation.
* **Decoupled Security Operations:** Development teams deploy specialized agents into their own spoke projects without needing broad IAM privileges. Central IT independently grants or revokes consumer access in the Central Registry without modifying agent application code or redeploying containers.

```bash
# grant IAP Egress role on Burger Seller Endpoint in Agent Registry
gcloud beta iap web add-iam-policy-binding \
  --resource-type=agent-registry \
  --endpoint=${BURGER_ENDPOINT_ID} \
  --region=${REGION} \
  --project=${PROJECT_GOVERNANCE} \
  --role="roles/iap.egressor" \
  --member="${CONCIERGE_SPIFFE_PRINCIPAL}" \
  --quiet
```

### Keep Pizza Agent Unbound (Deny by Default)
Do NOT add any IAP policy binding for the Pizza Agent yet. Because Agent Gateway
enforces Deny by Default, omitting the `roles/iap.egressor` binding for the Pizza
Agent ensures initial egress attempts will be blocked with HTTP 403 Forbidden.

If an IAM policy binding previously existed on the Pizza Agent, remove it explicitly:

```bash
# ensure pizza agent has no prior egress bindings
gcloud beta iap web remove-iam-policy-binding \
  --resource-type=agent-registry \
  --endpoint=${PIZZA_ENDPOINT_ID} \
  --region=${REGION} \
  --project=${PROJECT_GOVERNANCE} \
  --role="roles/iap.egressor" \
  --member="${CONCIERGE_SPIFFE_PRINCIPAL}" \
  --quiet || true
```

### Validate Initial Agent IAM Policies

```bash
# 1. inspect IAP IAM policy for Burger Agent (ALLOW policy)
gcloud beta iap web get-iam-policy \
  --resource-type=agent-registry \
  --endpoint=${BURGER_ENDPOINT_ID} \
  --region=${REGION} \
  --project=${PROJECT_GOVERNANCE}
```

#### Sample Output (Burger Agent — ALLOW):

```yaml
bindings:
- members:
  - principal://agents.global.org-123456789012.system.id.goog/resources/aiplatform/projects/112233445566/locations/us-central1/reasoningEngines/3569530964470136832
  role: roles/iap.egressor
etag: BwZaNcFHR0s=
version: 1
```

> aside positive
> **POLICY INTERPRETATION:** The Burger Agent's endpoint contains an active binding granting `roles/iap.egressor` specifically to the Purchasing Concierge's SPIFFE machine identity. When the Concierge queries the Burger Agent, IAP evaluates this policy and returns `ALLOW`.

```bash
# 2. inspect IAP IAM policy for Pizza Agent (DENY BY DEFAULT)
gcloud beta iap web get-iam-policy \
  --resource-type=agent-registry \
  --endpoint=${PIZZA_ENDPOINT_ID} \
  --region=${REGION} \
  --project=${PROJECT_GOVERNANCE}
```

> aside negative
> **DENY BY DEFAULT INTERPRETATION:** The Pizza Agent endpoint contains **no bindings** (`bindings: []` or just `etag`). Under Agent Gateway's Default Deny posture, any attempt by the Concierge to invoke the Pizza Agent will be evaluated by IAP and logged as `Permission Denied` (or blocked with HTTP 403 in `ENFORCE` mode).

This concludes the policy setup... next on to the *Test and Verify Governance Policies* section.

---

## Test and Verify Governance Policies via Cloud Logging
Duration: 15:00

In this section, you will test cross-project Agent-to-Agent (A2A) interactions,
analyze authorization events in Cloud Logging, modify access policies, and
observe real-time policy enforcement.

### Step 1: Open Vertex AI Playground in `PROJECT_CONCIERGE`
1. Open the [Google Cloud Console][08-01].
2. In the top project selector bar, switch to `PROJECT_CONCIERGE`.
3. In the navigation menu, navigate to **Vertex AI > Agent Platform > Agents > Deployments**.
4. Click on **`purchasing-concierge-adk`**.
5. Select **Playground** to open the interactive chat interface on the right side of the screen.

### Step 2: Test Burger Order (ALLOW Policy -> 200 OK)
In the Playground chat window, submit the following order prompt:

```text
I would like 10 Classic Cheeseburgers. Place this order now.
```

#### What happens behind the scenes:
1. **Dynamic Discovery:** During session startup, the Purchasing Concierge queried the Central Agent Registry in `PROJECT_GOVERNANCE` (via `core-gapi-services` through Agent Gateway) to discover the regional mTLS endpoint for `burger-seller-agent`.
2. **Intent Resolution & A2A Invocation:** Gemini inside the Purchasing Concierge parses the food order intent and invokes the Burger Seller Agent via an outbound RPC to `https://${REGION}-aiplatform.mtls.googleapis.com/.../reasoningEngines/${BURGER_ENGINE_ID}`.
3. **Gateway Interception & SPIFFE Propagation:** Because the Concierge container is configured with `agent_gateway_config`, its egress traffic is captured and routed to the Central Agent Gateway in `PROJECT_GOVERNANCE`, carrying the Concierge's cryptographic SPIFFE machine identity (`principal://agents.global.org-...`).
4. **IAP Policy Evaluation:** The Central Agent Gateway invokes the IAP authorization extension (`authzExtension`). IAP evaluates the caller's SPIFFE identity against the `roles/iap.egressor` policy on the target `burger-seller-agent` resource in Agent Registry. Because access was granted earlier, IAP returns `ALLOW` and records a `GRANTED: True` audit event.
5. **Cross-Project Execution:** The Agent Gateway proxies the authorized request cross-project into `PROJECT_SELLERS`, where the Burger Seller Reasoning Engine executes its order business logic and returns the order confirmation back through the gateway.

#### Expected response:

```text
Your order for 10x Classic Cheeseburger has been placed!
Order Details:
Classic Cheeseburger (10x): IDR 85,000 each = IDR 850,000 Total: IDR 850,000
Order ID: e8f9c732-f347-4cc4-acff-cfe09ccbeddd
```

### Step 3: Inspect Agent Gateway Logs for HTTP 200 & Allowed IAP Policy
When the Purchasing Concierge routes egress traffic through the Central Agent Gateway, the gateway logs the request method, target URL, HTTP status code (200), and the IAP authorization evaluation result (`ALLOWED`) in `PROJECT_GOVERNANCE`:

```bash
# query Agent Gateway logs for successful 200 OK requests authorized by IAP policy
gcloud logging read \
  "logName=\"projects/${PROJECT_GOVERNANCE}/logs/networkservices.googleapis.com%2Fgateway_requests\" AND jsonPayload.authzPolicyInfo.result=\"ALLOWED\"" \
  --project="${PROJECT_GOVERNANCE}" \
  --limit=10 \
  --format="table(timestamp.date('%Y-%m-%d %H:%M:%S'):label=TIME, httpRequest.requestMethod:label=METHOD, httpRequest.status:label=STATUS, jsonPayload.authzPolicyInfo.result:label=IAP_AUTHZ, httpRequest.requestUrl:label=REQUEST_URL)"
```

#### Sample log output:

```text
TIME                 METHOD  STATUS  IAP_AUTHZ  REQUEST_URL
2026-08-29 21:26:32  POST    200     ALLOWED    https://telemetry.mtls.googleapis.com/v1/traces
2026-08-29 21:26:20  POST    200     ALLOWED    https://us-central1-aiplatform.mtls.googleapis.com/v1beta1/projects/my-concierge-project/locations/us-central1/publishers/google/models/gemini-2.5-flash:generateContent
2026-08-29 21:26:13  POST    200     ALLOWED    https://us-central1-aiplatform.mtls.googleapis.com/v1beta1/projects/my-sellers-project/locations/us-central1/publishers/google/models/gemini-2.5-flash:generateContent
2026-08-29 21:26:07  GET     200     ALLOWED    https://agentregistry.googleapis.com/v1alpha/projects/my-governance-project/locations/us-central1/services
```

#### Understanding the Gateway Log URLs:

Each URL logged by the Central Agent Gateway represents a distinct stage in the cross-project multi-agent execution lifecycle:

| Target URL | Purpose & Architectural Context |
| :--- | :--- |
| **`https://agentregistry.googleapis.com/v1alpha/.../services`** | **Central Dynamic Service Discovery:** The Purchasing Concierge queries the Central Agent Registry in `PROJECT_GOVERNANCE` at initialization to retrieve the catalog of available seller agent endpoints, descriptions, and metadata. |
| **`https://${REGION}-aiplatform.mtls.googleapis.com/.../projects/${PROJECT_CONCIERGE}/...:generateContent`** | **Concierge Agent Reasoning:** The Concierge runtime invokes Vertex AI Gemini in `PROJECT_CONCIERGE` via mTLS to parse the customer's order intent, evaluate constraints, and decide which specialized seller agent to invoke. |
| **`https://${REGION}-aiplatform.mtls.googleapis.com/.../projects/${PROJECT_SELLERS}/...:generateContent`** | **Cross-Project Agent-to-Agent (A2A) Execution:** The authorized outbound call routed cross-project into `PROJECT_SELLERS`. The target Burger Seller Reasoning Engine executes its order processing logic and returns the confirmed order details. |
| **`https://telemetry.mtls.googleapis.com/v1/traces`** | **Centralized Observability & Distributed Tracing:** OpenTelemetry and Cloud Trace spans emitted by the agent containers through the Central Gateway to monitor latency, track hop-by-hop execution, and audit A2A call chains. |

---

### Step 4: Test Pizza Order (BLOCK Policy -> HTTP 403 Forbidden)
In the same Playground chat window, submit the following pizza order prompt:

```text
I would like 50 BBQ Pizzas. Place this order now.
```

#### What happens behind the scenes:
1. **Dynamic Discovery:** The Purchasing Concierge resolved the `pizza-seller-agent` regional mTLS endpoint from the Central Agent Registry during startup.
2. **Intent Resolution & A2A Invocation:** Gemini inside the Purchasing Concierge attempts to dispatch the pizza order request to the Pizza Seller endpoint.
3. **Gateway Interception & SPIFFE Propagation:** The outbound RPC is captured by `agent_gateway_config` and directed to the Central Agent Gateway in `PROJECT_GOVERNANCE`, carrying the Concierge's cryptographic SPIFFE machine identity (`principal://agents.global.org-...`).
4. **IAP Policy Evaluation (Deny by Default):** The Central Agent Gateway invokes the IAP authorization extension. Because **no** `roles/iap.egressor` binding exists for the Concierge SPIFFE on the `pizza-seller-agent` resource, IAP evaluates the request as unauthorized.
5. **Policy Denial & Audit Emission:** IAP returns `DENY` (`GRANTED: False`, `STATUS: Permission Denied.`) and emits a security audit event in `PROJECT_GOVERNANCE` Cloud Logging. In `ENFORCE` mode, the gateway blocks the request with `HTTP 403 Forbidden` without routing traffic to `PROJECT_SELLERS`.

### Step 5: Inspect Agent Gateway Logs for Denied Requests (HTTP 403 / Denied)

```bash
# query Agent Gateway logs for denied requests blocked by IAP policy
gcloud logging read \
  "logName=\"projects/${PROJECT_GOVERNANCE}/logs/networkservices.googleapis.com%2Fgateway_requests\" AND (httpRequest.status=403 OR jsonPayload.authzPolicyInfo.result=\"DENIED\")" \
  --project="${PROJECT_GOVERNANCE}" \
  --limit=10 \
  --format="table(timestamp.date('%Y-%m-%d %H:%M:%S'):label=TIME, httpRequest.requestMethod:label=METHOD, httpRequest.status:label=STATUS, jsonPayload.authzPolicyInfo.result:label=IAP_AUTHZ, httpRequest.requestUrl:label=REQUEST_URL)"
```

#### Sample denied log output:

```text
TIME                 METHOD  STATUS  IAP_AUTHZ  REQUEST_URL
2026-08-29 21:30:15  POST    403     DENIED     https://us-central1-aiplatform.mtls.googleapis.com/v1beta1/projects/my-sellers-project/locations/us-central1/publishers/google/models/gemini-2.5-flash:generateContent
2026-08-29 21:18:58  GET     403     ALLOWED    https://agentregistry.googleapis.com/v1alpha/projects/my-governance-project/locations/us-central1/services
2026-08-29 21:18:16  GET     403     ALLOWED    https://agentregistry.googleapis.com/v1alpha/projects/my-governance-project/locations/us-central1/services
```

> aside negative
> **DRY_RUN POLICY EVALUATION NOTE:** Because the Authz Extension is operating in **DRY_RUN** mode, the request is not actively dropped at the network layer and the client call completes. However, Cloud Logging in `PROJECT_GOVERNANCE` captures the security evaluation as **`STATUS: 403` / `DENIED`** because the Concierge SPIFFE identity lacks the `roles/iap.egressor` role on the Pizza Seller endpoint. In a production **ENFORCE** mode deployment, the Central Agent Gateway would immediately drop the connection and block egress with HTTP 403 Forbidden.

### Step 6: Dynamically Grant Egress Access to Pizza Agent
Update the security policy in `PROJECT_GOVERNANCE` to allow the Purchasing
Concierge to call the Pizza Agent:

```bash
# grant IAP Egress role on Pizza Seller Endpoint
gcloud beta iap web add-iam-policy-binding \
  --resource-type=agent-registry \
  --endpoint=${PIZZA_ENDPOINT_ID} \
  --region=${REGION} \
  --project=${PROJECT_GOVERNANCE} \
  --role="roles/iap.egressor" \
  --member="${CONCIERGE_SPIFFE_PRINCIPAL}" \
  --quiet
```

```bash
# validate IAP policy binding on Pizza Seller Endpoint
gcloud beta iap web get-iam-policy \
  --resource-type=agent-registry \
  --endpoint=${PIZZA_ENDPOINT_ID} \
  --region=${REGION} \
  --project=${PROJECT_GOVERNANCE}
```

#### Sample Output (Pizza Agent — ALLOW):

```yaml
bindings:
- members:
  - principal://agents.global.org-123456789012.system.id.goog/resources/aiplatform/projects/112233445566/locations/us-central1/reasoningEngines/3569530964470136832
  role: roles/iap.egressor
etag: BwZaNkqk4is=
version: 1
```

### Step 7: Query Pizza Agent Again (Immediate 200 OK Success)
In the Playground chat window, re-submit the order prompt:

```text
I would like 100 Hawaiian Pizza. Place this order now.
```

#### What happens behind the scenes:
1. **Dynamic Policy Refresh:** Modifying the IAM policy binding on `pizza-seller-agent` in `PROJECT_GOVERNANCE` takes effect immediately in the IAP authorization engine without restarting or redeploying any agent containers.
2. **A2A Invocation:** The Concierge dispatches the pizza order request through the Central Agent Gateway with its SPIFFE machine identity.
3. **IAP Policy Evaluation (Approval):** The gateway invokes IAP, which now evaluates the updated policy, verifies the active `roles/iap.egressor` binding on `pizza-seller-agent`, and returns `ALLOW` (`GRANTED: True`).
4. **Cross-Project Execution:** The Central Agent Gateway proxies the authorized traffic into `PROJECT_SELLERS`, where the Pizza Seller Reasoning Engine processes the order and streams the confirmation back to the Concierge.

#### Expected response:

```text
Your order for 100 Hawaiian Pizzas has been placed. Here are the details:
Hawaiian Pizza: 100 x IDR 110,000 = IDR 11,000,000 Total: IDR 11,000,000
Your Order ID is: e8ee3d7d-3ea5-493a-8720-8390488acb38.
```

### Step 8: Inspect Agent Gateway Logs for Granted Pizza Requests (HTTP 200 & Allowed)
Query the Central Agent Gateway logs in `PROJECT_GOVERNANCE` to confirm that the Pizza order request was authorized by the newly added IAP egress policy:

```bash
# query Agent Gateway logs for successful 200 OK requests authorized by IAP policy
gcloud logging read \
  "logName=\"projects/${PROJECT_GOVERNANCE}/logs/networkservices.googleapis.com%2Fgateway_requests\" AND jsonPayload.authzPolicyInfo.result=\"ALLOWED\"" \
  --project="${PROJECT_GOVERNANCE}" \
  --limit=10 \
  --format="table(timestamp.date('%Y-%m-%d %H:%M:%S'):label=TIME, httpRequest.requestMethod:label=METHOD, httpRequest.status:label=STATUS, jsonPayload.authzPolicyInfo.result:label=IAP_AUTHZ, httpRequest.requestUrl:label=REQUEST_URL)"
```

#### Sample log output:

```text
TIME                 METHOD  STATUS  IAP_AUTHZ  REQUEST_URL
2026-08-30 02:30:52  POST    200     ALLOWED    https://us-central1-aiplatform.mtls.googleapis.com/v1beta1/projects/my-sellers-project/locations/us-central1/publishers/google/models/gemini-2.5-flash:generateContent
2026-08-30 02:30:50  POST    200     ALLOWED    https://us-central1-aiplatform.googleapis.com:443/google.cloud.aiplatform.v1beta1.ReasoningEngineExecutionService/QueryReasoningEngine
2026-08-30 02:30:48  POST    200     ALLOWED    https://us-central1-aiplatform.mtls.googleapis.com/v1beta1/projects/my-concierge-project/locations/us-central1/publishers/google/models/gemini-2.5-flash:generateContent
```

This concludes testing and verification... next on to the *Clean up* section.

[08-01]: https://console.cloud.google.com/

---

## Clean up
Duration: 10:00

To avoid incurring charges to your Google Cloud account for the resources used
in this Codelab, execute the teardown steps in strict reverse dependency order:

### 1. Clean Up Reasoning Engine Deployments

```bash
# delete all Reasoning Engines deployed in Concierge and Sellers projects
uv run python -c '
import vertexai
import os
from vertexai.preview import reasoning_engines

region = os.environ.get("REGION", "us-central1")
for proj in [os.environ.get("PROJECT_CONCIERGE"), os.environ.get("PROJECT_SELLERS")]:
    if not proj:
        continue
    print(f"Cleaning reasoning engines in {proj}...")
    vertexai.init(project=proj, location=region)
    for eng in reasoning_engines.ReasoningEngine.list():
        print(f"  Deleting {eng.resource_name} ({eng.display_name})...")
        eng.delete()
'
```

### 2. Delete Agent Registry Services

```bash
# delete agent registry services in Central Governance Project
for SERVICE in burger-seller-agent pizza-seller-agent purchasing-concierge-adk core-gapi-services; do
  gcloud agent-registry services delete ${SERVICE} \
    --project=${PROJECT_GOVERNANCE} \
    --location=${REGION} \
    --quiet || true
done
```

### 3. Delete Agent Gateway and Security Policies

> aside negative
> **DEPENDENCY ORDER NOTE:** The Authorization Policy (`authz-policies`) references
> both the Agent Gateway and the Authz Extension. You must delete the Authorization
> Policy first before deleting the extension or gateway.

```bash
# 1. delete authorization policy
gcloud beta network-security authz-policies delete ${AGW_NAME}-authz-policy-profile-iap \
  --location=${REGION} \
  --project=${PROJECT_GOVERNANCE} --quiet || true

# 2. delete authorization extension
gcloud service-extensions authz-extensions delete ${AGW_NAME}-svc-ext-authz-iap-dryrun \
  --location=${REGION} \
  --project=${PROJECT_GOVERNANCE} --quiet || true

# 3. delete agent gateway
gcloud alpha network-services agent-gateways delete ${AGW_NAME} \
  --project=${PROJECT_GOVERNANCE} \
  --location=${REGION} --quiet || true
```

### 4. Remove Cross-Project IAM Bindings & Custom Role

```bash
# 1. remove custom role and network viewer bindings in PROJECT_GOVERNANCE
for SA in ${CONCIERGE_AI_SA} ${SELLERS_AI_SA}; do
  gcloud projects remove-iam-policy-binding ${PROJECT_GOVERNANCE} \
    --member="serviceAccount:${SA}" \
    --role="projects/${PROJECT_GOVERNANCE}/roles/ar_agw_cross_project_sa" --quiet || true

  gcloud projects remove-iam-policy-binding ${PROJECT_GOVERNANCE} \
    --member="serviceAccount:${SA}" \
    --role="roles/networkservices.viewer" --quiet || true
done

# 2. remove agent registry viewer & project viewer bindings in PROJECT_GOVERNANCE
for MEMBER in "serviceAccount:${CONCIERGE_AI_SA}" "serviceAccount:${CONCIERGE_RE_SA}" "serviceAccount:${CONCIERGE_COMPUTE_SA}" "serviceAccount:${SELLERS_AI_SA}" "serviceAccount:${SELLERS_RE_SA}" "serviceAccount:${SELLERS_COMPUTE_SA}" "principalSet://agents.global.org-${ORG_ID}.system.id.goog/attribute.platformContainer/aiplatform/projects/${PROJECT_NUMBER_CONCIERGE}" "principalSet://agents.global.org-${ORG_ID}.system.id.goog/attribute.platformContainer/aiplatform/projects/${PROJECT_NUMBER_SELLERS}"; do
  gcloud projects remove-iam-policy-binding ${PROJECT_GOVERNANCE} \
    --member="${MEMBER}" \
    --role="roles/agentregistry.viewer" --quiet || true
done

for SA in ${CONCIERGE_COMPUTE_SA} ${CONCIERGE_AI_SA}; do
  gcloud projects remove-iam-policy-binding ${PROJECT_GOVERNANCE} \
    --member="serviceAccount:${SA}" \
    --role="roles/viewer" --quiet || true
done

# 3. remove vertex ai user bindings in PROJECT_SELLERS
for MEMBER in "serviceAccount:${CONCIERGE_AI_SA}" "serviceAccount:${CONCIERGE_RE_SA}" "serviceAccount:${CONCIERGE_COMPUTE_SA}" "principalSet://agents.global.org-${ORG_ID}.system.id.goog/attribute.platformContainer/aiplatform/projects/${PROJECT_NUMBER_CONCIERGE}"; do
  gcloud projects remove-iam-policy-binding ${PROJECT_SELLERS} \
    --member="${MEMBER}" \
    --role="roles/aiplatform.user" --quiet || true
done

# 4. delete custom IAM role in PROJECT_GOVERNANCE
gcloud iam roles delete ar_agw_cross_project_sa \
  --project=${PROJECT_GOVERNANCE} --quiet || true
```

### 5. Delete Shared GCS Staging Bucket & Local Artifacts

```bash
# delete central staging bucket
gcloud storage rm -r gs://${PROJECT_GOVERNANCE}-shared-staging

# remove local configuration manifests and environment files
rm -rf cfg/ *.env
```

This concludes the cleanup portion... next on to the *Conclusion*!

---

## Conclusion
Duration: 00:00

Congratulations! You have successfully built, deployed, and governed a
multi-project Agent-to-Agent (A2A) architecture on Google Cloud across three
projects using Agent Gateway, Agent Registry, and Agent Identity.

### What you accomplished:
- **Centralized Egress Control:** Deployed a central Agent Gateway (`centralized-agw`) in `AGENT_TO_ANYWHERE` mode with IAP Service Extension authorization (`REQUEST_AUTHZ`).
- **Foundational API Governance:** Registered `core-gapi-services` in Central Agent Registry and authorized `roles/iap.egressor` across all 3 project `principalSet`s (`PROJECT_GOVERNANCE`, `PROJECT_CONCIERGE`, and `PROJECT_SELLERS`).
- **Cross-Project IAM Delegation:** Configured least-privilege custom role `ar_agw_cross_project_sa` to allow spoke Vertex AI Service Agents to discover and bind to the central gateway across project boundaries.
- **Cross-Project Agent Deployments:** Deployed the Purchasing Concierge in `PROJECT_CONCIERGE` and Seller Agents in `PROJECT_SELLERS` with `agentGatewayConfig` and `AGENT_IDENTITY` (SPIFFE).
- **Dynamic Auto-Discovery:** Implemented dynamic REST API autodiscovery from the Purchasing Concierge, eliminating hardcoded agent IDs, project numbers, and URLs.
- **Enforced Real-Time IAP Governance:**
  - Enforced a **Default Deny** security posture with `roles/iap.egressor` on individual Agent Registry resources.
  - Verified initial `HTTP 403 Forbidden` policy block on unauthorized pizza orders in Vertex AI Playground and audited `GRANTED: False` events in Cloud Logging.
  - Dynamically granted egress access to `pizza-seller-agent` and validated immediate `200 OK` order approval without redeploying agent containers.
- **Dependency-Ordered Teardown:** Cleaned up all runtime reasoning engines, registry services, gateway security policies, cross-project IAM bindings, and staging storage.

### Key Architectural Takeaways

| Architectural Pillar | Implementation in this Codelab | Enterprise Impact |
| :--- | :--- | :--- |
| **Separation of Concerns** | Central IT manages `PROJECT_GOVERNANCE` (Gateway, Registry, IAM), while domain teams own `PROJECT_CONCIERGE` and `PROJECT_SELLERS`. | Developers build agents without managing complex VPC topologies or egress infrastructure. SecOps maintains full control. |
| **Zero-Trust Machine Identity** | Vertex AI automatically mints cryptographically attested SPIFFE IDs (`principal://...`) evaluated by IAP. | Eliminates long-lived service account keys and enables granular agent-to-agent least-privilege access. |
| **Dynamic Service Discovery** | Purchasing Concierge queries Central Agent Registry via REST API at runtime. | Eliminates brittle hardcoded endpoints, allowing worker agents to be upgraded or redeployed independently. |
| **Live Policy Enforcement** | Modifying `roles/iap.egressor` on Agent Registry resources in `PROJECT_GOVERNANCE` takes effect immediately. | Access permissions can be granted, audited, or revoked in real time without downtime or container restarts. |

### Production Evolution & Next Steps
When moving this architecture into an enterprise production environment, consider the following enhancements:
- **Private Network Isolation with PSC-I:** Deploy Agent Gateway with [Private Service Connect Interfaces (PSC-I)][10-07] attached to a Shared VPC to eliminate public egress and enforce private enterprise perimeter security.
- **Payload Inspection with Model Armor:** Attach [Model Armor][10-06] filters to the Agent Gateway to inspect prompt and response payloads in real time for prompt injection, jailbreaks, and sensitive data protection (PII/DLP).
- **Enterprise MCP Server Catalog:** Register [Model Context Protocol (MCP)][10-08] tool servers running on [Cloud Run][10-09] or [Google Kubernetes Engine (GKE)][10-10] into the [Central Agent Registry][10-05] to expose vetted enterprise databases and APIs.

![cosmopup](img/cosmopup.jpg)

*Cosmopup says: "Agents are great—they do all the cross-project work while I focus on my primary objective: napping!"*

### What's next?
- [Gemini Enterprise Agent Platform Overview][10-01]
- [Configure and Deploy Agent Gateway with Agent Runtime][10-02]
- [Agent Identity & SPIFFE Attestation Deep Dive][10-03]

### Further reading & Documentation
- [Agent Gateway Architecture & Egress Governance][10-04]
- [Agent Registry Service Catalog Overview][10-05]
- [Model Armor Guardrails & Sensitive Data Protection][10-06]
- [Private Service Connect Interfaces (PSC-I) with Agent Gateway][10-07]
- [Model Context Protocol (MCP) Integration with Agent Runtime][10-08]
- [Deploy Containerized Tool Backends on Cloud Run][10-09]
- [Google Kubernetes Engine (GKE) Overview][10-10]

[10-01]: https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/overview
[10-02]: https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/deploy-gateway
[10-03]: https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/agent-identity
[10-04]: https://cloud.google.com/service-extensions/docs/configure-authz-iap
[10-05]: https://cloud.google.com/agent-registry/docs/overview
[10-06]: https://cloud.google.com/model-armor/docs/overview
[10-07]: https://cloud.google.com/vpc/docs/about-private-service-connect-interfaces
[10-08]: https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/mcp
[10-09]: https://cloud.google.com/run/docs
[10-10]: https://cloud.google.com/kubernetes-engine/docs
