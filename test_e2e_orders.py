import os
import time
import vertexai
from vertexai.preview import reasoning_engines
from dotenv import load_dotenv

load_dotenv("seller_agents.env")
load_dotenv()

def main():
    project = "deepakmichael-svc3"
    location = "us-central1"
    vertexai.init(project=project, location=location)

    concierge_id = "projects/933480738993/locations/us-central1/reasoningEngines/8048972122355138560"
    remote_app = reasoning_engines.ReasoningEngine(concierge_id)

    prompts = [
        "I want to buy 1 Classic Cheeseburger please!",
        "I want to order 1 Margherita pizza please!"
    ]

    for prompt in prompts:
        print(f"\nTesting Purchasing Concierge with prompt: '{prompt}'")
        success = False
        attempt = 1
        while not success and attempt <= 10:
            try:
                print(f"Attempt {attempt}...")
                response = remote_app.query(input=prompt)
                print("Response:", response)
                output_text = str(response.get("output", ""))
                if "error" not in output_text.lower() and "apologize" not in output_text.lower() and len(output_text) > 10:
                    success = True
                    print(f"Successfully processed: {prompt}")
                else:
                    print("Received error response, retrying in 5 seconds...")
                    time.sleep(5)
            except Exception as e:
                print(f"Exception encountered: {e}, retrying in 5 seconds...")
                time.sleep(5)
            attempt += 1

        if not success:
            print(f"Failed to get successful response for prompt: {prompt} after 10 attempts.")

if __name__ == "__main__":
    main()
