# core/tool_args.py

def infer_tool_args(tool_name: str, description: str) -> dict:
    if tool_name == "search_web":
        return { "query": description }

    if tool_name == "draft_reply":
        return {
            "to_address": "unknown",
            "subject": "Draft",
            "body": description
        }

    if tool_name == "check_inbox":
        return { "query": "UNSEEN" }

    if tool_name == "speak_out_loud":
        return { "text": description }

    return {}
