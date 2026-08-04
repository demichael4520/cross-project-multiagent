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
    region = "us-central1"
    
    url = f"https://agentregistry.googleapis.com/v1alpha/projects/{project_id}/locations/{region}/endpoints"
    print(f"Listing endpoints from: {url}")
    
    r = requests.get(url, headers=headers)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(json.dumps(data, indent=2))
        endpoints = data.get("endpoints", [])
        for ep in endpoints:
            print("Endpoint:", ep.get("name"))
    else:
        print(r.text)

if __name__ == "__main__":
    main()
