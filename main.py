# main.py
import json
import pyttsx3
from colorama import init, Fore

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool

from prompt_toolkit import prompt
from prompt_toolkit.formatted_text import HTML

import agents
import tools_web
import tools_email

from core.memory import MemoryManager
from core.planner import PlannerAgent
from core.critic import CriticAgent
from core.executor import ExecutorAgent
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


init(autoreset=True)



# ---------------- SECURITY STORES ----------------
permission_store = PermissionStore()
credential_vault = CredentialVault()

# Example: built-in tool permissions
permission_store.grant("search_web", "default")
permission_store.grant("check_inbox", "default")
permission_store.grant("draft_reply", "default")


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
    """Convert text to speech."""
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()
    return "Spoken."

# ---------------- TOOL REGISTRY ----------------
tool_registry = ToolRegistry()

tool_registry.register(
    ToolMeta(
        "search_web",
        tools_web.search_web,
        approved=True,
        source="builtin"
    )
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
    ToolMeta(
        "speak_out_loud",
        speak_out_loud,
        approved=True,
        source="builtin"
    )
)



USE_SECURE_EXECUTOR = True

# ---------------- EXECUTOR ----------------
if USE_SECURE_EXECUTOR:
    executor = SecureExecutor(
        llm=agents.manager_llm,
        tool_registry=tool_registry,
        permission_store=permission_store,
        credential_vault=credential_vault,
        system_prompt=system_prompt
        execution_enabled=True  # 🔥 explicit opt-in

    )
else:
    executor = ExecutorAgent(
        llm=agents.manager_llm,
        tool_registry=tool_registry,
        system_prompt=system_prompt
    )

# ---------------- CHAT LOOP ----------------
def start_chat_session():
    print(Fore.CYAN + "\n✅ SYSTEM ONLINE. Hermes is listening.")
    print(Fore.CYAN + "---------------------------------------------------------")

    while True:
        try:
            user_input = prompt(
                HTML('<b><style color="ansigreen">👤 YOU:</style></b> ')
            )

            # -------- EXIT --------
            if user_input.lower().strip() in ["exit", "quit"]:
                summary = summarizer.summarize_session(memory.load_session())
                memory.store_long_term("summary", summary)
                memory.clear_session()
                print(Fore.YELLOW + "🧠 Session summarized and stored.")
                print("👋 Bye!")
                break

            memory.add_session_message("user", user_input)

            # -------- PREFERENCES --------
            detected = detect_preferences(user_input)
            for k, v in detected.items():
                memory.update_preference(k, v)

            metrics = {}
            
            # ==================================================
            # 🔒 STEP 3 — DESIGN → APPROVAL → CODE → APPROVAL
            # ==================================================
            if is_capability_request(user_input):
                print(Fore.MAGENTA + "\n🧠 Capability request detected.")

                try:
                    with timed("tool_design", metrics):
                        tool_design = tool_designer.design_tool(
                            user_input=user_input,
                            available_tools=tool_registry.list_tools()
                        )
                except RuntimeError as e:
                    print(Fore.RED + str(e))
                    continue

                approved_design = approval_prompt(tool_design)
                if not approved_design:
                    print(Fore.RED + "❌ Tool design rejected.")
                    continue
                
                with timed("tool_code_generation", metrics):
                    tool_code = tool_code_generator.generate_code(tool_design)
                
                approved_code = code_approval_prompt(tool_code)
                if not approved_code:
                    print(Fore.RED + "❌ Tool code rejected.")
                    continue
                # 🔒 SAFE REGISTRATION (NOT EXECUTABLE)
                tool_registry.register_generated_tool(
                    name=tool_design["tool_name"],
                    function=None  # code not loaded yet
                )


                memory.store_long_term(
                    "decision",
                    f"Generated tool approved (inactive): {tool_design['tool_name']}"
                )
                memory.store_long_term(
                    "generated_tool_code",
                    f"Tool: {tool_design['tool_name']}\n\n{tool_code}"
                )



                print(Fore.GREEN + "✅ Tool registered (inactive). Execution disabled.")

                print(Fore.CYAN + "\n⏱️ Performance:")
                for k, v in metrics.items():
                    print(f"  {k}: {v:.2f}s")

                continue
            # ==================================================
                
                
                

                
            # ==================================================

            # -------- PLANNING --------
            with timed("planning", metrics):
                raw_plan = planner.create_plan(user_input)

            with timed("critic", metrics):
                plan = critic.review_plan(raw_plan)

            print(Fore.BLUE + "\n🧠 FINAL PLAN:")
            print(json.dumps(plan, indent=2))

            # -------- EXECUTION --------
            with timed("execution", metrics):
                final_answer = executor.execute_plan(plan)

            print(Fore.GREEN + "\n🤖 HERMES:\n" + final_answer)

            print(Fore.CYAN + "\n⏱️ Performance:")
            for k, v in metrics.items():
                print(f"  {k}: {v:.2f}s")

            memory.add_session_message("assistant", final_answer)

        except KeyboardInterrupt:
            print("\n👋 Force Exit.")
            break


if __name__ == "__main__":
    start_chat_session()
