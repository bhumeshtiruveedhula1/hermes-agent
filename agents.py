# agents.py
from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage

# --- 1. SPECIALIST (Qwen) - DISABLED ---
# print("   (Config: Qwen 2.5 Coder is ready on standby...)")
# coder_llm = ChatOllama(model="qwen2.5-coder", temperature=0)

# @tool
# def ask_programmer_agent(coding_task: str):
#     # ... (Keep this commented out) ...
#     pass

# agents.py
from langchain_ollama import ChatOllama

print("   (Config: Qwen 2.5 Manager is ready...)")

manager_llm = ChatOllama(
    model="qwen2.5:7b-instruct-q8_0",
    temperature=0.2,
    num_ctx=8192,
    keep_alive="-1m"
)

