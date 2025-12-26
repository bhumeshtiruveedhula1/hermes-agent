# Hermes v1 — Agent Architecture

Hermes is a local-first, deterministic AI agent system built around **planning, memory, and disciplined execution**.
This project focuses on *system intelligence*, not model tricks.

---

## 🎯 Design Goals

- Local execution (privacy-first)
- Deterministic agent behavior
- Persistent memory across sessions
- Debuggable and testable architecture
- VRAM-safe (sequential agents)

---

## 🧠 Core Agent Loop

User Input
↓
Preference Detection
↓
Planner Agent
↓
Critic Agent
↓
Executor Agent
↓
Memory (Session + Long-term)



All agents run **sequentially** using the same LLM instance.

---

## 🧩 Components Overview

### `PlannerAgent` (`core/planner.py`)
**Responsibility**
- Convert user intent into an executable plan
- Output strict JSON only

**Key Rules**
- Never executes tools
- Uses only allowed tool names
- Outputs deterministic schema

---

### `CriticAgent` (`core/critic.py`)
**Responsibility**
- Normalize and repair planner output
- Enforce schema contracts
- Fix invalid or hallucinated tool names

---

### `ExecutorAgent` (`core/executor.py`)
**Responsibility**
- Execute steps sequentially
- Call tools deterministically
- Use LLM only for reasoning steps
- Never crash on invalid plans

---

### `MemoryManager` (`core/memory.py`)
**Memory Types**
- Short-term: `session.json` (last N messages)
- Preferences: `preferences.json`
- Long-term: `hermes.db` (SQLite)

**Stored Knowledge**
- decisions
- summaries
- facts

Memory is **compressed intelligence**, not chat logs.

---

### Preference Learning (`core/preferences.py`)
- Rule-based detection only
- Updates preferences only on explicit user statements
- Avoids hallucinated personalization

---

### Summarization (`core/summarizer.py`)
- Converts session history into long-term summaries
- Triggered on exit
- Prevents memory bloat

---

### Tool Argument Inference (`core/tool_args.py`)
- Converts plan steps into tool call arguments
- Deterministic, no LLM guessing

---

## 🔧 Tools

Available tools (fixed contract):
- `search_web`
- `check_inbox`
- `draft_reply`
- `speak_out_loud`

Tools are side-effect only and fully isolated.

---

## 🧪 Testing Strategy

- Full integration test: `test_hermes_system.py`
- Covers:
  - memory
  - preferences
  - planner
  - critic
  - executor
  - tools
  - summarization

---

## 🚫 Explicit Non-Goals (v1)

- Vector databases
- Parallel agents
- UI frameworks
- Background schedulers
- Autonomous self-prompting loops

These are **v2+ concerns**.

---

## ✅ Status

Hermes v1 is **feature-complete, stable, and production-grade** for a local agent core.
