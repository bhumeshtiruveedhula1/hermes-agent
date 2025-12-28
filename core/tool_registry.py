# core/tool_registry.py
from dataclasses import dataclass
from typing import Dict, Callable

@dataclass
class ToolMeta:
    name: str
    function: Callable
    approved: bool = True
    source: str = "builtin"  # builtin | generated
    requires_credentials: bool = False


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolMeta] = {}

    def register(self, meta: ToolMeta):
        self._tools[meta.name] = meta

    def is_allowed(self, name: str) -> bool:
        tool = self._tools.get(name)
        return tool is not None and tool.approved

    def get(self, name: str):
        tool = self._tools.get(name)
        return tool.function if tool else None

    def list_tools(self):
        return list(self._tools.keys())
    # add inside ToolRegistry class

    def register_generated_tool(self, name: str, function):
        self.register(
            ToolMeta(
                name=name,
                function=function,
                approved=False,      # 🔒 always false initially
                source="generated",
                requires_credentials=False
            )
        )

