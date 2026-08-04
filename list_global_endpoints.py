import google.auth
import google.auth.transport.requests
import requests
import json

def main():
    credentials, project = google.auth.default()
    auth_request = google.auth.transport.requests.Request()
    credentials.refresh(auth_request)

    headers = {
        "Authorization": f"Bearer {credentials.token}",
        "Content-Type": "application/json"
    }

    project_id = "deepakmichael-svc3"
    
    for loc in ["us-central1", "global"]:
        url = f"https://agentregistry.googleapis.com/v1alpha/projects/{project_id}/locations/{loc}/endpoints"
        print(f"Listing endpoints from: {url}")
        r = requests.get(url, headers=headers)
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            for ep in data.get("endpoints", []):
                print(f"  Endpoint ID: {ep.get('name')}, DisplayName: {ep.get('displayName')}")
                for iface in ep.get("interfaces", []):
                    print(f"    - {iface.get('url')}")

if __name__ == "__main__":
    main()
