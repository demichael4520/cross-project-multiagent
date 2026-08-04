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

    burger_agent_id = os.getenv("BURGER_SELLER_AGENT_ID")
    print(f"Testing engine.query on burger agent ({burger_agent_id})...")
    burger_engine = reasoning_engines.ReasoningEngine(burger_agent_id)
    
    try:
        res = burger_engine.query(message="I want to order 1 cheeseburger", user_id="test_user")
        print("Result from engine.query:", res)
    except Exception as e:
        print("Error with engine.query(message=...):", e)
        try:
            res = burger_engine.query(input={"message": "I want to order 1 cheeseburger", "user_id": "test_user"})
            print("Result from engine.query(input=...):", res)
        except Exception as e2:
            print("Error with engine.query(input=...):", e2)

if __name__ == "__main__":
    main()
