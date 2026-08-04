import os
import vertexai
from vertexai.preview import reasoning_engines
from google.adk.integrations.agent_registry import AgentRegistry

def main():
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "deepakmichael-svc3")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    vertexai.init(project=project, location=location)

    print(f"=== Verifying Playground & Agent Registry Setup for Project: {project} ({location}) ===")

    print("\n1. Listing Deployed Reasoning Engines:")
    try:
        engines = reasoning_engines.ReasoningEngine.list()
        for e in engines:
            print(f"  - [{e.name}] {e.display_name}")
    except Exception as ex:
        print(f"  Error listing reasoning engines: {ex}")

    print("\n2. Querying Agent Registry Catalog:")
    try:
        registry = AgentRegistry(project_id=project, location=location)
        agents_response = registry.list_agents()
        agents = agents_response.get("agents", [])
        print(f"  Found {len(agents)} registered agents:")
        for agent in agents:
            print(f"  - Name: {agent.get('displayName')}")
            print(f"    Resource: {agent.get('name')}")
            protos = agent.get("protocols", [])
            print(f"    Protocols/Interfaces: {len(protos)}")
    except Exception as ex:
        print(f"  Error querying Agent Registry: {ex}")

    print("\n=== Verification Complete ===")

if __name__ == "__main__":
    main()
