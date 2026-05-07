# Hermes — Architecture Reference

> *How a one-sentence request becomes real actions across 12 integrations.*

---

## Table of Contents

1. [The Big Picture](#1-the-big-picture)
2. [Request Lifecycle](#2-request-lifecycle)
3. [Planner Agent](#3-planner-agent)
4. [Critic Agent](#4-critic-agent)
5. [Secure Executor](#5-secure-executor)
6. [Plugin System](#6-plugin-system)
7. [Autonomous Mission Planner](#7-autonomous-mission-planner)
8. [Approval System](#8-approval-system)
9. [Context Memory](#9-context-memory)
10. [WebSocket Architecture](#10-websocket-architecture)
11. [Multi-User System](#11-multi-user-system)
12. [Browser System](#12-browser-system)
13. [Conversation Store](#13-conversation-store)
14. [Data Layout](#14-data-layout)
15. [API Reference](#15-api-reference)

---

## 1. The Big Picture

Hermes is structured as three logical layers:

```
┌─────────────────────────────────────────────────────────────────┐
│  PRESENTATION LAYER                                             │
│  React dashboard (5173) ←──── WebSocket ────→ FastAPI (8000)   │
│  Chat, Missions, Browser, Plugins, History, Admin, Files        │
└───────────────────────────────┬─────────────────────────────────┘
                                │ REST + WS
┌───────────────────────────────▼─────────────────────────────────┐
│  INTELLIGENCE LAYER                                             │
│                                                                 │
│   User Input                                                    │
│       │                                                         │
│       ▼                                                         │
│   Context Manager ── injects last 6 messages                   │
│       │                                                         │
│       ▼                                                         │
│   Planner Agent ─── converts text to JSON step plan            │
│       │                                                         │
│       ▼                                                         │
│   Critic Agent ──── validates + corrects tool names            │
│       │                                                         │
│       ▼                                                         │
│   Secure Executor ─ routes each step to correct tool           │
│       │                                                         │
│       ▼                                                         │
│   Approval Gate ─── pauses for human sign-off on writes        │
└───────────────────────────────┬─────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────┐
│  TOOL LAYER                                                     │
│                                                                 │
│  Built-in:  Files  │  Browser  │  Web Search                   │
│  OAuth:     Gmail  │  Calendar │  GitHub                       │
│  Plugins:   Telegram│ WhatsApp │  Notion │ Slack │ Spotify     │
└─────────────────────────────────────────────────────────────────┘
```

All three layers communicate through the same FastAPI process. The frontend connects via WebSocket for real-time events and REST for data operations.

---

## 2. Request Lifecycle

A single user message goes through this pipeline:

```
User types: "read my latest emails"
                │
                ▼
    ┌─── api.py: POST /api/chat/mission ───────────────────────┐
    │                                                           │
    │   1. Autocorrect (pyspellchecker)                        │
    │      "emailz" → "emails"                                 │
    │                                                           │
    │   2. Load conversation history (ConversationStore)       │
    │      Last 6 messages → context string                    │
    │                                                           │
    │   3. build_contextual_input()                            │
    │      "=== HISTORY ===\n...\nCURRENT: read my emails"     │
    │                                                           │
    │   4. PlannerAgent.create_plan(contextual_input)          │
    │      LLM → JSON plan                                     │
    │      {                                                    │
    │        "goal": "Read latest emails",                      │
    │        "steps": [{                                        │
    │          "step_id": "1",                                  │
    │          "tool": "gmail_list",                            │
    │          "description": "List unread emails"              │
    │        }]                                                 │
    │      }                                                    │
    │                                                           │
    │   5. CriticAgent.review_plan(plan)                       │
    │      Validates tool names, fixes typos                    │
    │      "gmail_list" is valid → keep                        │
    │                                                           │
    │   6. For each step in plan:                               │
    │      tool in APPROVAL_TOOLS? → approval modal             │
    │      tool not in APPROVAL_TOOLS? → execute directly       │
    │                                                           │
    │   7. SecureExecutor.execute_plan(plan)                   │
    │      Routes to GmailCapability.execute(action="list")    │
    │      Returns: "1. Subject: ... From: ..."                │
    │                                                           │
    │   8. ConversationStore.add_message(hermes, result)       │
    │                                                           │
    │   9. broadcast(conversation_updated)                     │
    │                                                           │
    │   10. Return JSON response to frontend                    │
    └───────────────────────────────────────────────────────────┘
                │
                ▼
    Frontend renders result with GMAIL tool badge
```

---

## 3. Planner Agent

**File:** `core/planner.py`

The Planner is a single LLM call that converts natural language into a structured JSON plan.

### Output Schema
```json
{
  "goal": "string — overall mission description",
  "steps": [
    {
      "step_id": "string",
      "description": "string — what to do, including parameters",
      "tool": "string | null"
    }
  ]
}
```

### How It Works

```
System Prompt (static, set at startup)
├── Available tools list (exact names, never variations)
├── Rules per tool category (FILESYSTEM RULES, BROWSER RULES, etc.)
├── Context memory rules (INSTANT RECALL for follow-up questions)
├── Plugin tools (injected from PluginLoader.get_planner_prompt())
└── Security rules

+

User Input (dynamic, per request)
├── Conversation history (last 6 messages)
└── Current message

= JSON Plan
```

### Critical Design Decisions

**Tool names are exact strings.** The planner is given explicit rules like "use EXACTLY `fs_read` — NOT `read_file`, NOT `file_read`." The Critic catches anything that slips through.

**Plugin tools are injected at startup.** `PluginLoader.get_planner_prompt()` returns a formatted string listing all active plugin tools. This is appended to the system prompt when the planner is initialized.

**Context memory rules.** Follow-up questions like "what did you just read?" trigger `tool=null` with the answer coming from conversation history. The `INSTANT RECALL` block in the system prompt lists trigger phrases explicitly, with examples in JSON format.

**Tool validation after LLM response.** Even after the LLM returns, `allowed_tools` set filters the plan — anything not in the whitelist is set to `null`.

---

## 4. Critic Agent

**File:** `core/critic.py`

The Critic receives the Planner's JSON output and validates it. Its only job is to correct broken tool names — never remove valid ones.

### Correction Rules

```
"browser_open"   → "browser_go"
"read_file"      → "fs_read"
"list_files"     → "fs_list"
"send_email"     → "gmail_send"
"close_browser"  → "browser_close"
Any unknown tool → null
Any ALLOWED tool → KEEP exactly as-is, never null
```

### Double-Filter Architecture

```
Planner output
    │
    ▼
Critic LLM (fixes tool names)
    │
    ▼
_get_allowed_tools() hard filter
(Python set — not LLM)
    │
    ▼
Clean plan → Executor
```

The `_get_allowed_tools()` function builds the whitelist at call time — it reloads plugin tools dynamically so newly approved plugins are immediately valid.

---

## 5. Secure Executor

**File:** `core/secure_executor.py`

The Executor routes each plan step to the correct tool implementation. It's a large `if/elif` chain, ordered by tool category.

### Routing Order

```python
for step in plan["steps"]:
    tool = step["tool"]

    if not tool:          → LLM reasoning (tool=null steps)
    if tool in FS_TOOLS:  → FilesystemCapability
    if tool in BROWSER_TOOLS: → BrowserSession
    if tool in GMAIL_TOOLS:   → GmailCapability
    if tool in CALENDAR_TOOLS: → CalendarCapability
    if tool in GITHUB_TOOLS:  → GitHubCapability
    
    plugin = PluginLoader.get_plugin_for_tool(tool)
    if plugin:            → plugin.execute()
    
    if not registry.get(tool): → AutoToolBuilder
    
    # Standard tool registry path (legacy)
```

**Critical:** Every branch ends with `continue`. Missing `continue` causes fall-through to the auto-builder, which was a recurring bug during development.

### Tool Sets

```python
FS_TOOLS       = {"fs_list", "fs_read", "fs_write", "fs_delete"}

BROWSER_TOOLS  = {"browser_go", "browser_read", "browser_click",
                  "browser_fill", "browser_shot", "browser_scroll",
                  "browser_close"}

GMAIL_TOOLS    = {"gmail_list", "gmail_read", "gmail_send", "gmail_search"}

CALENDAR_TOOLS = {"calendar_list", "calendar_today",
                  "calendar_search", "calendar_create"}

GITHUB_TOOLS   = {"github_repos", "github_repo_info", "github_issues",
                  "github_prs", "github_commits", "github_search",
                  "github_create_issue"}

APPROVAL_TOOLS = {"fs_write", "fs_delete", "gmail_send",
                  "calendar_create", "telegram_send",
                  "github_create_issue", "whatsapp_send",
                  "notion_create", "notion_append", "slack_send"}
```

---

## 6. Plugin System

**File:** `core/plugin_loader.py`

The plugin system allows new integrations without modifying core files.

### File Structure

```
plugins/
├── active/        ← loaded at startup
├── pending/       ← awaiting human approval
└── backups/       ← disabled plugins saved here
```

### Plugin JSON Spec

```json
{
  "name": "slack",
  "version": "1.0",
  "description": "Send and read Slack messages",
  "module": "core.integrations.slack",
  "class": "SlackCapability",
  "tools": [
    {
      "name": "slack_send",
      "description": "Send a Slack message. Format: channel=X text=X",
      "action": "send",
      "requires_approval": true
    },
    {
      "name": "slack_channels",
      "description": "List Slack channels",
      "action": "list_channels",
      "requires_approval": false
    }
  ]
}
```

### Plugin Capability Class

```python
class SlackCapability:
    def execute(self, action: str, **kwargs) -> str:
        description = kwargs.get("description", "")

        if action == "send":
            # parse channel= and text= from description
            ...
            return "Sent to #general ✅"

        elif action == "list_channels":
            ...
            return "Channels:\n• #general\n• #dev"
```

### Discovery Flow

```
startup
    │
    ▼
PluginLoader scans plugins/active/*.json
    │
    ▼
For each JSON:
    import module dynamically (importlib)
    instantiate class
    register each tool → tool_name: plugin_instance map
    │
    ▼
get_planner_prompt() → formatted tool list for LLM
get_all_tool_names() → set for critic whitelist
get_plugin_for_tool(name) → plugin instance for executor
```

### AI Plugin Designer

`core/plugin_designer.py` wraps the LLM to design new plugins from natural language:

```
User: "design a plugin that checks cricket scores"
    │
    ▼
PluginDesigner._design_spec() → JSON spec via LLM
    │
    ▼
PluginDesigner._design_code() → Python class via LLM
    │
    ▼
PluginDesigner._check_syntax() → ast.parse() validation
    │
    ▼ (if syntax error)
PluginDesigner._fix_code() → LLM auto-fix
    │
    ▼
save to plugins/pending/
save to core/integrations/
    │
    ▼
Human reviews in Plugins tab → Approve/Reject
    │
    ▼ (if approved)
PluginLoader.approve_plugin() → test import → move to active/
```

---

## 7. Autonomous Mission Planner

**File:** `core/autonomous_executor.py`

Runs multi-step missions without user prompting between steps.

### Execution Flow

```
POST /api/mission/run
    │
    ▼
AutonomousExecutor.run_mission(prompt, conv_id, user_id, approval_fn)
    │
    ▼
broadcast(mission_started)
    │
    ▼
planner.create_plan(prompt) → critic.review_plan()
    │
    ▼
broadcast(mission_plan_ready, step_count=N)
    │
    ▼
for each step:
    broadcast(mission_step_start)
    │
    if tool in APPROVAL_TOOLS:
        approved = await approval_fn(tool, description)
        if not approved: skip step
    │
    result = await loop.run_in_executor(
        None,
        executor.execute_plan,
        {steps: [this_step]}
    )
    # ↑ Critical: runs sync executor in thread pool
    #   so async broadcasts fire between steps
    │
    if next step needs result (save/write/send keywords):
        inject "[Context: {result[:300]}]" into next step description
    │
    broadcast(mission_step_done)
    │
    ▼
broadcast(mission_complete)
    │
    ▼
mission_queue.set_status(done)
broadcast(queue_updated)
```

### Why `run_in_executor`?

`executor.execute_plan()` is synchronous — it calls Ollama and external APIs with blocking I/O. Running it directly in the async `run_mission` coroutine blocks the entire event loop, preventing WebSocket broadcasts from firing between steps. `loop.run_in_executor(None, fn, arg)` moves it to a thread pool, freeing the event loop for broadcasts.

### Context Chaining

Between steps, if the next step description contains result-dependent keywords (`save`, `write`, `send`, `summary`, `report`, `create`, `post`), the previous step's result is injected:

```
Step 1 result: "Top AI startups: OpenAI, Anthropic, Mistral..."
Step 2 description: "Save the research to /documents/report.txt"
    ↓ after injection:
"Save the research to /documents/report.txt
 [Context from previous step: Top AI startups: OpenAI, Anthropic, Mistral...]"
```

---

## 8. Approval System

### Flow

```
Executor detects tool in APPROVAL_TOOLS
    │
    ▼
Generate approval_id (uuid4 first 8 chars)
    │
    ▼
Create asyncio.Event(), store in approval_queue[approval_id]
    │
    ▼ (MUST happen before broadcast)
broadcast(approval_required, id, tool, description)
    │
    ▼
Frontend receives via WebSocket
    │
    ▼
ApprovalModal renders with 60s countdown
    │
    ▼
User clicks APPROVE or REJECT
    │
    ▼
POST /api/approvals/{id}/approve  or  /reject
    │
    ▼
approval_queue[id]["approved"] = True/False
approval_queue[id]["event"].set()
    │
    ▼
asyncio.wait_for(event.wait(), timeout=60) unblocks
    │
    ▼ (approved)
Step executes normally
    │
    ▼ (rejected or timeout)
step["tool"] = None
step["description"] = "[REJECTED] User denied {tool}"
```

### Why Queue-Before-Broadcast?

A common bug: creating the queue entry AFTER the broadcast meant the user could click Approve before the queue entry existed, causing the approve endpoint to find nothing. The fix is always register in `approval_queue` first, then broadcast.

---

## 9. Context Memory

**File:** `core/context_manager.py`

Hermes remembers the last 6 messages in a conversation.

### Format Injected into Planner

```
=== CONVERSATION HISTORY (use this as context) ===
USER: read /documents/notes.txt
HERMES [used: fs_read]: Contents of /documents/notes.txt:
hello world
=== END HISTORY ===

CURRENT REQUEST: what did you just read?
```

### Recall Intercept

For follow-up questions that don't need tool execution, `api.py` checks trigger phrases before calling the planner:

```python
RECALL_TRIGGERS = [
    "what did you just", "what was that", "tell me what you",
    "summarize it", "summarize that", "what did you read",
    "what did you find", "repeat that", "say that again"
]

if any(t in msg_lower for t in RECALL_TRIGGERS):
    # Answer from history directly via LLM with tool=null
    # Bypasses planner entirely — fast response
```

### fs_read Special Case

File contents are never truncated in context (other messages cap at 800 chars). This ensures "read a file then save it elsewhere" chains work correctly.

---

## 10. WebSocket Architecture

**One persistent connection per browser tab.**

```
Frontend                              Backend
   │                                     │
   │──── WS connect /ws/stream ─────────▶│
   │                                     │ append to connected_clients[]
   │                                     │
   │◀─── {"type": "ping"} ──────────────│ every 5s keepalive
   │                                     │
   │     [user sends chat message]       │
   │──── POST /api/chat/mission ────────▶│
   │                                     │ planner/critic/executor run
   │◀─── {"type":"approval_required"} ──│ approval needed
   │                                     │
   │──── POST /api/approvals/X/approve ─▶│
   │                                     │ event.set() → unblocks executor
   │◀─── {"type":"approval_resolved"} ──│
   │                                     │ executor continues
   │◀─── {"type":"conversation_updated"}│ result ready
   │                                     │
   │     [mission running]               │
   │◀─── {"type":"mission_step_start"}──│
   │◀─── {"type":"mission_step_done"} ──│
   │◀─── {"type":"mission_complete"} ───│
```

### Event Types

| Event | Trigger | Frontend Action |
|---|---|---|
| `ping` | Every 5s | Ignored |
| `approval_required` | APPROVAL_TOOLS step hit | Show ApprovalModal |
| `approval_resolved` | User approves/rejects | Hide modal |
| `conversation_updated` | Message saved | Reload sidebar |
| `mission_started` | run_mission() begins | Show live feed |
| `mission_plan_ready` | Plan built | Show step count |
| `mission_step_start` | Step begins | Update progress |
| `mission_step_done` | Step complete | Add to feed |
| `mission_complete` | All steps done | Show completion |
| `mission_failed` | Timeout or error | Show error state |
| `queue_updated` | Queue changes | Reload queue |
| `plugin_designed` | AI designer done | Show in pending |
| `plugin_approved` | Plugin approved | Reload plugins |
| `browser_navigate` | Browser navigated | Update URL display |
| `file_change` | File written/deleted | Reload file list |
| `safe_mode_changed` | Safe mode toggled | Update indicator |

---

## 11. Multi-User System

**File:** `core/user_store.py`

### User Schema

```json
{
  "id": "user_abc123",
  "name": "bhumesh",
  "password_hash": "sha256hex...",
  "role": "admin",
  "created_at": "2026-01-01T00:00:00",
  "sandbox_path": "/documents"
}
```

### Data Isolation

```
sandboxes/
├── user_1/documents/     ← default user
├── user_abc123/documents/ ← admin
└── user_def456/documents/ ← regular user

memory/conversations/
├── user_1/
├── user_abc123/
└── user_def456/
```

### Request Authentication

```python
def get_user_id(request: Request) -> str:
    return request.headers.get("X-User-Id", "user_1")
```

Frontend sets this header globally after login:
```javascript
axios.defaults.headers.common["X-User-Id"] = user.id
```

Default `user_1` fallback ensures all pre-Phase-11 functionality continues working.

### Role System

| Role | Capabilities |
|---|---|
| `admin` | All features + Admin tab + create/delete users |
| `user` | Chat, files, browser, missions — own sandbox only |

---

## 12. Browser System

**Files:** `core/browser/engine.py`, `core/browser/session.py`

### Singleton Pattern

```python
class BrowserSession:
    _instance = None

    @classmethod
    def get(cls) -> "BrowserSession":
        if cls._instance is None:
            cls._instance = BrowserSession()
        return cls._instance
```

One browser instance shared across all requests. This means browser state (current URL, cookies, DOM) persists between chat messages.

### Smart Click — 5 Strategies

```python
async def smart_click(self, target: str) -> str:
    # Strategy 1: CSS selector
    await self._page.click(target, timeout=4000)

    # Strategy 2: text content
    await self._page.get_by_text(target).first.click()

    # Strategy 3: link text
    await self._page.locator(f"a:has-text('{target[:20]}')").first.click()

    # Strategy 4: JavaScript click
    await self._page.evaluate(f"""
        const els = document.querySelectorAll('a,button,[role="link"]');
        for (const el of els) {{
            if (el.textContent.includes("{target[:40]}")) {{
                el.click(); break;
            }}
        }}
    """)

    # Strategy 5: URL extraction + navigation
    url_match = re.search(r'https?://[^\s]+', target)
    if url_match:
        await self._page.goto(url_match.group(0))
```

### Smart Fill Value Extraction

```python
def _extract_fill_value(description: str) -> str:
    # 1. Quoted: fill with "mr beast"        → mr beast
    q = re.search(r'["\'](.+?)["\']', description)
    if q: return q.group(1)

    # 2. "with X" pattern
    w = re.search(r'\bwith\s+(.+?)(?:\s+and\s+|\s*$)', description, re.I)
    if w: return w.group(1).strip()

    # 3. value=X pattern
    v = re.search(r'value=([^\s]+)', description)
    if v: return v.group(1)

    # 4. after last =
    if "=" in description:
        return description.split("=", 1)[1].strip()

    return description
```

### Headless Toggle

```python
BrowserSession.set_headless(True)   # Silent mode — no Chrome window
BrowserSession.set_headless(False)  # Live mode — visible Chrome
```

Changing mode calls `engine.set_headless()` which does a graceful Playwright restart in the same thread — the singleton is never destroyed.

---

## 13. Conversation Store

**File:** `core/conversation_store.py`

### Storage Format

```
memory/conversations/{user_id}/
├── index.json          ← lightweight index for sidebar
└── conv_YYYYMMDD_HHMMSS_xxxxxx.json ← full conversation
```

### Conversation Schema

```json
{
  "id": "conv_20260506_143022_abc123",
  "title": "Checked emails + Browsed GitHub",
  "created_at": "2026-05-06T14:30:22",
  "updated_at": "2026-05-06T14:31:45",
  "pinned": false,
  "tools_used": ["gmail_list", "github_repos"],
  "summary": "Listed emails and browsed repos...",
  "messages": [
    {
      "role": "user",
      "text": "check my emails",
      "ts": "2026-05-06T14:30:22",
      "tools": []
    },
    {
      "role": "hermes",
      "text": "You have 3 unread emails...",
      "ts": "2026-05-06T14:31:45",
      "tools": ["gmail_list"]
    }
  ]
}
```

### Auto-Title Generation

After the second message in a conversation, a title is generated from the tools used:

```python
labels = {
    "gmail_list": "Checked emails",
    "fs_write":   "Wrote file",
    "browser_go": "Browsed web",
    "github_repos": "Browsed GitHub",
    ...
}
# "Checked emails + Browsed GitHub"
```

---

## 14. Data Layout

```
hermes-agent/
│
├── memory/
│   ├── conversations/
│   │   ├── user_1/
│   │   │   ├── index.json
│   │   │   └── conv_*.json
│   │   └── {other_users}/
│   │
│   ├── users/
│   │   ├── index.json       ← user list (no password hashes)
│   │   └── user_*.json      ← full user records
│   │
│   ├── mission_queue.json   ← [{id, prompt, status, priority...}]
│   └── mission_templates.json ← [{id, name, prompt, builtin...}]
│
├── sandboxes/
│   └── {user_id}/
│       └── documents/       ← user's writable file area
│
├── plugins/
│   ├── active/              ← {name}.json + auto-loaded
│   ├── pending/             ← {name}.json + {name}.py awaiting approval
│   └── backups/             ← disabled plugins stored here
│
└── audit/
    └── audit_log.json       ← append-only action log
```

---

## 15. API Reference

### Chat
| Method | Route | Description |
|---|---|---|
| POST | `/api/chat` | Stateless chat (no history) |
| POST | `/api/chat/mission` | Context-aware chat with history |

### Conversations
| Method | Route | Description |
|---|---|---|
| POST | `/api/conversations` | Create new conversation |
| GET | `/api/conversations` | List all (supports `?search=`) |
| GET | `/api/conversations/{id}` | Get full conversation |
| DELETE | `/api/conversations/{id}` | Delete conversation |
| POST | `/api/conversations/{id}/pin` | Pin/unpin |

### Missions
| Method | Route | Description |
|---|---|---|
| POST | `/api/mission/run` | Run autonomous mission |
| GET | `/api/queue` | List mission queue |
| POST | `/api/queue` | Add to queue |
| DELETE | `/api/queue/{id}` | Remove from queue |
| POST | `/api/queue/clear` | Clear done/failed |
| GET | `/api/templates` | List templates |
| POST | `/api/templates` | Save template |
| DELETE | `/api/templates/{id}` | Delete template |

### Approvals
| Method | Route | Description |
|---|---|---|
| GET | `/api/approvals/pending` | List pending approvals |
| POST | `/api/approvals/{id}/approve` | Approve action |
| POST | `/api/approvals/{id}/reject` | Reject action |

### Files
| Method | Route | Description |
|---|---|---|
| GET | `/api/files` | List sandbox files |
| POST | `/api/files/write` | Write file |
| DELETE | `/api/files/delete` | Delete file |
| GET | `/api/files/read` | Read file content |

### Browser
| Method | Route | Description |
|---|---|---|
| POST | `/api/browser/navigate` | Navigate to URL |
| POST | `/api/browser/screenshot` | Take screenshot |
| POST | `/api/browser/read` | Get page text |
| POST | `/api/browser/close` | Close browser |
| POST | `/api/browser/mode` | Toggle headless |

### Plugins
| Method | Route | Description |
|---|---|---|
| GET | `/api/plugins` | List active + pending |
| POST | `/api/plugins/design` | AI plugin designer |
| POST | `/api/plugins/{name}/approve` | Approve pending plugin |
| POST | `/api/plugins/{name}/reject` | Reject pending plugin |
| POST | `/api/plugins/{name}/disable` | Disable active plugin |
| POST | `/api/plugins/{name}/restore` | Restore from backup |

### Auth
| Method | Route | Description |
|---|---|---|
| POST | `/api/auth/login` | Login |
| POST | `/api/auth/register` | Create user (admin) |
| GET | `/api/auth/users` | List users |
| DELETE | `/api/auth/users/{id}` | Delete user |

### Voice
| Method | Route | Description |
|---|---|---|
| GET | `/api/voice/status` | Get voice enabled state |
| POST | `/api/voice/toggle` | Toggle TTS on/off |

### System
| Method | Route | Description |
|---|---|---|
| GET | `/api/status` | System status + phase |
| GET | `/api/settings` | Current settings |
| POST | `/api/settings/safemode` | Toggle safe mode |
| GET | `/api/audit` | Audit log (last N) |
| GET | `/api/agents` | Background agents |
| POST | `/api/agents/{name}/enable` | Enable agent |
| POST | `/api/agents/{name}/disable` | Disable agent |

### WebSocket
| Route | Description |
|---|---|
| `ws://localhost:8000/ws/stream` | Real-time event stream |

---

## Design Principles

**1. Never break backward compat.**
`user_1` always works without headers. Single-user setups need zero configuration changes as new features land.

**2. Executor blocks are always closed with `continue`.**
This is enforced by convention. Missing `continue` causes fall-through to auto-builder — a silent, hard-to-debug failure mode.

**3. Queue before broadcast.**
Approval queue entries are always created before broadcasting to the frontend. A user clicking Approve in under a second would find an empty queue otherwise.

**4. Sync executor in async thread pool.**
`executor.execute_plan()` is synchronous. Any call from async context uses `loop.run_in_executor()`. Direct `await` is wrong — it blocks broadcasts.

**5. Plugins are stateless.**
Plugin capability classes can hold config (tokens, clients) but no request state. Each `execute()` call is independent.

**6. Voice is never fatal.**
All TTS calls are wrapped in try/except with daemon threads. A voice failure never surfaces to the user or affects execution flow.

**7. The LLM is the last resort for reasoning, not tool execution.**
Tool execution paths are deterministic Python code. The LLM is only used for planning (Planner), validation (Critic), and `tool=null` reasoning steps. Never for parsing tool results or deciding what happened.
