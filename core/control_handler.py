# core/control_handler.py

from core.audit.audit_replay import replay_audit


def handle_system_control(user_input: str, agent_store):
    text = user_input.lower().strip()

    if text == "list agents":
        agents = agent_store.list_all()
        if not agents:
            return "No agents registered."
        return "\n".join(
            f"- {a.name} | enabled={a.enabled} | schedule={a.schedule}"
            for a in agents
        )

    if text in ("audit", "audit replay"):
        return replay_audit()

    if text.startswith("enable agent"):
        name = text.replace("enable agent", "").strip()
        agent_store.enable(name)
        return f"✅ Agent '{name}' enabled"

    if text.startswith("disable agent"):
        name = text.replace("disable agent", "").strip()
        agent_store.disable(name)
        return f"⏸️ Agent '{name}' disabled"
    
    if text == "run scheduler":
        return "RUN_SCHEDULER"


    return "Unknown control command."
