import subprocess
import json

agents = [
    "agentregistry-00000000-0000-0000-ff71-ab64fdbdac70", # pizza
    "agentregistry-00000000-0000-0000-71c9-adc4aa022fe7", # burger
]

concierge_principal = "principal://agents.global.org-1015654926499.system.id.goog/resources/aiplatform/projects/933480738993/locations/us-central1/reasoningEngines/7629011457102839808"

for agent in agents:
    print(f"Fetching policy for agent {agent}...")
    res = subprocess.run(
        [
            "gcloud", "beta", "iap", "web", "get-iam-policy",
            "--project=deepakmichael-svc3",
            "--resource-type=agent-registry",
            f"--agent={agent}",
            "--region=us-central1",
            "--format=json"
        ],
        capture_output=True,
        text=True,
        check=True
    )
    policy = json.loads(res.stdout)
    
    # Ensure bindings exist
    if "bindings" not in policy:
        policy["bindings"] = []
        
    # Check if concierge principal is already in iap.egressor
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
        
    # Write temp policy file
    with open("temp_policy.json", "w") as f:
        json.dump(policy, f, indent=2)
        
    print(f"Setting policy for agent {agent}...")
    subprocess.run(
        [
            "gcloud", "beta", "iap", "web", "set-iam-policy", "temp_policy.json",
            "--project=deepakmichael-svc3",
            "--resource-type=agent-registry",
            f"--agent={agent}",
            "--region=us-central1",
            "--quiet"
        ],
        check=True
    )
    print(f"Successfully updated IAM policy for {agent}")

print("All agent IAP policies updated successfully!")
