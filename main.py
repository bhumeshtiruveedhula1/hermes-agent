# main.py
import json
import pyttsx3
from colorama import init, Fore

from langchain_core.tools import tool
from prompt_toolkit import prompt
from prompt_toolkit.formatted_text import HTML

import agents
import tools_web
import tools_email

from core.memory import MemoryManager
from core.planner import PlannerAgent
from core.critic import CriticAgent
from core.preferences import detect_preferences
from core.summarizer import MemorySummarizer
from core.tool_registry import ToolRegistry, ToolMeta
from core.timing import timed
from core.tool_designer import ToolDesignerAgent
from core.capability_detector import is_capability_request
from core.approval import approval_prompt
from core.tool_code_generator import ToolCodeGeneratorAgent
from core.code_approval import code_approval_prompt
from core.credential_vault import CredentialVault
from core.secure_executor import SecureExecutor
from core.permission_store import PermissionStore

from core.scheduler.scheduled_agent import ScheduledAgent
from core.scheduler.scheduler import Scheduler
from core.agent_store import AgentStore
from core.intent_router import is_system_control_request
from core.control_handler import handle_system_control
from core.capability_detector import detect_capability, CapabilityType

init(autoreset=True)

# ---------------- STORES ----------------
agent_store = AgentStore()
permission_store = PermissionStore()
credential_vault = CredentialVault()

# ---------------- PERMISSIONS ----------------
permission_store.grant("search_web", "default")
permission_store.grant("check_inbox", "default")
permission_store.grant("speak_out_loud", "default")
# intentionally NOT granting draft_reply yet

# ---------------- CREDENTIAL VAULT ----------------
credential_vault.register_placeholder(
    tool_name="check_inbox",
    credential_type="gmail_oauth"
)

# ---------------- MEMORY ----------------
memory = MemoryManager()
preferences = memory.load_preferences()

# ---------------- SYSTEM PROMPT ----------------
system_prompt = f"""
You are Hermes, an autonomous AI agent.

CORE DIRECTIVE: Be PRACTICAL and PROACTIVE.

User Preferences:
- Writing style: {preferences['writing_style']}
- Coding style: {preferences['coding_style']}
- Verbosity: {preferences['verbosity']}
"""

# ---------------- AGENTS ----------------
planner = PlannerAgent(agents.manager_llm)
critic = CriticAgent(agents.manager_llm)
summarizer = MemorySummarizer(agents.manager_llm)
tool_designer = ToolDesignerAgent(agents.manager_llm)
tool_code_generator = ToolCodeGeneratorAgent(agents.manager_llm)

# ---------------- VOICE TOOL ----------------
@tool
def speak_out_loud(text: str):
    """Speak text aloud using TTS."""
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()
    return "Spoken."

# ---------------- TOOL REGISTRY ----------------
tool_registry = ToolRegistry()

tool_registry.register(
    ToolMeta("search_web", tools_web.search_web, approved=True, source="builtin")
)

tool_registry.register(
    ToolMeta(
        "check_inbox",
        tools_email.check_inbox,
        approved=True,
        source="builtin",
        requires_credentials=True
    )
)

tool_registry.register(
    ToolMeta(
        "draft_reply",
        tools_email.draft_reply,
        approved=True,
        source="builtin",
        requires_credentials=True
    )
)

tool_registry.register(
    ToolMeta("speak_out_loud", speak_out_loud, approved=True, source="builtin")
)

# ---------------- EXECUTOR ----------------
executor = SecureExecutor(
    llm=agents.manager_llm,
    tool_registry=tool_registry,
    permission_store=permission_store,
    credential_vault=credential_vault,
    system_prompt=system_prompt,
    execution_enabled=True
)

# ---------------- SCHEDULER (MANUAL MODE) ----------------
scheduler = Scheduler(
    executor=executor,
    agent_provider=agent_store.list_all
)


# ---------------- CHAT LOOP ----------------
def start_chat_session():
    print(Fore.CYAN + "\n✅ SYSTEM ONLINE. Hermes is listening.")
    print(Fore.CYAN + "---------------------------------------------------------")

    while True:
        try:
            user_input = prompt(
                HTML('<b><style color="ansigreen">👤 YOU:</style></b> ')
            ).strip()

            # -------- EXIT --------
            if user_input in ("exit", "quit"):
                summary = summarizer.summarize_session(memory.load_session())
                memory.store_long_term("summary", summary)
                memory.clear_session()
                print(Fore.YELLOW + "🧠 Session summarized and stored.")
                break

            # ==================================================
            # 🔐 CONTROL PLANE (NO LLM, FIRST)
            # ==================================================
            if is_system_control_request(user_input):
                result = handle_system_control(user_input, agent_store)

                if result == "RUN_SCHEDULER":
                    scheduler.run_once()
                    print(Fore.YELLOW + "⏱️ Scheduler tick executed")
                else:
                    print(Fore.YELLOW + result)

                continue


            if user_input == "run scheduler":
                scheduler.run_once()
                print(Fore.YELLOW + "⏱️ Scheduler tick executed")
                continue

            # ==================================================
            # 🔧 CAPABILITY REQUEST → TOOL + AGENT CREATION
            # ==================================================
            if is_capability_request(user_input):
                print(Fore.MAGENTA + "\n🧠 Capability request detected.")

                capability = detect_capability(user_input)

                # 🚨 HARD BLOCK — credential-based agents
                if capability == CapabilityType.CREDENTIAL_REQUIRED:
                    print(Fore.RED + "❌ Credential-based agents are not allowed in Hermes v1.")
                    continue

                try:
                    tool_design = tool_designer.design_tool(
                    user_input=user_input,
                    available_tools=tool_registry.list_tools(),
                    forced_tool_type=capability.value,
                    allow_credentials=(capability == CapabilityType.CREDENTIAL_REQUIRED)
                )


                except RuntimeError as e:
                    print(Fore.RED + str(e))
                    continue

                if not approval_prompt(tool_design):
                    print(Fore.RED + "❌ Tool design rejected.")
                    continue

                tool_code = tool_code_generator.generate_code(tool_design)
                if not code_approval_prompt(tool_code):
                    print(Fore.RED + "❌ Tool code rejected.")
                    continue

                tool_registry.register_generated_tool(
                    name=tool_design["tool_name"],
                    function=None
                )

                agent = ScheduledAgent(
                    name=tool_design["tool_name"],
                    tool_name=tool_design["tool_name"],
                    schedule="daily",
                    permissions=["default"],
                    enabled=False
                )
                agent_store.register(agent)

                print(Fore.GREEN + f"✅ Agent '{agent.name}' registered (disabled).")
                print(f"👉 Enable with: enable agent {agent.name}")
                continue

            # ==================================================
            # 🔁 NORMAL CHAT FLOW
            # ==================================================
            memory.add_session_message("user", user_input)

            detected = detect_preferences(user_input)
            for k, v in detected.items():
                memory.update_preference(k, v)

            raw_plan = planner.create_plan(user_input)
            plan = critic.review_plan(raw_plan)

            print(Fore.BLUE + "\n🧠 FINAL PLAN:")
            print(json.dumps(plan, indent=2))

            final_answer = executor.execute_plan(plan)
            print(Fore.GREEN + "\n🤖 HERMES:\n" + final_answer)

            memory.add_session_message("assistant", final_answer)

        except KeyboardInterrupt:
            print("\n👋 Force Exit.")
            break


if __name__ == "__main__":
    start_chat_session()
