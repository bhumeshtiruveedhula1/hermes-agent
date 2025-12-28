# core/tool_code_generator.py

from langchain_core.messages import SystemMessage, HumanMessage


class ToolCodeGeneratorAgent:
    """
    Generates SAFE Python tool code from an approved tool design.
    NEVER executes code.
    NEVER registers tools automatically.
    """

    def __init__(self, llm):
        self.llm = llm
        self.system_prompt = SystemMessage(content="""
You are ToolCodeGeneratorAgent for Hermes.

Your job:
- Generate Python tool code ONLY
- Use @tool decorator from langchain_core.tools
- Include a proper docstring
- NO credentials
- NO file writes
- NO execution
- Return CODE ONLY

STRICT RULES:
- One function only
- Inputs must be explicit
- Tool must be safe by default
""")

    def generate_code(self, tool_design: dict) -> str:
        prompt = HumanMessage(content=f"""
Generate Python tool code for this approved tool design:

{tool_design}

Return ONLY valid Python code.
""")

        response = self.llm.invoke([
            self.system_prompt,
            prompt
        ])

        return response.content.strip()
