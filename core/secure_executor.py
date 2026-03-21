# core/secure_executor.py

from langchain_core.messages import SystemMessage, HumanMessage
from core.audit.audit_logger import AuditLogger
from core.audit.audit_event import AuditEvent
from core.auto_tool_builder import AutoToolBuilder

FS_TOOLS = {"fs_list", "fs_read", "fs_write", "fs_delete"}
FS_WRITE_TOOLS = {"fs_write", "fs_delete"}
BROWSER_TOOLS = {"browser_go", "browser_read", "browser_click", "browser_fill", "browser_shot", "browser_scroll", "browser_close"}
GMAIL_TOOLS = {"gmail_list", "gmail_read", "gmail_send", "gmail_search"}
CALENDAR_TOOLS = {"calendar_list", "calendar_today", "calendar_search", "calendar_create"}
GITHUB_TOOLS = {"github_repos", "github_issues", "github_prs", "github_commits", "github_create_issue", "github_search", "github_repo_info"}


class SecureExecutor:
    def __init__(
        self,
        llm,
        tool_registry,
        permission_store,
        credential_vault,
        system_prompt: str,
        execution_enabled: bool = False,
        safe_mode: bool = True        # ← NEW
    ):
        self.llm = llm
        self.tool_registry = tool_registry
        self.permission_store = permission_store
        self.credential_vault = credential_vault
        self.system_prompt = system_prompt
        self.audit = AuditLogger()
        self.execution_enabled = execution_enabled
        self.safe_mode = safe_mode    # ← NEW
        self.auto_builder = AutoToolBuilder(llm, tool_registry, safe_mode=safe_mode)  # ← NEW
    def execute_plan(self, plan: dict) -> str:
        results = []

        for step in plan.get("steps", []):
            tool_name = step.get("tool")
            description = step.get("description", "")

            # ---------------- NO TOOL: LLM REASONING ----------------
            if not tool_name:
                response = self.llm.invoke([
                    SystemMessage(content=self.system_prompt),
                    HumanMessage(content=description)
                ])
                self.audit.log(AuditEvent(phase="execution", action="llm_reasoning", decision="allowed", metadata={"description": description[:120]}))
                results.append(response.content)
                continue

            # ---------------- FILESYSTEM TOOLS ----------------
            if tool_name in FS_TOOLS:
                if not self.execution_enabled:
                    self.audit.log(AuditEvent(phase="filesystem", action="tool_call", tool_name=tool_name, decision="blocked", reason="execution_disabled"))
                    results.append("[BLOCKED] Execution disabled by system")
                    continue

                # Write/delete require human approval
                if tool_name in FS_WRITE_TOOLS:
                    from core.filesystem.write_approval import write_approval_prompt
                    import re
                    path_match = re.search(r'(/[^\s]*)', description)
                    clean_path = path_match.group(1) if path_match else description
                    action = "write" if tool_name == "fs_write" else "delete"
                    content = step.get("content", "")
                    approved = write_approval_prompt(action, clean_path, content)
                    if not approved:
                        self.audit.log(AuditEvent(phase="filesystem", action=action, tool_name=tool_name, decision="blocked", reason="user_rejected", metadata={"path": clean_path}))
                        results.append(f"[REJECTED] User denied {action} on {clean_path}")
                        continue

                try:
                    from core.filesystem.capability import FilesystemCapability
                    import re
                    fs = FilesystemCapability()
                    action_map = {"fs_list": "list", "fs_read": "read", "fs_write": "write", "fs_delete": "delete"}
                    action = action_map[tool_name]
                    path_match = re.search(r'(/[^\s]*)', description)
                    clean_path = path_match.group(1) if path_match else description
                    content = step.get("content", "")
                    result = fs.execute(action=action, path=clean_path, user_id="user_1", agent="hermes", content=content)
                    results.append(str(result))
                except Exception as e:
                    results.append(f"[ERROR] Filesystem error: {e}")
                    self.audit.log(AuditEvent(phase="filesystem", action="tool_call", tool_name=tool_name, decision="failed", reason=str(e)))

                continue

            # ---------------- BROWSER TOOLS ----------------
            # ---------------- BROWSER TOOLS ----------------
            if tool_name in BROWSER_TOOLS:
                if not self.execution_enabled:
                    self.audit.log(AuditEvent(phase="browser", action="tool_call", tool_name=tool_name, decision="blocked", reason="execution_disabled"))
                    results.append("[BLOCKED] Execution disabled by system")
                    continue

                try:
                    import re
                    from core.browser.session import BrowserSession
                    browser = BrowserSession.get()

                    # Extract clean URL for browser_go
                    clean_target = description
                    if tool_name == "browser_go":
                        url_match = re.search(r'https?://[^\s]+', description)
                        if url_match:
                            clean_target = url_match.group(0)
                        else:
                            domain_match = re.search(r'[a-zA-Z0-9-]+\.[a-zA-Z.]{2,}[^\s]*', description)
                            clean_target = domain_match.group(0) if domain_match else description

                    action_map = {
                        "browser_go":     ("navigate",   clean_target, ""),
                        "browser_read":   ("get_text",   "", ""),
                        "browser_click":  ("click", description.replace("'", "\\'"), ""),
                        "browser_shot":   ("screenshot", "", ""),
                        "browser_scroll": ("scroll",     description or "down", ""),
                        "browser_close":  ("close",      "", ""),
                        "browser_fill": ("fill",
                            description.split("=")[0].strip() if "=" in description else "input#search",
                            description.split("=", 1)[1].strip() if "=" in description else description),
                    }

                    action, target, value = action_map[tool_name]
                    result = browser.execute(action=action, target=target, value=value)

                    if tool_name == "browser_shot":
                        result = f"[SCREENSHOT_B64]{result}"

                    results.append(str(result))

                except Exception as e:
                    results.append(f"[ERROR] Browser error: {e}")
                    self.audit.log(AuditEvent(phase="browser", action="tool_call", tool_name=tool_name, decision="failed", reason=str(e)))

                continue
            
            # ---------------- GMAIL TOOLS ----------------
            if tool_name in GMAIL_TOOLS:
                if not self.execution_enabled:
                    self.audit.log(AuditEvent(phase="gmail", action="tool_call", tool_name=tool_name, decision="blocked", reason="execution_disabled"))
                    results.append("[BLOCKED] Execution disabled by system")
                    continue

                # Sending email requires approval
                if tool_name == "gmail_send":
                    from colorama import Fore
                    print(Fore.YELLOW + f"\n⚠️  EMAIL SEND APPROVAL")
                    print(Fore.WHITE + f"   Content: {description[:200]}")
                    answer = input(Fore.CYAN + "   Approve send? (yes/no): ").strip().lower()
                    if answer not in ("yes", "y"):
                        results.append("[REJECTED] Email send rejected by user.")
                        continue

                try:
                    from core.integrations.gmail import GmailCapability
                    import re
                    gmail = GmailCapability()

                    if tool_name == "gmail_list":
                        result = gmail.execute(action="list")

                    elif tool_name == "gmail_search":
                        import re
                        # Extract search terms — remove common words
                        query = description
                        for prefix in ["search emails", "search for emails", "find emails", "search", "find"]:
                            if query.lower().startswith(prefix):
                                query = query[len(prefix):].strip()
                        result = gmail.execute(action="search", query=query)

                    elif tool_name == "gmail_read":
                        msg_id = description.strip().split()[-1]
                        result = gmail.execute(action="read", msg_id=msg_id)

                    elif tool_name == "gmail_send":
                        to_match = re.search(r'to=([^\s]+)', description)
                        sub_match = re.search(r'subject=(.+?)(?:body=|$)', description)
                        body_match = re.search(r'body=(.+)', description)
                        result = gmail.execute(
                            action="send",
                            to=to_match.group(1) if to_match else "",
                            subject=sub_match.group(1).strip() if sub_match else "",
                            body=body_match.group(1).strip() if body_match else ""
                        )

                    results.append(str(result))

                except Exception as e:
                    results.append(f"[ERROR] Gmail error: {e}")
                    self.audit.log(AuditEvent(phase="gmail", action="tool_call", tool_name=tool_name, decision="failed", reason=str(e)))

                continue
            # ---------------- CALENDAR TOOLS ----------------
            if tool_name in CALENDAR_TOOLS:
                if not self.execution_enabled:
                    results.append("[BLOCKED] Execution disabled by system")
                    continue
            

                # Creating events requires approval
                if tool_name == "calendar_create":
                    from colorama import Fore
                    print(Fore.YELLOW + f"\n⚠️  CALENDAR CREATE APPROVAL")
                    print(Fore.WHITE + f"   Event: {description[:200]}")
                    answer = input(Fore.CYAN + "   Create this event? (yes/no): ").strip().lower()
                    if answer not in ("yes", "y"):
                        results.append("[REJECTED] Calendar event creation rejected.")
                        continue

                try:
                    from core.integrations.calendar import CalendarCapability
                    cal = CalendarCapability()

                    if tool_name == "calendar_list":
                        result = cal.execute(action="list")
                    elif tool_name == "calendar_today":
                        result = cal.execute(action="today")
                    elif tool_name == "calendar_search":
                        result = cal.execute(action="search", query=description)
                    elif tool_name == "calendar_create":
                        import re
                        # Parse title — stop at "start=" or end of string
                        title_match = re.search(r'title=(.+?)(?:\s+start=|$)', description)
                        # Parse start — stop at "end=" or whitespace boundary
                        start_match = re.search(r'start=([\d\-T:]+)', description)
                        # Parse end
                        end_match = re.search(r'end=([\d\-T:]+)', description)

                        title = title_match.group(1).strip() if title_match else ""
                        start = start_match.group(1).strip() if start_match else ""
                        end = end_match.group(1).strip() if end_match else ""

                        print(f"[CAL DEBUG] title={title} start={start} end={end}")

                        result = cal.execute(
                            action="create",
                            title=title,
                            start=start,
                            end=end,
                        )

                    results.append(str(result))

                except Exception as e:
                    results.append(f"[ERROR] Calendar error: {e}")

                continue
            
            # ---------------- GITHUB TOOLS ----------------
            if tool_name in GITHUB_TOOLS:
                if not self.execution_enabled:
                    results.append("[BLOCKED] Execution disabled by system")
                    continue

                # Creating issues requires approval
                if tool_name == "github_create_issue":
                    from colorama import Fore
                    print(Fore.YELLOW + f"\n⚠️  GITHUB ISSUE APPROVAL")
                    print(Fore.WHITE + f"   {description[:200]}")
                    answer = input(Fore.CYAN + "   Create this issue? (yes/no): ").strip().lower()
                    if answer not in ("yes", "y"):
                        results.append("[REJECTED] Issue creation rejected.")
                        continue

                try:
                    import re
                    from core.integrations.github import GitHubCapability
                    gh = GitHubCapability()

                    if tool_name == "github_repos":
                        result = gh.execute(action="list_repos")

                    elif tool_name == "github_repo_info":
                        repo_match = re.search(r'[\w\-]+/[\w\-\.]+', description)
                        repo = repo_match.group(0) if repo_match else description.strip()
                        result = gh.execute(action="repo_info", repo=repo)

                    elif tool_name == "github_issues":
                        repo_match = re.search(r'[\w\-]+/[\w\-\.]+', description)
                        repo = repo_match.group(0) if repo_match else description.strip()
                        result = gh.execute(action="list_issues", repo=repo)

                    elif tool_name == "github_prs":
                        repo_match = re.search(r'[\w\-]+/[\w\-\.]+', description)
                        repo = repo_match.group(0) if repo_match else description.strip()
                        result = gh.execute(action="list_prs", repo=repo)

                    elif tool_name == "github_commits":
                        repo_match = re.search(r'[\w\-]+/[\w\-\.]+', description)
                        repo = repo_match.group(0) if repo_match else description.strip()
                        result = gh.execute(action="list_commits", repo=repo)

                    elif tool_name == "github_search":
                        result = gh.execute(action="search_repos", query=description)

                    elif tool_name == "github_create_issue":
                        repo_match = re.search(r'repo=([\w\-]+/[\w\-\.]+)', description)
                        title_match = re.search(r'title=(.+?)(?:\s+body=|$)', description)
                        body_match = re.search(r'body=(.+)', description)
                        result = gh.execute(
                            action="create_issue",
                            repo=repo_match.group(1) if repo_match else "",
                            title=title_match.group(1).strip() if title_match else "",
                            body=body_match.group(1).strip() if body_match else ""
                        )

                    results.append(str(result))

                except Exception as e:
                    results.append(f"[ERROR] GitHub error: {e}")
                    self.audit.log(AuditEvent(
                        phase="github", action="tool_call",
                        tool_name=tool_name, decision="failed", reason=str(e)
                    ))

                continue

            # ---------------- TOOL EXISTS ----------------
            # ---------------- PLUGIN TOOLS (dynamic) ----------------
            from core.plugin_loader import PluginLoader
            plugin = PluginLoader.get_plugin_for_tool(tool_name)
            if plugin:
                if not self.execution_enabled:
                    results.append("[BLOCKED] Execution disabled by system")
                    continue

                tool_spec = plugin.get_tool(tool_name)

                if tool_spec and tool_spec.requires_approval:
                    from colorama import Fore
                    print(Fore.YELLOW + f"\n⚠️  PLUGIN APPROVAL REQUIRED")
                    print(Fore.WHITE  + f"   Tool: {tool_name}")
                    print(Fore.WHITE  + f"   Plugin: {plugin.name}")
                    print(Fore.WHITE  + f"   Action: {description[:150]}")
                    answer = input(Fore.CYAN + "   Approve? (yes/no): ").strip().lower()
                    if answer not in ("yes", "y"):
                        results.append(f"[REJECTED] Plugin tool '{tool_name}' rejected.")
                        continue

                result = plugin.execute(tool_name, description, step)
                results.append(str(result))
                continue

            # ---------------- TOOL EXISTS ----------------
            if not self.tool_registry.get(tool_name):
                built = self.auto_builder.attempt(tool_name, description)

                if built:
                    response = self.llm.invoke([
                        SystemMessage(content=self.system_prompt),
                        HumanMessage(content=f"Execute this task using tool '{tool_name}': {description}")
                    ])
                    self.audit.log(AuditEvent(
                        phase="auto_build", action="tool_execution",
                        tool_name=tool_name, decision="executed",
                        metadata={"description": description[:120]}
                    ))
                    results.append(f"[AUTO-TOOL: {tool_name}]\n{response.content}")
                else:
                    self.audit.log(AuditEvent(
                        phase="execution", action="tool_call",
                        tool_name=tool_name, decision="blocked",
                        reason="unknown_tool"
                    ))
                    results.append(f"[BLOCKED] Unknown tool: {tool_name}")
                continue

            # ---------------- TOOL APPROVED ----------------
            if not self.tool_registry.is_allowed(tool_name):
                self.audit.log(AuditEvent(phase="execution", action="tool_call", tool_name=tool_name, decision="blocked", reason="tool_not_approved"))
                results.append(f"[BLOCKED] Tool not approved: {tool_name}")
                continue

            # ---------------- PERMISSION CHECK ----------------
            required_permission = "default"
            if not self.permission_store.has_permission(tool_name, required_permission):
                self.audit.log(AuditEvent(phase="execution", action="tool_call", tool_name=tool_name, decision="blocked", reason="permission_denied", metadata={"required_permission": required_permission}))
                results.append(f"[BLOCKED] Permission '{required_permission}' not granted for {tool_name}")
                continue

            # ---------------- CREDENTIAL CHECK ----------------
            if self.tool_registry._tools[tool_name].requires_credentials:
                if not self.credential_vault.has_credentials(tool_name):
                    self.audit.log(AuditEvent(phase="execution", action="tool_call", tool_name=tool_name, decision="blocked", reason="missing_credentials"))
                    results.append(f"[BLOCKED] Missing credentials for tool: {tool_name}")
                    continue

            # ================== 🔒 EXECUTION GATE ==================
            if not self.execution_enabled:
                self.audit.log(AuditEvent(phase="execution", action="tool_call", tool_name=tool_name, decision="blocked", reason="execution_disabled"))
                results.append("[BLOCKED] Execution disabled by system")
                continue

            # ---------------- REAL TOOL EXECUTION ----------------
            try:
                credentials = {}
                if self.tool_registry._tools[tool_name].requires_credentials:
                    credentials = self.credential_vault.inject(tool_name)
                tool_fn = self.tool_registry.get(tool_name)
                if tool_name == "speak_out_loud":
                    payload = {"text": description}
                else:
                    payload = {**credentials, "query": description}
                result = tool_fn.invoke(payload)
                results.append(str(result))
                self.audit.log(AuditEvent(phase="execution", action="tool_call", tool_name=tool_name, decision="executed", reason="success"))
            except Exception as e:
                results.append(f"[ERROR] Tool execution failed: {e}")
                self.audit.log(AuditEvent(phase="execution", action="tool_call", tool_name=tool_name, decision="failed", reason=str(e)))

        return "\n\n".join(results)
