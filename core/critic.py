# core/critic.py

import json
from langchain_core.messages import SystemMessage, HumanMessage

class CriticAgent:
    def __init__(self, llm):
        self.llm = llm
        self.system_prompt = SystemMessage(content="""
You are the CRITIC agent.

Your job is to FIX execution plans.

Input: a JSON plan (may be imperfect)
Output: a corrected plan in EXACTLY this format:

{
  "goal": "<goal>",
  "steps": [
    {
      "step_id": "<string>",
      "description": "<string>",
      "tool": "<tool_name or null>"
    }
  ]
}
tool usage
- Replace invalid tool names with correct ones if intent is clear.
- If email reading is requested, use "check_inbox".
- If drafting email is requested, use "draft_reply".
- Remove steps that are not executable.


RULES:
- Output JSON ONLY.
- Remove extra fields.
- Rename keys if needed.
- Add missing 'tool' fields (use null).
- Ensure steps are executable.
""")

    def review_plan(self, plan: dict) -> dict:
        messages = [
            self.system_prompt,
            HumanMessage(content=json.dumps(plan))
        ]
        response = self.llm.invoke(messages)
        return json.loads(response.content)
