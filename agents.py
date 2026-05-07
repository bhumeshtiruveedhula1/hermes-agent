# agents.py — Phase 12+: Dual-model support
# Model is selected at startup via HERMES_MODEL env var (set by start_agent.bat).
# Default falls back to qwen3:8b for zero-config backward compat.
#
# Supported values:
#   HERMES_MODEL=qwen3:8b       — fast, 4GB VRAM, lower JSON accuracy
#   HERMES_MODEL=qwen2.5:14b    — quality, ~9GB hybrid, best planning

import os
from langchain_ollama import ChatOllama

# ── Model selection ─────────────────────────────────────────────────────────
_MODEL = os.environ.get("HERMES_MODEL", "qwen3:8b").strip()

# Per-model context window:
#   qwen3:8b    → 8192 tokens (small model, fits in full ctx)
#   qwen2.5:14b → 4096 tokens (larger model needs tighter ctx for speed)
_CTX = {
    "qwen3:8b":           8192,
    "qwen2.5-coder:14b":  4096,
}.get(_MODEL, 4096)

print(f"   (Config: {_MODEL} | ctx={_CTX} | VRAM-mode={'GPU-only' if _MODEL == 'qwen3:8b' else 'Hybrid GPU+CPU'})")

manager_llm = ChatOllama(
    model=_MODEL,
    temperature=0,
    num_ctx=_CTX,
    keep_alive="-1m"
)