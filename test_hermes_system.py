"""
Hermes AI Agent – Full System Validation Script
Tests memory, preferences, planner, critic, executor, tools, and summarization.
"""

import json
import os
from pprint import pprint

import agents
import tools_web
import tools_email

from core.memory import MemoryManager
from core.planner import PlannerAgent
from core.critic import CriticAgent
from core.executor import ExecutorAgent
from core.preferences import detect_preferences
from core.summarizer import MemorySummarizer
from core.tool_args import infer_tool_args

from langchain_core.messages import SystemMessage, HumanMessage


# ---------------- BASIC SETUP ----------------
print("\n========== HERMES SYSTEM TEST ==========\n")

memory = MemoryManager()
planner = PlannerAgent(agents.manager_llm)
critic = CriticAgent(agents.manager_llm)
summarizer = MemorySummarizer(agents.manager_llm)

TOOLS = {
    "search_web": tools_web.search_web,
    "check_inbox": tools_email.check_inbox,
    "draft_reply": tools_email.draft_reply,
}

system_prompt = """
You are Hermes, an autonomous AI agent.
Be practical and proactive.
"""

executor = ExecutorAgent(
    llm=agents.manager_llm,
    tools=TOOLS,
    system_prompt=system_prompt
)


# ---------------- TEST 1: MEMORY INIT ----------------
print("\n[TEST 1] Memory Initialization")

prefs = memory.load_preferences()
assert isinstance(prefs, dict), "Preferences not loaded"
print("✔ Preferences loaded:", prefs)

session = memory.load_session()
assert isinstance(session, list), "Session not initialized"
print("✔ Session memory ready")


# ---------------- TEST 2: PREFERENCE DETECTION ----------------
print("\n[TEST 2] Preference Detection")

text = "keep it concise and production ready"
detected = detect_preferences(text)

assert detected, "No preferences detected"
for k, v in detected.items():
    memory.update_preference(k, v)

prefs = memory.load_preferences()
print("✔ Preferences updated:", prefs)


# ---------------- TEST 3: PLANNER OUTPUT ----------------
print("\n[TEST 3] Planner JSON Contract")

user_input = "check my email"
raw_plan = planner.create_plan(user_input)

print("Planner output:")
pprint(raw_plan)

assert "steps" in raw_plan, "Planner missing steps"
assert isinstance(raw_plan["steps"], list), "Steps not a list"

for step in raw_plan["steps"]:
    assert "step_id" in step, "Missing step_id"
    assert "description" in step, "Missing description"
    assert "tool" in step, "Missing tool field"

print("✔ Planner schema valid")


# ---------------- TEST 4: CRITIC NORMALIZATION ----------------
print("\n[TEST 4] Critic Plan Normalization")

final_plan = critic.review_plan(raw_plan)

print("Critic output:")
pprint(final_plan)

for step in final_plan["steps"]:
    assert "tool" in step, "Critic failed to normalize tool field"

print("✔ Critic enforced schema")


# ---------------- TEST 5: TOOL ARG INFERENCE ----------------
print("\n[TEST 5] Tool Argument Inference")

for step in final_plan["steps"]:
    if step["tool"]:
        args = infer_tool_args(step["tool"], step["description"])
        assert isinstance(args, dict), "Tool args not dict"
        print(f"✔ Args for {step['tool']}:", args)


# ---------------- TEST 6: EXECUTOR (SAFE RUN) ----------------
print("\n[TEST 6] Executor Execution")

result = executor.execute_plan(final_plan)
assert isinstance(result, str), "Executor did not return string"

print("✔ Executor ran successfully")
print("\nExecutor output preview:\n", result[:300])


# ---------------- TEST 7: MEMORY WRITE ----------------
print("\n[TEST 7] Memory Persistence")

memory.add_session_message("user", user_input)
memory.add_session_message("assistant", result)

session = memory.load_session()
assert len(session) >= 2, "Session messages not stored"
print("✔ Session memory written")


# ---------------- TEST 8: SESSION SUMMARIZATION ----------------
print("\n[TEST 8] Session Summarization")

summary = summarizer.summarize_session(session)
assert isinstance(summary, str) and summary.strip(), "Empty summary"

memory.store_long_term("summary", summary)
memory.clear_session()

print("✔ Session summarized and cleared")
print("\nSummary:\n", summary)


# ---------------- FINAL RESULT ----------------
print("\n========== ALL TESTS PASSED ==========")
print("Hermes core architecture is STABLE.\n")
