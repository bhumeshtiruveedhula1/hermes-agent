# Hermes — Local AI Agent System (v1)

Hermes is a **local-first AI agent** that thinks before acting.

Instead of a reactive chatbot, Hermes uses:
- memory
- planning
- execution
- self-review

to behave like a real autonomous system.

---

## ✨ Features

- 🧠 Planner → Critic → Executor architecture
- 💾 Persistent memory (JSON + SQLite)
- 🎯 Deterministic tool execution
- 🧩 Preference learning
- 🧪 Full integration testing
- 🔐 Local & private (no cloud dependency)

---

## 📂 Project Structure

AI_Agent_System/
│
├── main.py
├── test_hermes_system.py
│
├── core/
│ ├── memory.py
│ ├── planner.py
│ ├── critic.py
│ ├── executor.py
│ ├── preferences.py
│ ├── summarizer.py
│ └── tool_args.py
│
├── tools/
│ ├── tools_web.py
│ └── tools_email.py
│
├── memory/
│ ├── session.json
│ ├── preferences.json
│ └── hermes.db

---

## 🚀 Quick Start

### 1. Setup
```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
