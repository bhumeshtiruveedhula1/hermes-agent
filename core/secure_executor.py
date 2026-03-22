# core/secure_executor.py

from langchain_core.messages import SystemMessage, HumanMessage
from core.audit.audit_logger import AuditLogger
from core.audit.audit_event import AuditEvent
from core.auto_tool_builder import AutoToolBuilder

FS_TOOLS      = {"fs_list", "fs_read", "fs_write", "fs_delete"}
FS_WRITE_TOOLS= {"fs_write", "fs_delete"}
BROWSER_TOOLS = {"browser_go", "browser_read", "browser_click", "browser_fill", "browser_shot", "browser_scroll", "browser_close"}
GMAIL_TOOLS   = {"gmail_list", "gmail_read", "gmail_send", "gmail_search"}
CALENDAR_TOOLS= {"calendar_list", "calendar_today", "calendar_search", "calendar_create"}
GITHUB_TOOLS  = {"github_repos", "github_issues", "github_prs", "github_commits", "github_create_issue", "github_search", "github_repo_info"}


class SecureExecutor:
    def __init__(self, llm, tool_registry, permission_store, credential_vault,
                 system_prompt: str, execution_enabled: bool = False, safe_mode: bool = True):
        self.llm              = llm
        self.tool_registry    = tool_registry
        self.permission_store = permission_store
        self.credential_vault = credential_vault
        self.system_prompt    = system_prompt
        self.audit            = AuditLogger()
        self.execution_enabled= execution_enabled
        self.safe_mode        = safe_mode
        self.auto_builder     = AutoToolBuilder(llm, tool_registry, safe_mode=safe_mode)

    def execute_plan(self, plan: dict) -> str:
        results = []

        for step in plan.get("steps", []):
            tool_name   = step.get("tool")
            description = step.get("description", "")

            # ── NO TOOL ──────────────────────────────────────────────
            if not tool_name:
                response = self.llm.invoke([
                    SystemMessage(content=self.system_prompt),
                    HumanMessage(content=description)
                ])
                self.audit.log(AuditEvent(phase="execution", action="llm_reasoning",
                    decision="allowed", metadata={"description": description[:120]}))
                results.append(response.content)
                continue

            # ── FILESYSTEM ───────────────────────────────────────────
            if tool_name in FS_TOOLS:
                if not self.execution_enabled:
                    results.append("[BLOCKED] Execution disabled by system")
                    continue
                try:
                    from core.filesystem.capability import FilesystemCapability
                    import re
                    fs         = FilesystemCapability()
                    action_map = {"fs_list":"list","fs_read":"read","fs_write":"write","fs_delete":"delete"}
                    action     = action_map[tool_name]
                    path_match = re.search(r'(/[^\s]+)', description)
                    clean_path = path_match.group(1) if path_match else f"/documents/{description.strip()}"

                    content = step.get("content", "")
                    if not content and tool_name == "fs_write":
                        quote_match = re.search(r'["\'](.+?)["\']', description)
                        content = quote_match.group(1) if quote_match else ""

                    result = fs.execute(action=action, path=clean_path,
                                        user_id="user_1", agent="hermes", content=content)

                    if tool_name == "fs_read" and result and not result.startswith("["):
                        result = f"Contents of {clean_path}:\n{result}"

                    results.append(str(result))
                except Exception as e:
                    results.append(f"[ERROR] Filesystem error: {e}")
                    self.audit.log(AuditEvent(phase="filesystem", action="tool_call",
                        tool_name=tool_name, decision="failed", reason=str(e)))
                continue   # ← CRITICAL — was missing before!

            # ── BROWSER ──────────────────────────────────────────────
            if tool_name in BROWSER_TOOLS:
                if not self.execution_enabled:
                    results.append("[BLOCKED] Execution disabled by system")
                    continue
                try:
                    import re
                    from core.browser.session import BrowserSession
                    browser = BrowserSession.get()

                    clean_target = description
                    if tool_name == "browser_go":
                        url_match = re.search(r'https?://[^\s]+', description)
                        clean_target = url_match.group(0) if url_match else description

                    action_map = {
                        "browser_go":     ("navigate",   clean_target, ""),
                        "browser_read":   ("get_text",   "", ""),
                        "browser_click":  ("click",      description.replace("'", "\\'"), ""),
                        "browser_shot":   ("screenshot", "", ""),
                        "browser_scroll": ("scroll",     description or "down", ""),
                        "browser_close":  ("close",      "", ""),
                        "browser_fill":   ("fill",
                            description.split("=")[0].strip() if "=" in description else "input#search",
                            description.split("=",1)[1].strip() if "=" in description else description),
                    }
                    action, target, value = action_map[tool_name]
                    result = browser.execute(action=action, target=target, value=value)
                    if tool_name == "browser_shot":
                        result = f"[SCREENSHOT_B64]{result}"
                    results.append(str(result))
                except Exception as e:
                    results.append(f"[ERROR] Browser error: {e}")
                    self.audit.log(AuditEvent(phase="browser", action="tool_call",
                        tool_name=tool_name, decision="failed", reason=str(e)))
                continue

            # ── GMAIL ────────────────────────────────────────────────
            if tool_name in GMAIL_TOOLS:
                if not self.execution_enabled:
                    results.append("[BLOCKED] Execution disabled by system")
                    continue
                try:
                    from core.integrations.gmail import GmailCapability
                    import re
                    gmail = GmailCapability()
                    if tool_name == "gmail_list":
                        result = gmail.execute(action="list")
                    elif tool_name == "gmail_search":
                        query = description
                        for prefix in ["search emails","search for emails","find emails","search","find"]:
                            if query.lower().startswith(prefix):
                                query = query[len(prefix):].strip()
                        result = gmail.execute(action="search", query=query)
                    elif tool_name == "gmail_read":
                        msg_id = description.strip().split()[-1]
                        result = gmail.execute(action="read", msg_id=msg_id)
                    elif tool_name == "gmail_send":
                        to_m   = re.search(r'to=([^\s]+)', description)
                        sub_m  = re.search(r'subject=(.+?)(?:body=|$)', description)
                        body_m = re.search(r'body=(.+)', description)
                        result = gmail.execute(action="send",
                            to=to_m.group(1) if to_m else "",
                            subject=sub_m.group(1).strip() if sub_m else "",
                            body=body_m.group(1).strip() if body_m else "")
                    results.append(str(result))
                except Exception as e:
                    results.append(f"[ERROR] Gmail error: {e}")
                    self.audit.log(AuditEvent(phase="gmail", action="tool_call",
                        tool_name=tool_name, decision="failed", reason=str(e)))
                continue

            # ── CALENDAR ─────────────────────────────────────────────
            if tool_name in CALENDAR_TOOLS:
                if not self.execution_enabled:
                    results.append("[BLOCKED] Execution disabled by system")
                    continue
                try:
                    from core.integrations.calendar import CalendarCapability
                    import re
                    cal = CalendarCapability()
                    if tool_name == "calendar_list":
                        result = cal.execute(action="list")
                    elif tool_name == "calendar_today":
                        result = cal.execute(action="today")
                    elif tool_name == "calendar_search":
                        result = cal.execute(action="search", query=description)
                    elif tool_name == "calendar_create":
                        title_m = re.search(r'title=(.+?)(?:\s+start=|$)', description)
                        start_m = re.search(r'start=([\d\-T:]+)', description)
                        end_m   = re.search(r'end=([\d\-T:]+)', description)
                        result  = cal.execute(action="create",
                            title=title_m.group(1).strip() if title_m else "",
                            start=start_m.group(1).strip() if start_m else "",
                            end=end_m.group(1).strip() if end_m else "")
                    results.append(str(result))
                except Exception as e:
                    results.append(f"[ERROR] Calendar error: {e}")
                continue

            # ── GITHUB ───────────────────────────────────────────────
            if tool_name in GITHUB_TOOLS:
                if not self.execution_enabled:
                    results.append("[BLOCKED] Execution disabled by system")
                    continue
                try:
                    import re
                    from core.integrations.github import GitHubCapability
                    gh = GitHubCapability()
                    repo_m = re.search(r'[\w\-]+/[\w\-\.]+', description)
                    repo   = repo_m.group(0) if repo_m else description.strip()
                    if tool_name == "github_repos":
                        result = gh.execute(action="list_repos")
                    elif tool_name == "github_repo_info":
                        result = gh.execute(action="repo_info", repo=repo)
                    elif tool_name == "github_issues":
                        result = gh.execute(action="list_issues", repo=repo)
                    elif tool_name == "github_prs":
                        result = gh.execute(action="list_prs", repo=repo)
                    elif tool_name == "github_commits":
                        result = gh.execute(action="list_commits", repo=repo)
                    elif tool_name == "github_search":
                        result = gh.execute(action="search_repos", query=description)
                    elif tool_name == "github_create_issue":
                        repo_m2  = re.search(r'repo=([\w\-]+/[\w\-\.]+)', description)
                        title_m  = re.search(r'title=(.+?)(?:\s+body=|$)', description)
                        body_m   = re.search(r'body=(.+)', description)
                        result   = gh.execute(action="create_issue",
                            repo=repo_m2.group(1) if repo_m2 else "",
                            title=title_m.group(1).strip() if title_m else "",
                            body=body_m.group(1).strip() if body_m else "")
                    results.append(str(result))
                except Exception as e:
                    results.append(f"[ERROR] GitHub error: {e}")
                    self.audit.log(AuditEvent(phase="github", action="tool_call",
                        tool_name=tool_name, decision="failed", reason=str(e)))
                continue

            # ── PLUGIN TOOLS ─────────────────────────────────────────
            from core.plugin_loader import PluginLoader
            plugin = PluginLoader.get_plugin_for_tool(tool_name)
            if plugin:
                if not self.execution_enabled:
                    results.append("[BLOCKED] Execution disabled by system")
                    continue
                result = plugin.execute(tool_name, description, step)
                results.append(str(result))
                continue

            # ── AUTO BUILDER ─────────────────────────────────────────
            if not self.tool_registry.get(tool_name):
                built = self.auto_builder.attempt(tool_name, description)
                if built:
                    response = self.llm.invoke([
                        SystemMessage(content=self.system_prompt),
                        HumanMessage(content=f"Execute this task using tool '{tool_name}': {description}")
                    ])
                    self.audit.log(AuditEvent(phase="auto_build", action="tool_execution",
                        tool_name=tool_name, decision="executed",
                        metadata={"description": description[:120]}))
                    results.append(f"[AUTO-TOOL: {tool_name}]\n{response.content}")
                else:
                    self.audit.log(AuditEvent(phase="execution", action="tool_call",
                        tool_name=tool_name, decision="blocked", reason="unknown_tool"))
                    results.append(f"[BLOCKED] Unknown tool: {tool_name}")
                continue

            # ── TOOL APPROVED ────────────────────────────────────────
            if not self.tool_registry.is_allowed(tool_name):
                results.append(f"[BLOCKED] Tool not approved: {tool_name}")
                continue

            # ── PERMISSION CHECK ─────────────────────────────────────
            if not self.permission_store.has_permission(tool_name, "default"):
                results.append(f"[BLOCKED] Permission not granted for {tool_name}")
                continue

            # ── CREDENTIAL CHECK ─────────────────────────────────────
            if self.tool_registry._tools[tool_name].requires_credentials:
                if not self.credential_vault.has_credentials(tool_name):
                    results.append(f"[BLOCKED] Missing credentials for tool: {tool_name}")
                    continue

            # ── EXECUTION GATE ───────────────────────────────────────
            if not self.execution_enabled:
                results.append("[BLOCKED] Execution disabled by system")
                continue

            # ── REAL TOOL EXECUTION ──────────────────────────────────
            try:
                credentials = {}
                if self.tool_registry._tools[tool_name].requires_credentials:
                    credentials = self.credential_vault.inject(tool_name)
                tool_fn = self.tool_registry.get(tool_name)
                payload = {"text": description} if tool_name == "speak_out_loud" \
                          else {**credentials, "query": description}
                result  = tool_fn.invoke(payload)
                results.append(str(result))
                self.audit.log(AuditEvent(phase="execution", action="tool_call",
                    tool_name=tool_name, decision="executed", reason="success"))
            except Exception as e:
                results.append(f"[ERROR] Tool execution failed: {e}")
                self.audit.log(AuditEvent(phase="execution", action="tool_call",
                    tool_name=tool_name, decision="failed", reason=str(e)))

        return "\n\n".join(results)
