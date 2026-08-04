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

    from purchasing_concierge.purchasing_agent import PurchasingAgent
    agent = PurchasingAgent(agent_ids={
        "burger_seller_agent": os.getenv("BURGER_SELLER_AGENT_ID")
    })
    
    # Mock tool context
    class MockContext:
        state = {}
        
    res = agent.send_task("burger_seller_agent", "I want to order 1 Classic Cheeseburger please.", MockContext())
    print("Result of send_task:", res)

if __name__ == "__main__":
    main()
