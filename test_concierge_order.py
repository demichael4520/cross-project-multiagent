import vertexai
from vertexai.preview import reasoning_engines

vertexai.init(project="deepakmichaelprod", location="us-central1")
engine_name = "projects/114740196141/locations/us-central1/reasoningEngines/4485309801198256128"
print(f"Connecting to concierge reasoning engine: {engine_name}")

remote_app = reasoning_engines.ReasoningEngine(engine_name)
print("Sending test query to concierge to order burger and pizza...")
response = remote_app.query(input="I confirm ordering 1 Classic Cheeseburger for IDR 85K from burger seller agent and 1 Pepperoni Pizza for IDR 140K from pizza seller agent. Please place both orders now.")
print("CONCIERGE RESPONSE:", response)
