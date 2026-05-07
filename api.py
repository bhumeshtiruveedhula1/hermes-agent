# api.py — Hermes FastAPI Backend — Phase 9: Context Memory

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional

# ── Hermes core imports ──────────────────────────────────────────────
import agents as hermes_agents
from core.agent_store import AgentStore
from core.permission_store import PermissionStore
from core.credential_vault import CredentialVault
from core.tool_registry import ToolRegistry, ToolMeta
from core.secure_executor import SecureExecutor
from core.planner import PlannerAgent
from core.critic import CriticAgent
from core.scheduler.scheduler import Scheduler
from core.scheduler.scheduled_agent import ScheduledAgent
from core.audit.audit_logger import AuditLogger
from core.filesystem.capability import FilesystemCapability
from core.filesystem.sandbox import SandboxResolver
from core.conversation_store import ConversationStore
from core.context_manager import build_contextual_input   # ← Phase 9
from core.user_store import UserStore                      # ← Phase 11
from core.autonomous_executor import AutonomousExecutor    # ← Phase 15
from core.mission_queue import MissionQueue                # ← Phase 15
from core.mission_templates import MissionTemplates        # ← Phase 15
import tools_web
import tools_email

# ── Bootstrap ────────────────────────────────────────────────────────
agent_store      = AgentStore()
permission_store = PermissionStore()
credential_vault = CredentialVault()
conv_store       = ConversationStore()
user_store       = UserStore()                             # Phase 11

permission_store.grant("search_web",     "default")
permission_store.grant("check_inbox",    "default")
permission_store.grant("speak_out_loud", "default")
permission_store.grant("fs_list",        "default")
permission_store.grant("fs_read",        "default")
permission_store.grant("fs_write",       "default")
permission_store.grant("fs_delete",      "default")

credential_vault.register_placeholder("check_inbox", "gmail_oauth")

tool_registry = ToolRegistry()
tool_registry.register(ToolMeta("search_web",  tools_web.search_web,    approved=True, source="builtin"))
tool_registry.register(ToolMeta("check_inbox", tools_email.check_inbox, approved=True, source="builtin", requires_credentials=True))
tool_registry.register(ToolMeta("draft_reply", tools_email.draft_reply, approved=True, source="builtin", requires_credentials=True))

system_prompt = "You are Hermes, an autonomous AI agent. Be practical and proactive."

executor = SecureExecutor(
    llm=hermes_agents.manager_llm,
    tool_registry=tool_registry,
    permission_store=permission_store,
    credential_vault=credential_vault,
    system_prompt=system_prompt,
    execution_enabled=True,
    safe_mode=True
)

planner   = PlannerAgent(hermes_agents.manager_llm)
critic    = CriticAgent(hermes_agents.manager_llm)
scheduler = Scheduler(executor=executor, agent_provider=agent_store.list_all)
audit     = AuditLogger()

# Phase 15 — Autonomous missions
mission_queue     = MissionQueue()
mission_templates = MissionTemplates()
# auto_executor wired after broadcast() is defined (see below)

if not agent_store.get("folder_monitor"):
    agent_store.register(ScheduledAgent(
        name="folder_monitor", tool_name="fs_list",
        schedule="interval:1", permissions=["default"],
        enabled=False, metadata={"path": "/documents"}
    ))

