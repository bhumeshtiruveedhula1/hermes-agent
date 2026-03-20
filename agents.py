# agents.py
from langchain_ollama import ChatOllama

print("   (Config: Qwen3 8B is ready...)")

manager_llm = ChatOllama(
    model="qwen3:8b",
    temperature=0,
    num_ctx=8192,
    keep_alive="-1m"
)