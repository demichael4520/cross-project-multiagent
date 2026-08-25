#!/bin/bash
REGION="${REGION:-us-central1}"
TOKEN=$(gcloud auth application-default print-access-token)

echo "=== 1. Purchasing Concierge ($PROJECT_CONCIERGE) ==="
curl -s -X GET "https://${REGION}-aiplatform.googleapis.com/v1beta1/projects/${PROJECT_CONCIERGE}/locations/${REGION}/reasoningEngines/${CONCIERGE_ENGINE_ID}" \
-H "Authorization: Bearer ${TOKEN}" -H "Content-Type: application/json" \
| jq '{displayName: .displayName, identityType: .spec.identityType, effectiveIdentity: .spec.effectiveIdentity, agentGatewayConfig: .spec.deploymentSpec.agentGatewayConfig}'

echo "=== 2. Burger Agent ($PROJECT_SELLERS) ==="
curl -s -X GET "https://${REGION}-aiplatform.googleapis.com/v1beta1/projects/${PROJECT_SELLERS}/locations/${REGION}/reasoningEngines/${BURGER_ENGINE_ID}" \
-H "Authorization: Bearer ${TOKEN}" -H "Content-Type: application/json" \
| jq '{displayName: .displayName, identityType: .spec.identityType, effectiveIdentity: .spec.effectiveIdentity, agentGatewayConfig: .spec.deploymentSpec.agentGatewayConfig}'

echo "=== 3. Pizza Agent ($PROJECT_SELLERS) ==="
curl -s -X GET "https://${REGION}-aiplatform.googleapis.com/v1beta1/projects/${PROJECT_SELLERS}/locations/${REGION}/reasoningEngines/${PIZZA_ENGINE_ID}" \
-H "Authorization: Bearer ${TOKEN}" -H "Content-Type: application/json" \
| jq '{displayName: .displayName, identityType: .spec.identityType, effectiveIdentity: .spec.effectiveIdentity, agentGatewayConfig: .spec.deploymentSpec.agentGatewayConfig}'