# ── FastAPI app ───────────────────────────────────────────────────────
app = FastAPI(title="Hermes API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── WebSocket ─────────────────────────────────────────────────────────
connected_clients: list[WebSocket] = []

async def broadcast(event: dict):
    dead = []
    for ws in connected_clients:
        try:
            await ws.send_json(event)
        except Exception:
            dead.append(ws)
    for ws in dead:
        if ws in connected_clients:
            connected_clients.remove(ws)

@app.websocket("/ws/stream")
async def websocket_stream(ws: WebSocket):
    await ws.accept()
    connected_clients.append(ws)
    try:
        while True:
            try:
                await asyncio.wait_for(ws.receive_text(), timeout=5.0)
            except asyncio.TimeoutError:
                await ws.send_json({"type": "ping"})
    except WebSocketDisconnect:
        if ws in connected_clients:
            connected_clients.remove(ws)
    except Exception:
        if ws in connected_clients:
            connected_clients.remove(ws)

# ── Approval Queue ────────────────────────────────────────────────────
approval_queue: dict[str, dict] = {}

# Phase 15 — wire auto_executor now that broadcast() exists
auto_executor = AutonomousExecutor(planner, critic, executor, broadcast)

# ── Models ────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str

class ConvMessageRequest(BaseModel):
    conv_id: str
    message: str

class WriteRequest(BaseModel):
    path: str
    content: str

class BrowserNavRequest(BaseModel):
    url: str

class SafeModeRequest(BaseModel):
    enabled: bool

class PluginDesignRequest(BaseModel):
    description: str

class BrowserModeRequest(BaseModel):
    headless: bool

class PinRequest(BaseModel):
    pinned: bool

# Phase 11 — Auth models
class LoginRequest(BaseModel):
    name: str
    password: str

class CreateUserRequest(BaseModel):
    name: str
    password: str
    role: str = "user"

# Phase 11 — User ID from request header (defaults to user_1 for backward compat)
def get_user_id(request: Request) -> str:
    return request.headers.get("X-User-Id", "user_1")

# Phase 12 — Voice output state (default off)
voice_enabled: bool = False

class VoiceSettingRequest(BaseModel):
    enabled: bool

# Phase 15 — Autonomous mission models
class AutonomousMissionRequest(BaseModel):
    conv_id: str
    prompt:  str
    user_id: str = "user_1"

class QueueMissionRequest(BaseModel):
    conv_id:  str
    prompt:   str
    user_id:  str = "user_1"
    priority: int = 0

class SaveTemplateRequest(BaseModel):
    name:        str
    description: str
    prompt:      str

# ── Status ────────────────────────────────────────────────────────────
@app.get("/api/status")
def get_status():
    return {
        "online": True,
        "model": "qwen3:8b",
        "phase": "9",
        "agents_total": len(agent_store.list_all()),
        "agents_enabled": len([a for a in agent_store.list_all() if a.enabled]),
        "ts": datetime.utcnow().isoformat(),
    }

# ── Settings ──────────────────────────────────────────────────────────
@app.get("/api/settings")
def get_settings():
    return {"safe_mode": executor.safe_mode}

@app.post("/api/settings/safemode")
async def set_safe_mode(req: SafeModeRequest):
    executor.safe_mode = req.enabled
    executor.auto_builder.safe_mode = req.enabled
    await broadcast({"type": "safe_mode_changed", "enabled": req.enabled})
    return {"safe_mode": req.enabled}

# ── Agents ────────────────────────────────────────────────────────────
@app.get("/api/agents")
def get_agents():
    return [
        {
            "name": a.name, "tool_name": a.tool_name,
            "schedule": a.schedule, "enabled": a.enabled,
            "last_run_at": a.last_run_at.isoformat() if a.last_run_at else None,
            "metadata": a.metadata,
        }
        for a in agent_store.list_all()
    ]

@app.post("/api/agents/{name}/enable")
async def enable_agent(name: str):
    agent_store.enable(name)
    await broadcast({"type": "agent_update", "name": name, "enabled": True})
    return {"ok": True}

@app.post("/api/agents/{name}/disable")
async def disable_agent(name: str):
    agent_store.disable(name)
    await broadcast({"type": "agent_update", "name": name, "enabled": False})
    return {"ok": True}

@app.post("/api/scheduler/run")
async def run_scheduler():
    scheduler.run_once()
    await broadcast({"type": "scheduler_tick", "ts": datetime.utcnow().isoformat()})
    return {"ok": True}

# ── Audit ─────────────────────────────────────────────────────────────
@app.get("/api/audit")
def get_audit(limit: int = 50):
    events = audit.load_events()
    result = []
    for e in events[-limit:]:
        result.append({
            "ts": e.get("timestamp", ""), "phase": e.get("phase", ""),
            "action": e.get("action", ""), "decision": e.get("decision", ""),
            "tool": e.get("tool_name", ""), "reason": e.get("reason", ""),
        })
    return list(reversed(result))

# ── Auth (Phase 11) ──────────────────────────────────────────────────
@app.post("/api/auth/login")
def login(req: LoginRequest):
    user = user_store.verify(req.name, req.password)
    if not user:
        return {"ok": False, "error": "Invalid credentials"}
    return {"ok": True, "user": {
        "id": user["id"], "name": user["name"], "role": user["role"]
    }}

@app.post("/api/auth/register")
def register(req: CreateUserRequest):
    if user_store.get_by_name(req.name):
        return {"ok": False, "error": "Username taken"}
    user = user_store.create(req.name, req.password, req.role)
    return {"ok": True, "user": {"id": user["id"], "name": user["name"]}}

@app.get("/api/auth/users")
def list_users():
    return user_store.list_all()

@app.delete("/api/auth/users/{user_id}")
def delete_user(user_id: str):
    ok = user_store.delete(user_id)
    return {"ok": ok, "error": "Cannot delete admin" if not ok else None}

# ── Files ─────────────────────────────────────────────────────────────
@app.get("/api/files")
def get_files(request: Request, path: str = "/documents"):
    uid = get_user_id(request)
    try:
        physical = SandboxResolver.resolve(uid, path)
        if not physical.exists():
            return []
        items = []
        for p in physical.iterdir():
            stat = p.stat()
            items.append({
                "name": p.name, "is_dir": p.is_dir(),
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
        return sorted(items, key=lambda x: x["name"])
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/files/write")
async def write_file(req: WriteRequest, request: Request):
    uid = get_user_id(request)
    fs  = FilesystemCapability()
    result = fs.execute(action="write", path=req.path, user_id=uid, agent="dashboard", content=req.content)
    await broadcast({"type": "file_change", "action": "write", "path": req.path})
    return {"result": result}

@app.delete("/api/files/delete")
async def delete_file(path: str, request: Request):
    uid = get_user_id(request)
    fs  = FilesystemCapability()
    result = fs.execute(action="delete", path=path, user_id=uid, agent="dashboard")
    await broadcast({"type": "file_change", "action": "delete", "path": path})
    return {"result": result}

@app.get("/api/files/read")
def read_file(path: str, request: Request):
    uid = get_user_id(request)
    fs  = FilesystemCapability()
    result = fs.execute(action="read", path=path, user_id=uid, agent="dashboard")
    return {"content": result}

# ── Browser ───────────────────────────────────────────────────────────
@app.post("/api/browser/screenshot")
async def api_browser_screenshot():
    from core.browser.session import BrowserSession
    session = BrowserSession.get()
    result  = session.execute(action="screenshot")
    if result.startswith("[BLOCKED]") or result.startswith("[ERROR]"):
        return {"error": result}
    return {"screenshot": result}

@app.post("/api/browser/navigate")
async def api_browser_navigate(req: BrowserNavRequest):
    from core.browser.session import BrowserSession
    session = BrowserSession.get()
    result  = session.execute(action="navigate", target=req.url)
    await broadcast({"type": "browser_navigate", "url": req.url})
    return {"result": result}

@app.post("/api/browser/read")
async def api_browser_read():
    from core.browser.session import BrowserSession
    session = BrowserSession.get()
    result  = session.execute(action="get_text")
    return {"text": result}

@app.post("/api/browser/close")
async def api_browser_close():
    from core.browser.session import BrowserSession
    session = BrowserSession.get()
    result  = session.execute(action="close")
    return {"result": result}

# Phase 10 Task 3 — Headless mode toggle
@app.post("/api/browser/mode")
async def set_browser_mode(req: BrowserModeRequest):
    from core.browser.session import BrowserSession
    BrowserSession.set_headless(req.headless)
    await broadcast({"type": "browser_mode_changed", "headless": req.headless})
    return {"headless": req.headless, "ok": True}

# ── Voice (Phase 12) ──────────────────────────────────────────────────
@app.get("/api/voice/status")
def voice_status():
    return {"voice_enabled": voice_enabled}

@app.post("/api/voice/toggle")
async def toggle_voice(req: VoiceSettingRequest):
    global voice_enabled
    voice_enabled = req.enabled
    await broadcast({"type": "voice_changed", "enabled": req.enabled})
    return {"voice_enabled": voice_enabled}

# ── Approvals ─────────────────────────────────────────────────────────
@app.get("/api/approvals/pending")
def get_pending_approvals():
    return [
        {k: v for k, v in a.items() if k != "event"}
        for a in approval_queue.values()
    ]

@app.post("/api/approvals/{approval_id}/approve")
async def approve_action(approval_id: str):
    print(f"[APPROVAL] Received approve for {approval_id}, in queue: {approval_id in approval_queue}")
    if approval_id in approval_queue:
        approval_queue[approval_id]["approved"] = True
        approval_queue[approval_id]["event"].set()
        await broadcast({"type": "approval_resolved", "id": approval_id, "approved": True})
    return {"ok": True}

@app.post("/api/approvals/{approval_id}/reject")
async def reject_action(approval_id: str):
    if approval_id in approval_queue:
        approval_queue[approval_id]["approved"] = False
        approval_queue[approval_id]["event"].set()
        await broadcast({"type": "approval_resolved", "id": approval_id, "approved": False})
    return {"ok": True}

# ── Plugins ───────────────────────────────────────────────────────────
@app.get("/api/plugins")
def get_plugins():
    from core.plugin_loader import PluginLoader
    return {
        "active":  PluginLoader.get_all_plugins(),
        "pending": PluginLoader.get_pending_plugins()
    }

@app.post("/api/plugins/design")
async def design_plugin(req: PluginDesignRequest):
    from core.plugin_designer import PluginDesigner
    designer = PluginDesigner(hermes_agents.manager_llm)
    try:
        result = designer.design(req.description)
        await broadcast({"type": "plugin_designed", "name": result["plugin_name"]})
        return result
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/plugins/{name}/approve")
async def approve_plugin(name: str):
    from core.plugin_loader import PluginLoader
    success, message = PluginLoader.approve_plugin(name)
    if success:
        await broadcast({"type": "plugin_approved", "name": name})
        return {"ok": True, "message": message}
    return {"ok": False, "error": message}

@app.post("/api/plugins/{name}/reject")
async def reject_plugin(name: str):
    from core.plugin_loader import PluginLoader
    success = PluginLoader.reject_plugin(name)
    return {"ok": success}

@app.post("/api/plugins/{name}/disable")
async def disable_plugin(name: str):
    from core.plugin_loader import PluginLoader
    success = PluginLoader.disable_plugin(name)
    return {"ok": success}

@app.post("/api/plugins/{name}/restore")
async def restore_plugin(name: str):
    from core.plugin_loader import PluginLoader
    success = PluginLoader.restore_plugin(name)
    if success:
        await broadcast({"type": "plugin_restored", "name": name})
    return {"ok": success}

# ── Conversations ─────────────────────────────────────────────────────
@app.post("/api/conversations")
def create_conversation(request: Request):
    return conv_store.create(user_id=get_user_id(request))

@app.get("/api/conversations")
def list_conversations(request: Request, search: str = ""):
    return conv_store.list_all(search=search, user_id=get_user_id(request))

@app.get("/api/conversations/{conv_id}")
def get_conversation(conv_id: str, request: Request):
    conv = conv_store.get(conv_id, user_id=get_user_id(request))
    if not conv:
        return {"error": "Not found"}
    return conv

@app.delete("/api/conversations/{conv_id}")
def delete_conversation(conv_id: str, request: Request):
    conv_store.delete(conv_id, user_id=get_user_id(request))
    return {"ok": True}

@app.post("/api/conversations/{conv_id}/pin")
def pin_conversation(conv_id: str, req: PinRequest, request: Request):
    conv_store.pin(conv_id, req.pinned, user_id=get_user_id(request))
    return {"ok": True}

# ── Chat (stateless — no context) ────────────────────────────────────
@app.post("/api/chat")
async def chat(req: ChatRequest):
    try:
        from core.autocorrect import autocorrect
        corrected_msg, corrections = autocorrect(req.message)
        raw_plan = planner.create_plan(corrected_msg)
        plan     = critic.review_plan(raw_plan)
        result   = executor.execute_plan(plan)
        await broadcast({"type": "chat_result", "message": req.message, "result": result})
        return {
            "plan": plan, "result": result,
            "corrections": corrections,
            "corrected_input": corrected_msg if corrections else None
        }
    except Exception as e:
        return {"plan": {}, "result": f"[ERROR] {str(e)}"}

# ── Chat Mission (with context memory) ───────────────────────────────
@app.post("/api/chat/mission")
async def chat_mission(req: ConvMessageRequest, request: Request):
    user_id = get_user_id(request)   # Phase 11: per-user isolation
    try:
        from core.autocorrect import autocorrect
        corrected_msg, corrections = autocorrect(req.message)

        # ── Phase 9: Snapshot history BEFORE saving current message ──────
        # BUG FIX (double-message): build context from history that does NOT
        # include the current user turn yet. We pass this clean list to
        # build_contextual_input which uses it directly (no [:-1] slice needed
        # here since current message isn't in the list yet).
        conv_before = conv_store.get(req.conv_id)
        conv_messages_before = conv_before.get("messages", []) if conv_before else []
        contextual_input = build_contextual_input(corrected_msg, conv_messages_before)

        # Now save user message (AFTER context snapshot)
        conv_store.add_message(req.conv_id, "user", req.message)

        # Plugin designer shortcut
        msg_lower = corrected_msg.lower()
        if any(p in msg_lower for p in ["design a plugin","create a plugin","add a plugin","make a plugin","build a plugin"]):
            from core.plugin_designer import PluginDesigner
            designer = PluginDesigner(hermes_agents.manager_llm)
            try:
                result_data = designer.design(corrected_msg)
                result = f"Plugin '{result_data['plugin_name']}' designed! Go to the Plugins tab to review the spec, code, and approve it."
                conv_store.add_message(req.conv_id, "hermes", result, ["plugin_designer"], user_id=user_id)
                await broadcast({"type": "plugin_designed", "name": result_data["plugin_name"]})
                return {"plan": {}, "result": result, "tools_used": ["plugin_designer"], "corrections": corrections}
            except Exception as e:
                result = f"[ERROR] Plugin design failed: {e}"
                conv_store.add_message(req.conv_id, "hermes", result, [], user_id=user_id)
                return {"plan": {}, "result": result, "tools_used": [], "corrections": corrections}

        # ── Recall shortcut — deterministic memory answer ─────────────────
        # Qwen3:8B cannot reliably pick tool=null for recall questions via
        # prompt alone. We intercept deterministically BEFORE calling the
        # planner so the model never gets a chance to call the wrong tool.
        if _is_recall_question(corrected_msg) and conv_messages_before:
            last_result, _ = _get_last_hermes_result(conv_messages_before)
            if last_result:
                from langchain_core.messages import SystemMessage as SM, HumanMessage as HM
                recall_resp = hermes_agents.manager_llm.invoke([
                    SM(content=(
                        "You are Hermes, a helpful AI assistant. "
                        "Answer the user's question using ONLY the context provided below. "
                        "Be concise and direct. Do not mention file paths unless the user asks. "
                        "Do not call any tools. Do not make up information outside the context."
                    )),
                    HM(content=f"Previous result:\n{last_result}\n\nUser: {corrected_msg}")
                ])
                result     = recall_resp.content
                tools_used = []
                conv_store.add_message(req.conv_id, "hermes", result, tools_used, user_id=user_id)
                conv_obj = conv_store.get(req.conv_id, user_id=user_id)
                if conv_obj and len(conv_obj["messages"]) == 2:
                    conv_store.update_title(req.conv_id, _generate_title(req.message, result, tools_used), user_id=user_id)
                    conv_store.update_summary(req.conv_id, _generate_summary(tools_used, result), user_id=user_id)
                await broadcast({"type": "conversation_updated", "conv_id": req.conv_id, "tools": tools_used})
                return {
                    "plan": {"goal": "Answer from memory", "steps": []},
                    "result": result, "tools_used": tools_used, "corrections": corrections
                }

        # Plan using contextual input (has history prepended)
        raw_plan = planner.create_plan(contextual_input)
        plan     = critic.review_plan(raw_plan)

        # ── Frontend approval for sensitive actions ────────────────
        APPROVAL_TOOLS = {
            "fs_write", "fs_delete",
            "gmail_send", "calendar_create",
            "telegram_send", "github_create_issue",
            "whatsapp_send",    # Phase 14
            "notion_create",    # Phase 14
            "notion_append",    # Phase 14
            "slack_send",       # Phase 14
        }
        for step in plan.get("steps", []):
            tool = step.get("tool", "")
            if tool not in APPROVAL_TOOLS:
                continue

            approval_id = str(uuid.uuid4())[:8]

            event = asyncio.Event()
            approval_queue[approval_id] = {
                "id": approval_id, "action": tool, "tool": tool,
                "details": {"description": step.get("description",""), "conv_id": req.conv_id},
                "approved": None, "event": event
            }

            await broadcast({
                "type": "approval_required",
                "id": approval_id, "action": tool, "tool": tool,
                "details": {"description": step.get("description",""), "conv_id": req.conv_id}
            })
            print(f"[APPROVAL] Sent approval_required for {tool} — ID: {approval_id}")

            try:
                await asyncio.wait_for(event.wait(), timeout=60.0)
                approved = approval_queue[approval_id]["approved"]
                print(f"[APPROVAL] Result for {approval_id}: {approved}")
            except asyncio.TimeoutError:
                print(f"[APPROVAL] TIMEOUT for {approval_id}")
                approved = False
            finally:
                approval_queue.pop(approval_id, None)

            if not approved:
                step["tool"] = None
                step["description"] = f"[REJECTED] User denied {tool}"

        executor.current_user_id = user_id   # Phase 11: route fs ops to correct sandbox
        result     = executor.execute_plan(plan)
        tools_used = [s.get("tool") for s in plan.get("steps", []) if s.get("tool")]

        # Phase 12 — Voice output (non-blocking, never fatal)
        if voice_enabled and result and not result.startswith("[ERROR]"):
            try:
                from core.voice.tts import speak
                speak(result)
            except Exception:
                pass  # TTS failure must never break the response

        conv_store.add_message(req.conv_id, "hermes", result, tools_used, user_id=user_id)

        # Auto-title after first exchange
        conv = conv_store.get(req.conv_id, user_id=user_id)
        if conv and len(conv["messages"]) == 2:
            conv_store.update_title(req.conv_id, _generate_title(req.message, result, tools_used), user_id=user_id)
            conv_store.update_summary(req.conv_id, _generate_summary(tools_used, result), user_id=user_id)

        await broadcast({"type": "conversation_updated", "conv_id": req.conv_id, "tools": tools_used})

        return {
            "plan": plan, "result": result,
            "tools_used": tools_used, "corrections": corrections,
            "corrected_input": corrected_msg if corrections else None
        }

    except Exception as e:
        return {"plan": {}, "result": f"[ERROR] {str(e)}", "tools_used": []}


# ── Recall Detection Helpers ──────────────────────────────────────────────────
# Used by chat_mission to intercept memory questions before the planner runs.

_RECALL_TRIGGERS = [
    "what did you just read", "what did you read",
    "what was that", "what was in",
    "summarize it", "summarize that", "can you summarize", "give me a summary",
    "what did it say", "what does it say",
    "tell me what you found", "what did you find",
    "what was the result", "what were the results",
    "what did you write", "what was written",
    "what did you just do", "what was in the file",
]

def _is_recall_question(msg: str) -> bool:
    """
    Returns True if the user's message is asking about a previous result
    (not requesting new tool execution).
    """
    m = msg.lower().strip()
    return any(trigger in m for trigger in _RECALL_TRIGGERS)


def _get_last_hermes_result(conv_messages: list) -> tuple:
    """
    Scans conversation history in reverse and returns (text, tools) of the
    most recent hermes message that is NOT a [BLOCKED] or [ERROR] response.
    Returns (None, []) if nothing usable is found.
    """
    for msg in reversed(conv_messages):
        if msg.get("role") == "hermes":
            text  = msg.get("text", "")
            tools = msg.get("tools", [])
            # Skip failed/blocked responses — they contain no usable content
            if text and not text.startswith("[BLOCKED]") and not text.startswith("[ERROR]"):
                return text, tools
    return None, []

def _generate_title(user_msg: str, result: str, tools: list) -> str:
    if not tools:
        return user_msg[:50] + ("..." if len(user_msg) > 50 else "")
    labels = {
        "gmail_list":"Checked emails",  "gmail_send":"Sent email",
        "gmail_read":"Read email",       "gmail_search":"Searched emails",
        "calendar_today":"Checked calendar", "calendar_create":"Created event",
        "calendar_list":"Listed events",     "calendar_search":"Searched calendar",
        "github_repos":"Browsed GitHub",     "github_repo_info":"Read repo",
        "github_issues":"Checked issues",    "github_prs":"Checked PRs",
        "github_commits":"Checked commits",  "github_create_issue":"Created issue",
        "browser_go":"Browsed web",
        "fs_list":"Listed files",   "fs_read":"Read file",
        "fs_write":"Wrote file",    "fs_delete":"Deleted file",
        "search_web":"Searched web",
        "weather_current":"Checked weather",
        "telegram_send":"Sent Telegram",
        "plugin_designer":"Designed plugin",
    }
    return " + ".join([labels.get(t, t) for t in tools[:3]]) or user_msg[:50]

def _generate_summary(tools: list, result: str) -> str:
    if not tools:
        return result[:100]
    return f"Used {', '.join(tools[:3])}. {result[:80]}..."


# ── Phase 15: Autonomous Mission ──────────────────────────────────────────
@app.post("/api/mission/run")
async def run_autonomous_mission(req: AutonomousMissionRequest):
    """Execute a full multi-step mission autonomously with live WS updates."""
    # Track this run in the mission queue so UI shows live status
    mission_record = mission_queue.enqueue(
        req.prompt, req.user_id, req.conv_id, priority=-1
    )
    mission_id = mission_record["id"]
    mission_queue.set_status(mission_id, "running")

    try:
        async def approval_fn(tool: str, description: str, conv_id: str) -> bool:
            approval_id = str(uuid.uuid4())[:8]
            event       = asyncio.Event()
            approval_queue[approval_id] = {
                "id": approval_id, "action": tool, "tool": tool,
                "details": {"description": description, "conv_id": conv_id},
                "approved": None, "event": event,
            }
            await broadcast({
                "type": "approval_required",
                "id": approval_id, "action": tool, "tool": tool,
                "details": {"description": description, "conv_id": conv_id},
            })
            try:
                await asyncio.wait_for(event.wait(), timeout=60.0)
                return bool(approval_queue[approval_id]["approved"])
            except asyncio.TimeoutError:
                return False
            finally:
                approval_queue.pop(approval_id, None)

        # Set user context on executor
        executor.current_user_id = req.user_id

        result = await asyncio.wait_for(
            auto_executor.run_mission(
                mission_prompt=req.prompt,
                conv_id=req.conv_id,
                user_id=req.user_id,
                approval_fn=approval_fn,
            ),
            timeout=300.0,  # 5 minute hard cap — prevents infinite hangs
        )
        final_status = "done" if result.get("success") else "failed"
        mission_queue.set_status(mission_id, final_status, result.get("final_output", ""))
        await broadcast({"type": "queue_updated"})
        return result
    except asyncio.TimeoutError:
        msg = "[TIMEOUT] Mission exceeded 5 minute limit and was stopped."
        mission_queue.set_status(mission_id, "failed", msg)
        await broadcast({"type": "mission_failed", "conv_id": req.conv_id,
                         "error": msg, "ts": datetime.utcnow().isoformat()})
        await broadcast({"type": "queue_updated"})
        return {"success": False, "steps_taken": 0, "results": [], "final_output": msg}
    except Exception as e:
        mission_queue.set_status(mission_id, "failed", str(e))
        await broadcast({"type": "queue_updated"})
        return {"success": False, "steps_taken": 0, "results": [], "final_output": str(e)}


# ── Phase 15: Mission Queue ───────────────────────────────────────────────
@app.get("/api/queue")
def get_queue(user_id: str = "user_1"):
    return mission_queue.list_all(user_id)

@app.post("/api/queue")
async def add_to_queue(req: QueueMissionRequest):
    mission = mission_queue.enqueue(req.prompt, req.user_id, req.conv_id, req.priority)
    await broadcast({"type": "queue_updated", "mission": mission})
    return mission

@app.delete("/api/queue/{mission_id}")
async def remove_from_queue(mission_id: str):
    mission_queue.delete(mission_id)
    await broadcast({"type": "queue_updated"})
    return {"ok": True}

@app.post("/api/queue/clear")
async def clear_done_missions():
    mission_queue.clear_done()
    return {"ok": True}


# ── Phase 15: Mission Templates ───────────────────────────────────────────
@app.get("/api/templates")
def get_templates():
    return mission_templates.list_all()

@app.post("/api/templates")
def save_template(req: SaveTemplateRequest):
    return mission_templates.save(req.name, req.description, req.prompt)

@app.delete("/api/templates/{template_id}")
def delete_template(template_id: str):
    success = mission_templates.delete(template_id)
    return {"ok": success}
