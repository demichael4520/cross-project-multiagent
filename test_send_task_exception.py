import vertexai
from vertexai.preview import reasoning_engines

def main():
    project = "deepakmichael-svc3"
    location = "us-central1"
    vertexai.init(project=project, location=location)

    concierge_id = "projects/933480738993/locations/us-central1/reasoningEngines/5499019939589128192"
    remote_app = reasoning_engines.ReasoningEngine(concierge_id)
    
    res = remote_app.query(input={"input": "Execute send_task(agent_name='burger_seller_agent', task='order 1 burger') and give me the exact return value.", "user_id": "test_user"})
    print("Response:", res)

if __name__ == "__main__":
    main()
