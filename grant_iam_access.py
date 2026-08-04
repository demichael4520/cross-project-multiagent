from google.cloud.aiplatform_v1 import ReasoningEngineServiceClient

def main():
    client = ReasoningEngineServiceClient(client_options={'api_endpoint': 'us-central1-aiplatform.googleapis.com'})
    
    seller_engines = [
        "projects/933480738993/locations/us-central1/reasoningEngines/446614476377030656", # burger
        "projects/933480738993/locations/us-central1/reasoningEngines/2684903491180167168", # pizza
    ]
    
    concierge_principal = "principal://agents.global.org-1015654926499.system.id.goog/resources/aiplatform/projects/933480738993/locations/us-central1/reasoningEngines/7629011457102839808"

    for name in seller_engines:
        print(f"Getting IAM policy for {name}...")
        policy = client.get_iam_policy({"resource": name})
        
        updated = False
        for binding in policy.bindings:
            if binding.role in ["roles/aiplatform.agentContextEditor", "roles/aiplatform.viewer", "roles/aiplatform.admin"]:
                if concierge_principal not in binding.members:
                    binding.members.append(concierge_principal)
                    updated = True
        
        if updated:
            print(f"Setting IAM policy for {name}...")
            updated_policy = client.set_iam_policy({"resource": name, "policy": policy})
            print(f"Successfully updated IAM policy for {name}")
        else:
            print(f"Concierge principal already present or role not found for {name}")

if __name__ == "__main__":
    main()
