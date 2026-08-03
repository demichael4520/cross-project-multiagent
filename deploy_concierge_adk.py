#!/usr/bin/env python3
import argparse
import os
import vertexai
from vertexai import agent_engines
from vertexai import types
from dotenv import load_dotenv

load_dotenv("seller_agents.env")
load_dotenv()

def main():
    parser = argparse.ArgumentParser(description="Deploy Purchasing Concierge Agent to Agent Runtime with Agent Identity")
    parser.add_argument("--project", required=True, help="Google Cloud Project ID")
    parser.add_argument("--region", default="us-central1", help="Vertex AI Region")
    parser.add_argument("--staging-bucket", help="GCS bucket for staging (default: gs://PROJECT_ID-staging)")
    parser.add_argument("--enable-agent-identity", action="store_true", help="Enable Agent Identity for concierge agent")
    args = parser.parse_args()

    staging_bucket = args.staging_bucket or f"gs://{args.project}-staging"
    if not staging_bucket.startswith("gs://"):
        staging_bucket = f"gs://{staging_bucket}"

    vertexai.init(
        project=args.project,
        location=args.region,
        staging_bucket=staging_bucket,
    )

    from purchasing_concierge.agent import root_agent

    adk_app = agent_engines.AdkApp(
        agent=root_agent,
        env_vars={
            "GOOGLE_GENAI_USE_VERTEXAI": "true",
            "PIZZA_SELLER_AGENT_ID": os.environ.get("PIZZA_SELLER_AGENT_ID", ""),
            "BURGER_SELLER_AGENT_ID": os.environ.get("BURGER_SELLER_AGENT_ID", ""),
            "GOOGLE_CLOUD_PROJECT": args.project,
            "GOOGLE_CLOUD_LOCATION": args.region,
        }
    )

    class PlaygroundCompatibleAdkAgent:
        agent_framework = "google-adk"

        def __init__(self, app: agent_engines.AdkApp):
            self.app = app

        def set_up(self):
            self.app.set_up()

        def register_operations(self) -> dict[str, list[str]]:
            return {
                "": ["query"],
                "stream": ["stream_query"],
            }

        def _parse_args(self, input = None, user_id = None, session_id = None, **kwargs):
            kw_user_id = kwargs.pop("user_id", None)
            kw_userId = kwargs.pop("userId", None)
            user_id = user_id or kw_user_id or kw_userId

            kw_session_id = kwargs.pop("session_id", None)
            kw_sessionId = kwargs.pop("sessionId", None)
            session_id = session_id or kw_session_id or kw_sessionId

            kw_message = kwargs.pop("message", None)
            kw_input = kwargs.pop("input", None)
            if input is None:
                input = kw_message or kw_input

            if input is None:
                 raise ValueError("Either 'input' or 'message' must be provided")

            if isinstance(input, dict):
                if not input:
                    message = ""
                    effective_user_id = user_id or "console-tester-user"
                    effective_session_id = session_id
                else:
                    message = input.get("message")
                    if message is None:
                        message = input.get("input")
                    if message is None:
                        message = ""
                    else:
                        message = str(message)
                    
                    effective_user_id = user_id or input.get("user_id") or input.get("userId") or "console-tester-user"
                    effective_session_id = session_id or input.get("session_id") or input.get("sessionId")
            else:
                message = str(input)
                effective_user_id = user_id or "console-tester-user"
                effective_session_id = session_id
                
            return message, effective_user_id, effective_session_id, kwargs

        def query(self, input = None, user_id = None, session_id = None, **kwargs) -> dict:
            message, effective_user_id, effective_session_id, clean_kwargs = self._parse_args(input, user_id, session_id, **kwargs)
            final_text = ""
            for chunk in self.app.stream_query(message=message, user_id=effective_user_id, session_id=effective_session_id, **clean_kwargs):
                if isinstance(chunk, dict) and isinstance(chunk.get("content"), dict):
                    parts = chunk["content"].get("parts", [])
                    if isinstance(parts, list):
                        for part in parts:
                            if isinstance(part, dict) and "text" in part:
                                if not part.get("thought") and not part.get("raw_thought"):
                                    final_text += part["text"]
            return {"output": final_text}

        def stream_query(self, input = None, user_id = None, session_id = None, **kwargs):
            message, effective_user_id, effective_session_id, clean_kwargs = self._parse_args(input, user_id, session_id, **kwargs)
            for chunk in self.app.stream_query(message=message, user_id=effective_user_id, session_id=effective_session_id, **clean_kwargs):
                yield chunk

    playground_app = PlaygroundCompatibleAdkAgent(app=adk_app)

    identity_config = {"identity_type": types.IdentityType.AGENT_IDENTITY} if args.enable_agent_identity else {}

    print("Deploying Purchasing Concierge to Agent Runtime...")
    deploy_config = {
        "display_name": "purchasing-concierge-adk",
        "requirements": [
            "google-cloud-aiplatform[agent_engines]>=1.149.0",
            "google-adk[a2a,agent-identity]==1.34.0",
        ],
        "extra_packages": [
            "./purchasing_concierge",
        ],
        **identity_config,
    }

    deployed_concierge = agent_engines.create(
        agent_engine=playground_app,
        config=deploy_config,
    )

    print(f"Purchasing Concierge deployed: {deployed_concierge.resource_name}")
    print(f"Concierge ID: {deployed_concierge.name}")

if __name__ == "__main__":
    main()
