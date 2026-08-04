import subprocess
import json

project_id = "deepakmichael-svc3"
region = "us-central1"
concierge_principal = "principal://agents.global.org-1015654926499.system.id.goog/resources/aiplatform/projects/933480738993/locations/us-central1/reasoningEngines/7629011457102839808"
endpoint_id = "agentregistry-00000000-0000-0000-55a9-87c001002d4e"

def main():
    print(f"Granting egress to endpoint {endpoint_id}...")
    
    p_res = subprocess.run([
        "gcloud", "beta", "iap", "web", "get-iam-policy",
        f"--project={project_id}",
        "--resource-type=agent-registry",
        f"--endpoint={endpoint_id}",
        f"--region={region}",
        "--format=json"
    ], capture_output=True, text=True)
    
    if p_res.returncode != 0:
        print(f"Warning getting policy: {p_res.stderr}")
        return
        
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
        
    s_res = subprocess.run([
        "gcloud", "beta", "iap", "web", "set-iam-policy", "temp_policy.json",
        f"--project={project_id}",
        "--resource-type=agent-registry",
        f"--endpoint={endpoint_id}",
        f"--region={region}",
        "--quiet"
    ], capture_output=True, text=True)
    
    if s_res.returncode == 0:
        print(f"Successfully updated policy for core gapi endpoint {endpoint_id}")
    else:
        print(f"Failed to update policy: {s_res.stderr}")

if __name__ == "__main__":
    main()
