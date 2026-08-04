import vertexai
from vertexai.preview import reasoning_engines

def main():
    project = "deepakmichael-svc3"
    location = "us-central1"
    vertexai.init(project=project, location=location)

    burger_agent_id = "projects/933480738993/locations/us-central1/reasoningEngines/446614476377030656"
    remote_agent = reasoning_engines.ReasoningEngine(burger_agent_id)

    print("Testing Burger Agent with prompt: 'I would like to order 1 Classic Cheeseburger please.'")
    response = remote_agent.query(input="I would like to order 1 Classic Cheeseburger please.")
    print("Response from Burger Agent:", response)

if __name__ == "__main__":
    main()
