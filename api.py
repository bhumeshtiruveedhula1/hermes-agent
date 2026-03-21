# api.py — Hermes FastAPI Backend
# Place this in: C:\Users\bhumeshjyothi\Desktop\gemini\AI_Agent_System\api.py

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import json
import asyncio
from pathlib import Path
from datetime import datetime

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
import tools_web
import tools_email

# ── Bootstrap (same as main.py) ──────────────────────────────────────
agent_store    = AgentStore()
permission_store = PermissionStore()
credential_vault = CredentialVault()

permission_store.grant("search_web",    "default")
permission_store.grant("check_inbox",   "default")
permission_store.grant("speak_out_loud","default")
permission_store.grant("fs_list",       "default")
permission_store.grant("fs_read",       "default")
permission_store.grant("fs_write",      "default")
permission_store.grant("fs_delete",     "default")

credential_vault.register_placeholder("check_inbox", "gmail_oauth")

tool_registry = ToolRegistry()
tool_registry.register(ToolMeta("search_web",  tools_web.search_web,     approved=True, source="builtin"))
tool_registry.register(ToolMeta("check_inbox", tools_email.check_inbox,  approved=True, source="builtin", requires_credentials=True))
tool_registry.register(ToolMeta("draft_reply", tools_email.draft_reply,  approved=True, source="builtin", requires_credentials=True))

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

# ── WebSocket broadcast ───────────────────────────────────────────────
connected_clients: list[WebSocket] = []

async def broadcast(event: dict):
    dead = []
    for ws in connected_clients:
        try:
            await ws.send_json(event)
        except Exception:
            dead.append(ws)
    for ws in dead:
        connected_clients.remove(ws)

@app.websocket("/ws/stream")
async def websocket_stream(ws: WebSocket):
    await ws.accept()
    connected_clients.append(ws)
    try:
        while True:
            await asyncio.sleep(30)
    except WebSocketDisconnect:
        connected_clients.remove(ws)

# ── Models ────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str

class WriteRequest(BaseModel):
    path: str
    content: str

class AgentToggle(BaseModel):
    enabled: bool

# ── Routes ────────────────────────────────────────────────────────────

@app.get("/api/agents")
def get_agents():
    return [
        {
            "name": a.name,
            "tool_name": a.tool_name,
            "schedule": a.schedule,
            "enabled": a.enabled,
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

@app.get("/api/audit")
def get_audit(limit: int = 50):
    events = audit.load_events()
    result = []
    for e in events[-limit:]:
        result.append({
            "ts":       e.get("timestamp", ""),
            "phase":    e.get("phase", ""),
            "action":   e.get("action", ""),
            "decision": e.get("decision", ""),
            "tool":     e.get("tool_name", ""),
            "reason":   e.get("reason", ""),
        })
    return list(reversed(result))

@app.get("/api/files")
def get_files(user_id: str = "user_1", path: str = "/documents"):
    try:
        physical = SandboxResolver.resolve(user_id, path)
        if not physical.exists():
            return []
        items = []
        for p in physical.iterdir():
            stat = p.stat()
            items.append({
                "name": p.name,
                "is_dir": p.is_dir(),
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
        return sorted(items, key=lambda x: x["name"])
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/files/write")
async def write_file(req: WriteRequest, user_id: str = "user_1"):
    fs = FilesystemCapability()
    result = fs.execute(action="write", path=req.path, user_id=user_id, agent="dashboard", content=req.content)
    await broadcast({"type": "file_change", "action": "write", "path": req.path})
    return {"result": result}

@app.delete("/api/files/delete")
async def delete_file(path: str, user_id: str = "user_1"):
    fs = FilesystemCapability()
    result = fs.execute(action="delete", path=path, user_id=user_id, agent="dashboard")
    await broadcast({"type": "file_change", "action": "delete", "path": path})
    return {"result": result}

@app.get("/api/files/read")
def read_file(path: str, user_id: str = "user_1"):
    fs = FilesystemCapability()
    result = fs.execute(action="read", path=path, user_id=user_id, agent="dashboard")
    return {"content": result}

@app.post("/api/chat")
async def chat(req: ChatRequest):
    try:
        raw_plan = planner.create_plan(req.message)
        plan     = critic.review_plan(raw_plan)
        result   = executor.execute_plan(plan)
        await broadcast({"type": "chat_result", "message": req.message, "result": result})
        return {"plan": plan, "result": result}
    except Exception as e:
        return {"plan": {}, "result": f"[ERROR] {str(e)}"}

@app.get("/api/status")
def get_status():
    return {
        "online": True,
        "model": "qwen3:8b",
        "phase": "3",
        "agents_total": len(agent_store.list_all()),
        "agents_enabled": len([a for a in agent_store.list_all() if a.enabled]),
        "ts": datetime.utcnow().isoformat(),
    }
# ── Browser direct control endpoints ─────────────────────────────────

class BrowserNavRequest(BaseModel):
    url: str

@app.post("/api/browser/screenshot")
async def api_browser_screenshot():
    from core.browser.session import BrowserSession
    session = BrowserSession.get()
    result = session.execute(action="screenshot")
    if result.startswith("[BLOCKED]") or result.startswith("[ERROR]"):
        return {"error": result}
    return {"screenshot": result}

@app.post("/api/browser/navigate")
async def api_browser_navigate(req: BrowserNavRequest):
    from core.browser.session import BrowserSession
    session = BrowserSession.get()
    result = session.execute(action="navigate", target=req.url)
    await broadcast({"type": "browser_navigate", "url": req.url})
    return {"result": result}

@app.post("/api/browser/read")
async def api_browser_read():
    from core.browser.session import BrowserSession
    session = BrowserSession.get()
    result = session.execute(action="get_text")
    return {"text": result}

@app.post("/api/browser/close")
async def api_browser_close():
    from core.browser.session import BrowserSession
    session = BrowserSession.get()
    result = session.execute(action="close")
    return {"result": result}


class SafeModeRequest(BaseModel):
    enabled: bool

@app.post("/api/settings/safemode")
async def set_safe_mode(req: SafeModeRequest):
    executor.safe_mode = req.enabled
    executor.auto_builder.safe_mode = req.enabled
    await broadcast({"type": "safe_mode_changed", "enabled": req.enabled})
    return {"safe_mode": req.enabled}

@app.get("/api/settings")
def get_settings():
    return {"safe_mode": executor.safe_mode}


# ── Plugin management endpoints ───────────────────────────────────────

@app.get("/api/plugins")
def get_plugins():
    from core.plugin_loader import PluginLoader
    return {
        "active": PluginLoader.get_all_plugins(),
        "pending": PluginLoader.get_pending_plugins()
    }

@app.post("/api/plugins/{name}/approve")
async def approve_plugin(name: str):
    from core.plugin_loader import PluginLoader
    success = PluginLoader.approve_plugin(name)
    await broadcast({"type": "plugin_approved", "name": name})
    return {"ok": success}

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
