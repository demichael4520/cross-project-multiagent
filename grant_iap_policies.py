import subprocess
import json
import vertexai
from google.cloud.aiplatform_v1 import ReasoningEngineServiceClient
from google.adk.integrations.agent_registry import AgentRegistry

def main():
    project = "deepakmichael-svc3"
    location = "us-central1"
    vertexai.init(project=project, location=location)

    client = ReasoningEngineServiceClient(client_options={'api_endpoint': f'{location}-aiplatform.googleapis.com'})
    parent = f"projects/{project}/locations/{location}"

    # Find latest concierge reasoning engine
    response = client.list_reasoning_engines(parent=parent)
    engines = list(response.reasoning_engines)
    engines.sort(key=lambda x: x.create_time, reverse=True)

    concierge_id = None
    for eng in engines:
        if "concierge" in eng.display_name:
            concierge_id = eng.name
            break

    if not concierge_id:
        print("Error: Concierge reasoning engine not found.")
        return

    concierge_principal = f"principal://agents.global.org-1015654926499.system.id.goog/resources/aiplatform/{concierge_id}"
    print(f"Concierge Principal: {concierge_principal}")

    # Query Agent Registry to get seller agent endpoint IDs
    registry = AgentRegistry(project_id=project, location=location)
    agents_resp = registry.list_agents()
    
    seller_endpoint_ids = []
    for agent in agents_resp.get("agents", []):
        display_name = agent.get("displayName", "")
        if "burger" in display_name.lower() or "pizza" in display_name.lower():
            # agent['name'] is projects/.../agents/agentregistry-...
            full_name = agent.get("name")
            endpoint_id = full_name.split("/")[-1]
            seller_endpoint_ids.append(endpoint_id)
            print(f"Found seller agent {display_name} with endpoint ID: {endpoint_id}")

    for endpoint_id in seller_endpoint_ids:
        print(f"Fetching IAP policy for endpoint {endpoint_id}...")
        p_res = subprocess.run([
            "gcloud", "beta", "iap", "web", "get-iam-policy",
            f"--project={project}",
            "--resource-type=agent-registry",
            f"--agent={endpoint_id}",
            f"--region={location}",
            "--format=json"
        ], capture_output=True, text=True)

        if p_res.returncode != 0:
            print(f"Warning getting policy for {endpoint_id}: {p_res.stderr}")
            continue

        try:
            policy = json.loads(p_res.stdout)
        except:
            policy = {"bindings": []}

        if "bindings" not in policy:
            policy["bindings"] = []

        found = False
        for b in policy["bindings"]:
            if b.get("role") == "roles/iap.egressor":
                if concierge_principal not in b.get("members", []):
                    b.setdefault("members", []).append(concierge_principal)
                found = True
        if not found:
            policy["bindings"].append({
                "role": "roles/iap.egressor",
                "members": [concierge_principal]
            })

        with open("temp_policy.json", "w") as f:
            json.dump(policy, f, indent=2)

        print(f"Setting IAP policy for endpoint {endpoint_id}...")
        s_res = subprocess.run([
            "gcloud", "beta", "iap", "web", "set-iam-policy", "temp_policy.json",
            f"--project={project}",
            "--resource-type=agent-registry",
            f"--agent={endpoint_id}",
            f"--region={location}",
            "--quiet"
        ], capture_output=True, text=True)

        if s_res.returncode == 0:
            print(f"Successfully updated IAP policy for endpoint {endpoint_id}")
        else:
            print(f"Failed to update IAP policy: {s_res.stderr}")

    print("All seller agent IAP policies updated successfully!")

if __name__ == "__main__":
    main()
