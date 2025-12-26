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

# --- 2. MANAGER (Hermes) - ACTIVE & UNCHAINED ---
print("   (Config: Hermes 3 Manager is ready...)")
# Increased temperature to 0.3 so it writes better essays/code
manager_llm = ChatOllama(
    model="hermes3", 
    temperature=0.3, 
    num_ctx=4096, 
    keep_alive="-1m"
)