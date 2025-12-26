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

init(autoreset=True)

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

# ---------------- VOICE TOOL ----------------
@tool
def speak_out_loud(text: str):
    """
    Convert the given text to speech and speak it out loud.
    """
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()
    return "Spoken."

# ---------------- TOOL REGISTRY ----------------
tool_registry = ToolRegistry()

tool_registry.register(
    ToolMeta(
        name="search_web",
        function=tools_web.search_web,
        approved=True,
        source="builtin"
    )
)

tool_registry.register(
    ToolMeta(
        name="check_inbox",
        function=tools_email.check_inbox,
        approved=True,
        source="builtin",
        requires_credentials=True
    )
)

tool_registry.register(
    ToolMeta(
        name="draft_reply",
        function=tools_email.draft_reply,
        approved=True,
        source="builtin",
        requires_credentials=True
    )
)

tool_registry.register(
    ToolMeta(
        name="speak_out_loud",
        function=speak_out_loud,
        approved=True,
        source="builtin"
    )
)

# ---------------- EXECUTOR ----------------
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

            # -------- EXIT + SUMMARIZE --------
            if user_input.lower().strip() in ["exit", "quit"]:
                summary = summarizer.summarize_session(
                    memory.load_session()
                )
                memory.store_long_term("summary", summary)
                memory.clear_session()

                print(Fore.YELLOW + "🧠 Session summarized and stored.")
                print("👋 Bye!")
                break

            memory.add_session_message("user", user_input)

            # -------- PREFERENCE DETECTION --------
            detected = detect_preferences(user_input)
            for key, value in detected.items():
                memory.update_preference(key, value)
                print(Fore.YELLOW + f"🧠 Learned preference: {key} = {value}")

            metrics = {}

            # -------- PLANNING --------
            with timed("planning", metrics):
                raw_plan = planner.create_plan(user_input)

            with timed("critic", metrics):
                plan = critic.review_plan(raw_plan)

            print(Fore.BLUE + "\n🧠 FINAL PLAN:")
            print(json.dumps(plan, indent=2))
            print(Fore.BLUE + "---------------------------------------------------------")

            # -------- EXECUTION --------
            with timed("execution", metrics):
                final_answer = executor.execute_plan(plan)

            print(Fore.GREEN + "\n🤖 HERMES:\n" + final_answer)

            print(Fore.CYAN + "\n⏱️ Performance:")
            for k, v in metrics.items():
                print(f"  {k}: {v:.2f}s")

            # -------- MEMORY WRITE --------
            memory.add_session_message("assistant", final_answer)
            memory.store_long_term(
                "summary",
                f"User: {user_input}\nResult: {final_answer[:500]}"
            )

        except KeyboardInterrupt:
            print("\n👋 Force Exit.")
            break

if __name__ == "__main__":
    start_chat_session()
