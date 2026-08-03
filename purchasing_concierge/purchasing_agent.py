import json
import uuid
from typing import Dict
import os

from google.adk import Agent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.tool_context import ToolContext

class PurchasingAgent:
    """The purchasing agent.

    This is the agent responsible for choosing which remote seller agents to send
    tasks to and coordinate their work.
    """

    def __init__(
        self,
        agent_ids: Dict[str, str],
    ):
        self.agent_ids = agent_ids
        self.agents = ""
        self.a2a_client_init_status = False
        # Static definitions for description in prompt
        self.agent_metadata = {
            "burger_seller_agent": {
                "name": "burger_seller_agent",
                "description": "Helps with understanding burger menu, prices, and creating burger orders. Menu: Classic Cheeseburger (85K), Double Cheeseburger (110K), Spicy Chicken Burger (80K), Spicy Cajun Burger (85K)."
            },
            "pizza_seller_agent": {
                "name": "pizza_seller_agent",
                "description": "Specialized agent for ordering pizzas. Supports bbq, thai, mexican, indian, and italian variants. Menu: Margherita (100K), Pepperoni (140K), Hawaiian (110K), Veggie (100K), BBQ Chicken (130K)."
            }
        }

    def create_agent(self) -> Agent:
        return Agent(
            model="gemini-2.5-flash",
            name="purchasing_agent",
            instruction=self.root_instruction,
            before_model_callback=self.before_model_callback,
            before_agent_callback=self.before_agent_callback,
            description=(
                "This purchasing agent orchestrates the decomposition of the user purchase request into"
                " tasks that can be performed by the seller agents."
            ),
            tools=[
                self.send_task,
            ],
        )

    def root_instruction(self, context: ReadonlyContext) -> str:
        current_agent = self.check_active_agent(context)
        return f"""You are an expert purchasing delegator that can delegate the user product inquiry and purchase request to the
appropriate seller remote agents.

Execution:
- For actionable tasks, you can use `send_task` to assign tasks to remote agents to perform.
- When the remote agent is repeatedly asking for user confirmation, assume that the remote agent doesn't have access to user's conversation context. 
    So improve the task description to include all the necessary information related to that agent
- Never ask user permission when you want to connect with remote agents. If you need to make connection with multiple remote agents, directly
    connect with them without asking user permission or asking user preference
- Always show the detailed response information from the seller agent and propagate it properly to the user. 
- If the remote seller is asking for confirmation, rely the confirmation question with proper and necessary information to the user if the user haven't do so. 
- If the user already confirmed the related order in the past conversation history, you can confirm on behalf of the user
- Do not give irrelevant context to remote seller agent. For example, ordered pizza item is not relevant for the burger seller agent
- Never ask order confirmation to the remote seller agent 

Please rely on tools to address the request, and don't make up the response. If you are not sure, please ask the user for more details.
Focus on the most recent parts of the conversation primarily.

If there is an active agent, send the request to that agent with the update task tool.

Agents:
{self.agents}

Current active seller agent: {current_agent["active_agent"]}
"""

    def check_active_agent(self, context: ReadonlyContext):
        state = context.state
        if (
            "session_id" in state
            and "session_active" in state
            and state["session_active"]
            and "active_agent" in state
        ):
            return {"active_agent": f"{state['active_agent']}"}
        return {"active_agent": "None"}

    async def before_agent_callback(self, callback_context: CallbackContext):
        if not self.a2a_client_init_status:
            project = os.getenv("GOOGLE_CLOUD_PROJECT", "deepakmichael-svc3")
            location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
            
            try:
                from google.adk.integrations.agent_registry import AgentRegistry
                registry = AgentRegistry(project_id=project, location=location)
                response = registry.list_agents()
                
                discovered_agents = {}
                for agent in response.get("agents", []):
                    display_name = agent.get("displayName")
                    runtime_ref = agent.get("adkAgentDefinition", {}).get("provisionedReasoningEngine", {}).get("reasoningEngine")
                    if display_name and runtime_ref:
                        discovered_agents[display_name] = runtime_ref
                        if "burger" in display_name.lower():
                            discovered_agents["burger_seller_agent"] = runtime_ref
                        elif "pizza" in display_name.lower():
                            discovered_agents["pizza_seller_agent"] = runtime_ref

                if discovered_agents:
                    self.agent_ids.update(discovered_agents)
            except Exception as e:
                print(f"Warning: Failed to query Agent Registry in project {project}: {e}")

            agent_info = []
            for name, meta in self.agent_metadata.items():
                if name in self.agent_ids:
                    agent_info.append(json.dumps({"name": meta["name"], "description": meta["description"]}))
            self.agents = "\n".join(agent_info)
            self.a2a_client_init_status = True

    async def before_model_callback(
        self, callback_context: CallbackContext, llm_request
    ):
        state = callback_context.state
        if "session_active" not in state or not state["session_active"]:
            if "session_id" not in state:
                state["session_id"] = str(uuid.uuid4())
            state["session_active"] = True

    def send_task(self, agent_name: str, task: str, tool_context: ToolContext) -> str:
        """Sends a task to remote seller agent.

        This will send a message to the remote agent named agent_name.

        Args:
            agent_name: The name of the agent to send the task to. Must be one of: burger_seller_agent, pizza_seller_agent.
            task: The comprehensive conversation context summary and goal to be achieved regarding user inquiry and purchase request.
        """
        if agent_name not in self.agent_ids:
            return f"Error: Agent {agent_name} not found"
            
        state = tool_context.state
        state["active_agent"] = agent_name
        
        agent_id = self.agent_ids[agent_name]
        session_id = state.get("session_id", "default_session")

        import vertexai
        from vertexai.preview import reasoning_engines
        
        # Initialize vertexai with default credentials if needed, but it should inherit from environment
        project = os.getenv("GOOGLE_CLOUD_PROJECT")
        location = os.getenv("GOOGLE_CLOUD_LOCATION")
        vertexai.init(project=project, location=location)

        import vertexai
        from vertexai.preview import reasoning_engines
        from google.cloud.aiplatform_v1beta1 import types as aip_types
        from vertexai.reasoning_engines import _utils

        try:
            print(f"Calling remote agent {agent_name} (ID: {agent_id}) with task: {task}")
            engine = reasoning_engines.ReasoningEngine(agent_id)
            execution_client = engine.execution_api_client
            
            input_data = {
                "message": task,
                "user_id": "purchasing_agent",
                "session_id": session_id
            }

            request = aip_types.StreamQueryReasoningEngineRequest(
                name=engine.resource_name,
                input=input_data,
                class_method="stream_query"
            )
            
            response_stream = execution_client.stream_query_reasoning_engine(request=request)
            
            collected_text = []
            for chunk in response_stream:
                try:
                    for parsed_json in _utils.yield_parsed_json(chunk):
                        if parsed_json is not None and "content" in parsed_json:
                            parts = parsed_json["content"].get("parts", [])
                            for part in parts:
                                if "text" in part:
                                    collected_text.append(part["text"])
                except Exception as parse_err:
                    print(f"Error parsing chunk: {parse_err}")
                    
            if collected_text:
                response_text = "".join(collected_text)
                print(f"Response from {agent_name}: {response_text}")
                return response_text
            return "Failed to get response from agent."
        except Exception as e:
            print(f"Error calling remote agent {agent_name}: {e}")
            return f"Error calling agent {agent_name}: {e}"
