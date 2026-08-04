import subprocess
import json

project_id = "deepakmichael-svc3"
region = "us-central1"
concierge_principal = "principal://agents.global.org-1015654926499.system.id.goog/resources/aiplatform/projects/933480738993/locations/us-central1/reasoningEngines/8571389679130116096"

def main():
    print("Listing agents from Agent Registry...")
    res = subprocess.run([
        "gcloud", "beta", "iap", "web", "list-agents",
        f"--project={project_id}",
        f"--region={region}",
        "--format=json"
    ], capture_output=True, text=True)
    
    if res.returncode != 0:
        print(f"Error listing agents: {res.stderr}")
        return

    try:
        agents = json.loads(res.stdout)
    except Exception as e:
        print(f"Failed to parse agents json: {e}, output: {res.stdout}")
        return

    print(f"Found {len(agents)} agents in registry.")
    for agent in agents:
        agent_name = agent.get("name") # e.g. agentregistry-00000000-0000-0000-...
        display_name = agent.get("displayName")
        print(f"Granting egress to agent {display_name} ({agent_name})...")
        
        # Get IAM policy
        p_res = subprocess.run([
            "gcloud", "beta", "iap", "web", "get-iam-policy",
            f"--project={project_id}",
            "--resource-type=agent-registry",
            f"--agent={agent_name}",
            f"--region={region}",
            "--format=json"
        ], capture_output=True, text=True)
        
        if p_res.returncode != 0:
            print(f"  Warning getting policy: {p_res.stderr}")
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
            
        s_res = subprocess.run([
            "gcloud", "beta", "iap", "web", "set-iam-policy", "temp_policy.json",
            f"--project={project_id}",
            "--resource-type=agent-registry",
            f"--agent={agent_name}",
            f"--region={region}",
            "--quiet"
        ], capture_output=True, text=True)
        
        if s_res.returncode == 0:
            print(f"  Successfully updated policy for {agent_name}")
        else:
            print(f"  Failed to update policy: {s_res.stderr}")

if __name__ == "__main__":
    main()
