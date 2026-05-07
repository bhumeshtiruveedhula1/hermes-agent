<div align="center">

```
██╗  ██╗███████╗██████╗ ███╗   ███╗███████╗███████╗
██║  ██║██╔════╝██╔══██╗████╗ ████║██╔════╝██╔════╝
███████║█████╗  ██████╔╝██╔████╔██║█████╗  ███████╗
██╔══██║██╔══╝  ██╔══██╗██║╚██╔╝██║██╔══╝  ╚════██║
██║  ██║███████╗██║  ██║██║ ╚═╝ ██║███████╗███████║
╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝╚══════╝╚══════╝
```

### *An autonomous AI agent platform that thinks, plans, and acts — so you don't have to.*

[![Phase](https://img.shields.io/badge/Phase-15%20Complete-brightgreen?style=flat-square)](https://github.com/bhumeshtiruveedhula1/hermes-agent)
[![Model](https://img.shields.io/badge/Model-Qwen3%3A8B-blue?style=flat-square)](https://ollama.ai)
[![Stack](https://img.shields.io/badge/Stack-FastAPI%20%2B%20React-orange?style=flat-square)](https://fastapi.tiangolo.com)
[![GPU](https://img.shields.io/badge/GPU-RTX%204060-76b900?style=flat-square)](https://nvidia.com)
[![License](https://img.shields.io/badge/License-MIT-purple?style=flat-square)](LICENSE)

</div>

---

## What is Hermes?

> *"Most AI tools are chatbots with a sidebar. Hermes is an operator."*

Hermes is a **locally-run autonomous AI agent platform** built from scratch.

You give it a goal. It builds a plan. It executes that plan across your files, browser, email, calendar, GitHub, Slack, Notion, Telegram, Spotify, and WhatsApp — while asking for your approval before doing anything irreversible.

No cloud dependency. No API fees for the core model. No data leaving your machine.

It runs on your GPU.

---

## The Moment That Makes It Click

```
You:    "Research the top 5 AI startups this week, summarize each one,
         save the report to my documents, and send it to my Slack."

Hermes: Planning mission...
        ▶ Step 1/4  [search_web]   Searching: top AI startups 2026...
        ▶ Step 2/4  [search_web]   Deep diving each company...
        ⚡ Step 3/4  [fs_write]    ── APPROVAL REQUIRED ──────────────
                                   Write to /documents/ai_report.txt
                                   [ APPROVE ]  [ Reject ]
        ✓           User approved.
        ⚡ Step 4/4  [slack_send]  ── APPROVAL REQUIRED ──────────────
                                   Post to #general
                                   [ APPROVE ]  [ Reject ]
        ✓           User approved.

        ✅ Mission complete in 4 steps.
           Report saved. Slack notified.
```

You typed one sentence. Hermes did the rest.

---

## Architecture at a Glance

```
╔═════════════════════════════════════════════════════════════╗
║                    HERMES DASHBOARD                         ║
║             React + Vite  (localhost:5173)                  ║
║  ┌─────────┐ ┌──────────┐ ┌─────────┐ ┌────────────────┐    ║
║  │  Chat   │ │ Missions │ │ Plugins │ │    Browser     │    ║
║  │(context │ │(autonomo-│ │(AI      │ │  (live + shot) │    ║
║  │ memory) │ │ us queue)│ │ creator)│ │                │    ║
║  └─────────┘ └──────────┘ └─────────┘ └────────────────┘    ║
╚══════════════════════╤══════════════════════════════════════╝
                       │  WebSocket + REST
╔══════════════════════▼══════════════════════════════════════╗
║                  FASTAPI BACKEND                            ║
║                  (localhost:8000)                           ║
║                                                             ║
║  ┌─────────┐   ┌─────────┐   ┌──────────────────────────┐   ║
║  │ Planner │──▶│  Critic │──▶│     Secure Executor     │   ║
║  │  Agent  │   │  Agent  │   │  (tool router + gate)    │   ║
║  └─────────┘   └─────────┘   └──────────────────────────┘   ║
║                                          │                  ║
║  ┌───────────────────────────────────────▼──────────────┐   ║
║  │                   TOOL LAYER                         │   ║
║  │  Files │ Browser │ Gmail │ Calendar │ GitHub         │   ║
║  │  Slack │ Notion  │ Spotify│ Telegram│ WhatsApp       │   ║
║  └──────────────────────────────────────────────────────┘   ║
║                                                             ║
║  ┌─────────────────────────────────────────────────────┐    ║
║  │  PLUGIN SYSTEM — drop JSON + Python file, done     │     ║
║  └─────────────────────────────────────────────────────┘    ║
╚══════════════════════╤══════════════════════════════════════╝
                       │
╔══════════════════════▼══════════════════════════════════════╗
║              QWEN3:8B  via  OLLAMA                          ║
║              Running locally — RTX 4060                     ║
╚═════════════════════════════════════════════════════════════╝
```

---

## Features

### 🧠 Planner → Critic → Executor Pipeline
Every request is converted into a step-by-step JSON plan by the Planner LLM. The Critic reviews and corrects tool names. The Executor runs each step with a security gate. Three layers between your words and real actions.

### 🔐 Approval Gate
Write, send, delete — anything irreversible pauses and shows a real-time modal in the dashboard with a 60-second countdown. You approve or reject. Auto-rejects on timeout.

### 🤖 Autonomous Missions
Describe the full goal once. Hermes plans all steps, executes them in sequence, chains results between steps, and reports back when complete. A live feed shows each step happening in real time.

### 📋 Mission Queue + Templates
Line up multiple missions. Built-in templates for morning briefing, research & save, GitHub reports, and more. Save your own. Run with one click.

### 🧩 Plugin System
Adding a new integration means dropping two files — a JSON spec and a Python class. No changes to core code. The planner and critic auto-discover new tools at startup.

### 🤖 AI Plugin Creator
Type: *"design a plugin that checks train delays."* Hermes writes the JSON spec and Python code itself, syntax-checks it, and queues it for your review before it goes live.

### 🗣️ Context Memory
Hermes remembers what it did earlier in the same conversation. "What did you just read?" and "summarize it" and "save that" all work correctly.

### 👁️ Live Browser
Watch Hermes navigate the web in a panel inside the dashboard. Toggle between Live mode (visible Chrome) and Silent mode (headless). Screenshots stream into chat.

### 🎤 Voice I/O
Click the mic button and speak. Hermes auto-sends your speech. Enable voice output and hear responses spoken aloud via offline TTS.

### 👥 Multi-User
Login screen, SHA-256 hashed passwords, role-based access (admin/user), per-user file sandboxes, per-user conversation history, admin panel for user management.

---

## Integrations

| Category | Integration | Tools |
|---|---|---|
| 📧 Email | Gmail (OAuth) | List, read, search, send |
| 📅 Calendar | Google Calendar (OAuth) | List, today, search, create |
| 💻 Code | GitHub (REST API) | Repos, issues, PRs, commits, create issue |
| 💬 Messaging | Telegram Bot | Send, receive |
| 💬 Messaging | WhatsApp (Twilio) | Send, list |
| 📝 Productivity | Notion | List pages, read, create, append |
| 💼 Workspace | Slack | Channels, send, read |
| 🎵 Music | Spotify (OAuth) | Current, search, play*, pause*, next* |
| 🌤️ Utility | Weather (Open-Meteo) | Current, forecast |
| 🔍 Utility | Web Search | Search + summarize |
| 🌐 Browser | Playwright Chromium | Navigate, read, click, fill, screenshot |
| 📁 Files | Sandboxed Filesystem | List, read, write, delete |

*Requires Spotify Premium*

---

## Tech Stack

```
Backend      Python 3.13 + FastAPI + Uvicorn
LLM          Qwen3:8B via Ollama (local, RTX 4060)
Frontend     React 18 + Vite
Real-time    WebSockets (native FastAPI)
Browser      Playwright (Chromium)
Storage      JSON files (memory/ + sandboxes/)
Auth         SHA-256 hashed passwords, localStorage sessions
Voice In     Web Speech API (Chrome/Edge)
Voice Out    pyttsx3 (offline Windows SAPI)
Fonts        Bebas Neue + Space Mono
```

---

## Project Structure

```
hermes-agent/
│
├── api.py                       ← FastAPI app, all 40+ endpoints
├── agents.py                    ← Ollama LLM client setup
│
├── core/
│   ├── planner.py               ← user input → JSON step plan
│   ├── critic.py                ← validates + corrects tool names
│   ├── secure_executor.py       ← routes each step to correct tool
│   ├── context_manager.py       ← injects conversation history
│   ├── autonomous_executor.py   ← multi-step async mission runner
│   ├── mission_queue.py         ← persistent prioritized queue
│   ├── mission_templates.py     ← built-in + user templates
│   ├── plugin_loader.py         ← dynamic plugin discovery
│   ├── plugin_designer.py       ← AI-powered plugin creator
│   ├── conversation_store.py    ← per-user chat history (JSON)
│   ├── user_store.py            ← multi-user auth store
│   ├── autocorrect.py           ← spell check before planning
│   │
│   ├── browser/
│   │   ├── engine.py            ← Playwright + smart_click (5 strategies)
│   │   └── session.py           ← singleton session, headless toggle
│   │
│   ├── integrations/
│   │   ├── gmail.py             ← Gmail OAuth capability
│   │   ├── calendar.py          ← Google Calendar OAuth capability
│   │   ├── github.py            ← GitHub REST capability
│   │   ├── telegram.py          ← Telegram Bot capability
│   │   ├── whatsapp.py          ← Twilio WhatsApp capability
│   │   ├── notion.py            ← Notion REST capability
│   │   ├── spotify.py           ← Spotify OAuth capability
│   │   └── slack.py             ← Slack Bot capability
│   │
│   ├── voice/
│   │   └── tts.py               ← offline TTS, daemon threads
│   │
│   └── filesystem/
│       ├── capability.py        ← read/write/list/delete
│       └── sandbox.py           ← per-user path resolver
│
├── plugins/
│   ├── active/                  ← auto-loaded at startup
│   ├── pending/                 ← awaiting human approval
│   └── backups/                 ← disabled plugin backups
│
├── memory/
│   ├── conversations/{user_id}/ ← per-user chat history
│   ├── users/                   ← user accounts
│   ├── mission_queue.json       ← persistent mission queue
│   └── mission_templates.json   ← saved templates
│
├── sandboxes/
│   └── {user_id}/documents/     ← isolated per-user filesystem
│
└── hermes-ui/src/
    ├── App.jsx                  ← root, WebSocket, auth gate
    ├── pages/
    │   ├── Chat.jsx             ← mission chat + sidebar + badges
    │   ├── Missions.jsx         ← autonomous mission planner UI
    │   ├── Overview.jsx         ← live system dashboard
    │   ├── Plugins.jsx          ← plugin manager + AI designer
    │   ├── History.jsx          ← conversation history browser
    │   ├── Browser.jsx          ← live browser control
    │   ├── Files.jsx            ← sandbox file manager
    │   ├── Agents.jsx           ← background agent manager
    │   ├── AuditLog.jsx         ← tamper-evident audit log
    │   ├── Admin.jsx            ← user management (admin only)
    │   └── Login.jsx            ← full-screen auth screen
    └── components/
        └── ApprovalModal.jsx    ← WebSocket approval modal
```

---

## Getting Started

### Prerequisites
```powershell
# Install Ollama
winget install Ollama.Ollama

# Pull the model
ollama pull qwen3:8b

# Install Python deps
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium

# Install frontend deps
cd hermes-ui && npm install
```

### Configure
```bash
# Copy example env
cp .env.example .env

# Add credentials for integrations you want to use
# (see .env.example for full list with instructions)
```

### Run
```powershell
# Terminal 1 — Backend
uvicorn api:app --reload

# Terminal 2 — Frontend
cd hermes-ui && npm run dev
```

Open `http://localhost:5173`

```
Default admin login:
Username: admin
Password: hermes2026
```

---

## The Approval Modal

Every write, send, or delete pauses here:

```
╔══════════════════════════════════════╗
║ ████████████████████████░░░░░  42s  ║  ← countdown
╠══════════════════════════════════════╣
║                                      ║
║   ✍   APPROVAL REQUIRED             ║
║   fs_write · 42s remaining           ║
║                                      ║
║   Write "AI startups report" to      ║
║   /documents/ai_report.txt           ║
║                                      ║
║   [      APPROVE      ]  [ Reject ]  ║
╚══════════════════════════════════════╝
```

No response in 60 seconds → auto-rejected. Safe by default.

---

## Adding a Plugin in 2 Minutes

**`plugins/active/trivia.json`**
```json
{
  "name": "trivia",
  "description": "Random trivia facts",
  "module": "core.integrations.trivia",
  "class": "TriviaCapability",
  "tools": [{
    "name": "trivia_fact",
    "description": "Get a random trivia fact",
    "action": "random",
    "requires_approval": false
  }]
}
```

**`core/integrations/trivia.py`**
```python
import requests

class TriviaCapability:
    def execute(self, action, **kwargs):
        r = requests.get("https://opentdb.com/api.php?amount=1&type=boolean")
        q = r.json()["results"][0]
        return f"{q['question']} (Answer: {q['correct_answer']})"
```

Restart. Hermes now knows trivia.

Or type: **"design a plugin that tells trivia facts"** — Hermes writes both files.

---

## Roadmap

```
✅  Phase 0-8    Foundation — executor, filesystem, browser, background agents
✅  Phase 9      Conversation context memory
✅  Phase 10     Smart browser agent (dual mode, live view, smart fill)
✅  Phase 11     Multi-user system (login, roles, sandboxes, admin panel)
✅  Phase 12     Voice I/O (mic input, TTS output, waveform animation)
✅  Phase 14     External integrations (Slack, Notion, Spotify, WhatsApp)
✅  Phase 15     Autonomous mission planner (queue, templates, live feed)

⬜  Phase 13     Mobile PWA + responsive + push notifications
⬜  Phase 16     Productization (installer, auto-updater, onboarding)
⬜  Phase 17     Hermes Cloud (hosted, multi-tenant)
⬜  Phase 18     Plugin Marketplace (share + install community plugins)
⬜  Phase 19     Hermes API (build on top of Hermes)
```

---

## Philosophy

**Local first.** Your data stays on your machine. The LLM runs on your GPU. No per-message API cost for core functionality.

**Approval gated.** Every write, send, or delete requires human confirmation. The system is built to ask, not assume.

**Plugin native.** The core stays small. Everything else is a plugin. Two files and a restart.

**Observable.** Every action is logged. Every plan is visible in the dashboard. Every step broadcasts to the UI in real time. You always know what Hermes is doing and why.

---

<div align="center">

*Built from scratch. One developer. One GPU. 15 phases.*

*Started as a curiosity. Became something real.*

**⭐ If Hermes made you think differently about what a local AI assistant can be — star this repo.**

</div>
