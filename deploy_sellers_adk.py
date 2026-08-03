#!/usr/bin/env python3
import argparse
import os
import vertexai
from vertexai import agent_engines
from vertexai import types
from dotenv import load_dotenv

load_dotenv()

def main():
    parser = argparse.ArgumentParser(description="Deploy Remote Seller Agents to Agent Runtime with Agent Identity")
    parser.add_argument("--project", required=True, help="Google Cloud Project ID")
    parser.add_argument("--region", default="us-central1", help="Vertex AI Region")
    parser.add_argument("--staging-bucket", help="GCS bucket for staging (default: gs://PROJECT_ID-staging)")
    parser.add_argument("--enable-agent-identity", action="store_true", help="Enable Agent Identity for seller agents")
    args = parser.parse_args()

    staging_bucket = args.staging_bucket or f"gs://{args.project}-staging"
    if not staging_bucket.startswith("gs://"):
        staging_bucket = f"gs://{staging_bucket}"

    vertexai.init(
        project=args.project,
        location=args.region,
        staging_bucket=staging_bucket,
    )

    class AutoCreateSessionAdkApp(agent_engines.AdkApp):
        def set_up(self):
            print("AutoCreateSessionAdkApp.set_up() called!")
            super().set_up()
            if "runner" in self._tmpl_attrs:
                self._tmpl_attrs["runner"].auto_create_session = True
                print("Set runner.auto_create_session = True")
            if "in_memory_runner" in self._tmpl_attrs:
                self._tmpl_attrs["in_memory_runner"].auto_create_session = True
                print("Set in_memory_runner.auto_create_session = True")

    from remote_seller_agents.burger_agent.agent_adk import burger_agent as burger_adk_agent
    from remote_seller_agents.pizza_agent.agent_adk import pizza_agent as pizza_adk_agent

    identity_config = {"identity_type": types.IdentityType.AGENT_IDENTITY} if args.enable_agent_identity else {}

    # Deploy Burger Agent
    print("Deploying Burger Agent to Agent Runtime...")
    burger_app = AutoCreateSessionAdkApp(
        agent=burger_adk_agent,
        env_vars={
            "GOOGLE_GENAI_USE_VERTEXAI": "true",
            "GOOGLE_CLOUD_PROJECT": args.project,
            "GOOGLE_CLOUD_LOCATION": args.region,
        }
    )
    
    burger_deploy_config = {
        "display_name": "burger-seller-agent-adk",
        "requirements": [
            "google-cloud-aiplatform[agent_engines]>=1.149.0",
            "google-adk[a2a,agent-identity]==1.34.0",
        ],
        "extra_packages": ["./remote_seller_agents"],
        **identity_config,
    }
    
    deployed_burger = agent_engines.create(
        agent_engine=burger_app,
        config=burger_deploy_config,
    )
    print(f"Burger Agent deployed: {deployed_burger.resource_name}")

    # Deploy Pizza Agent
    print("Deploying Pizza Agent to Agent Runtime...")
    pizza_app = AutoCreateSessionAdkApp(
        agent=pizza_adk_agent,
        env_vars={
            "GOOGLE_GENAI_USE_VERTEXAI": "true",
            "GOOGLE_CLOUD_PROJECT": args.project,
            "GOOGLE_CLOUD_LOCATION": args.region,
        }
    )
    
    pizza_deploy_config = {
        "display_name": "pizza-seller-agent-adk",
        "requirements": [
            "google-cloud-aiplatform[agent_engines]>=1.149.0",
            "google-adk[a2a,agent-identity]==1.34.0",
        ],
        "extra_packages": ["./remote_seller_agents"],
        **identity_config,
    }
    
    deployed_pizza = agent_engines.create(
        agent_engine=pizza_app,
        config=pizza_deploy_config,
    )
    print(f"Pizza Agent deployed: {deployed_pizza.resource_name}")

    with open("seller_agents.env", "w") as f:
        f.write(f"BURGER_SELLER_AGENT_ID={deployed_burger.name}\n")
        f.write(f"PIZZA_SELLER_AGENT_ID={deployed_pizza.name}\n")
    print("Saved agent IDs to seller_agents.env")

if __name__ == "__main__":
    main()
