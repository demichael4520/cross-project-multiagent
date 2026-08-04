import os
import google.auth
import google.auth.transport.requests
import requests

def main():
    location = "us-central1"
    burger_id = "projects/933480738993/locations/us-central1/reasoningEngines/6363711068044263424"
    
    credentials, proj = google.auth.default(
        scopes=['https://www.googleapis.com/auth/cloud-platform']
    )
    auth_req = google.auth.transport.requests.Request()
    credentials.refresh(auth_req)
    
    url = f"https://{location}-aiplatform.googleapis.com/v1beta1/{burger_id}:query"
    headers = {
        "Authorization": f"Bearer {credentials.token}",
        "Content-Type": "application/json",
    }
    payload = {
        "input": {
            "message": "I would like to order 1 Classic Cheeseburger please.",
            "user_id": "test_user"
        }
    }
    
    resp = requests.post(url, headers=headers, json=payload)
    print("Status:", resp.status_code)
    print("Body:", resp.text)

if __name__ == "__main__":
    main()
