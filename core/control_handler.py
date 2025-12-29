# core/control_handler.py

def handle_system_control(user_input: str) -> str:
    text = user_input.lower()

    if "enable" in text and "scheduler" in text:
        return "Scheduler enable request detected. Background agents must be enabled explicitly via configuration."

    if "disable" in text and "scheduler" in text:
        return "Scheduler disable request detected. No scheduler is currently running."

    if "revoke" in text and "permission" in text:
        return "Permission revocation requires explicit tool or admin interface. No action taken."

    if "remove" in text and "vault" in text:
        return "Credential vault entries cannot be modified via chat. No action taken."

    if "execution_enabled" in text:
        return "Execution mode can only be changed at startup configuration."

    return "System control request acknowledged, but no executable action is available."
