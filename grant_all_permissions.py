import os
import vertexai
from google.cloud.aiplatform_v1 import ReasoningEngineServiceClient

def main():
    project = "deepakmichael-svc3"
    location = "us-central1"
    vertexai.init(project=project, location=location)

    client = ReasoningEngineServiceClient(client_options={'api_endpoint': f'{location}-aiplatform.googleapis.com'})
    parent = f"projects/{project}/locations/{location}"

    # List reasoning engines
    response = client.list_reasoning_engines(parent=parent)
    engines = list(response.reasoning_engines)
    engines.sort(key=lambda x: x.create_time, reverse=True)

    concierge_id = None
    burger_id = None
    pizza_id = None

    for eng in engines:
        if "concierge" in eng.display_name and not concierge_id:
            concierge_id = eng.name
        elif "burger" in eng.display_name and not burger_id:
            burger_id = eng.name
        elif "pizza" in eng.display_name and not pizza_id:
            pizza_id = eng.name

    print(f"Found Concierge: {concierge_id}")
    print(f"Found Burger Agent: {burger_id}")
    print(f"Found Pizza Agent: {pizza_id}")

    if not concierge_id or not burger_id or not pizza_id:
        print("Error: Could not find all required reasoning engines.")
        return

    concierge_principal = f"principal://agents.global.org-1015654926499.system.id.goog/resources/aiplatform/{concierge_id}"
    print(f"Concierge Principal: {concierge_principal}")

    seller_engines = [burger_id, pizza_id]

    for name in seller_engines:
        print(f"Getting IAM policy for {name}...")
        policy = client.get_iam_policy({"resource": name})
        
        roles_to_add = [
            "roles/aiplatform.agentContextEditor",
            "roles/aiplatform.user",
        ]
        
        updated = False
        for role in roles_to_add:
            found = False
            for binding in policy.bindings:
                if binding.role == role:
                    found = True
                    if concierge_principal not in binding.members:
                        binding.members.append(concierge_principal)
                        updated = True
            if not found:
                from google.iam.v1.policy_pb2 import Binding
                b = Binding(role=role, members=[concierge_principal])
                policy.bindings.append(b)
                updated = True

        if updated:
            print(f"Setting IAM policy for {name}...")
            updated_policy = client.set_iam_policy({"resource": name, "policy": policy})
            print(f"Successfully updated IAM policy for {name}")
        else:
            print(f"Concierge principal already present for {name}")

    print("IAM permissions granted successfully!")

if __name__ == "__main__":
    main()
