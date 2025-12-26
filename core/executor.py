# core/executor.py

from langchain_core.messages import SystemMessage, HumanMessage

class ExecutorAgent:
    def __init__(self, llm, tool_registry, system_prompt: str):
        self.llm = llm
        self.tool_registry = tool_registry
        self.system_prompt = system_prompt

    def execute_plan(self, plan: dict) -> str:
        results = []

        for step in plan.get("steps", []):
            tool_name = step.get("tool")
            description = step.get("description", "")

            # -------- TOOL EXECUTION (GOVERNED) --------
            if tool_name:
                # Approval gate
                if not self.tool_registry.is_allowed(tool_name):
                    results.append(
                        f"[BLOCKED] Tool '{tool_name}' is not approved."
                    )
                    continue

                tool_fn = self.tool_registry.get(tool_name)
                if not tool_fn:
                    results.append(
                        f"[ERROR] Unknown tool: {tool_name}"
                    )
                    continue

                # -------- TOOL SEMANTIC GUARD --------
                if tool_name == "draft_reply" and "essay" in description.lower():
                    results.append(
                        "[BLOCKED] draft_reply is an email tool, not a text writer."
                    )
                    continue

                # -------- ARG INFERENCE (SAFE DEFAULTS) --------
                if tool_name == "search_web":
                    args = {"query": description}
                elif tool_name == "check_inbox":
                    args = {"query": "UNSEEN"}
                else:
                    args = {}

                try:
                    result = tool_fn.invoke(args)
                except Exception as e:
                    result = f"[ERROR] Tool execution failed: {e}"

            # -------- LLM REASONING --------
            else:
                response = self.llm.invoke([
                    SystemMessage(content=self.system_prompt),
                    HumanMessage(content=description)
                ])
                result = response.content

            results.append(str(result))

        return "\n\n".join(results)
