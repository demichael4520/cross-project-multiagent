import os
import vertexai
from vertexai.preview import reasoning_engines
from dotenv import load_dotenv

load_dotenv("seller_agents.env")
load_dotenv()

def main():
    project = "deepakmichael-svc3"
    location = "us-central1"
    vertexai.init(project=project, location=location)

    concierge_id = "projects/933480738993/locations/us-central1/reasoningEngines/166757980782460928"
    remote_app = reasoning_engines.ReasoningEngine(concierge_id)
    
    print("Testing Purchasing Concierge query with playground dict input...")
    response = remote_app.query(input={"input": "I want to order 4 cheeseburgers!", "user_id": "terminal_user"})
    print("Response:", response)

if __name__ == "__main__":
    main()
