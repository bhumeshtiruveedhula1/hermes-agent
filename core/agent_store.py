# core/agent_store.py

import json
from pathlib import Path
from typing import List
from datetime import datetime

from core.scheduler.scheduled_agent import ScheduledAgent


AGENT_STORE_PATH = Path("memory/agents.json")


class AgentStore:
    def __init__(self):
        self._agents: List[ScheduledAgent] = []
        self._load()

    # ---------------- PERSISTENCE ----------------

    def _load(self):
        if not AGENT_STORE_PATH.exists():
            self._agents = []
            return

        with open(AGENT_STORE_PATH, "r") as f:
            raw = json.load(f)

        agents = []
        for a in raw:
            agents.append(
                ScheduledAgent(
                    name=a["name"],
                    tool_name=a["tool_name"],
                    schedule=a["schedule"],
                    permissions=a["permissions"],
                    enabled=a["enabled"],
                    last_run_at=datetime.fromisoformat(a["last_run_at"])
                    if a["last_run_at"]
                    else None,
                )
            )

        self._agents = agents

    def _save(self):
        AGENT_STORE_PATH.parent.mkdir(exist_ok=True)

        with open(AGENT_STORE_PATH, "w") as f:
            json.dump(
                [
                    {
                        "name": a.name,
                        "tool_name": a.tool_name,
                        "schedule": a.schedule,
                        "permissions": a.permissions,
                        "enabled": a.enabled,
                        "last_run_at": a.last_run_at.isoformat()
                        if a.last_run_at
                        else None,
                    }
                    for a in self._agents
                ],
                f,
                indent=2,
            )

    # ---------------- API ----------------

    def register(self, agent: ScheduledAgent):
        if self.get(agent.name):
            raise ValueError(f"Agent '{agent.name}' already exists")

        self._agents.append(agent)
        self._save()

    def enable(self, name: str):
        agent = self.get(name)
        if not agent:
            raise ValueError(f"Agent '{name}' not found")
        agent.enabled = True
        self._save()

    def disable(self, name: str):
        agent = self.get(name)
        if not agent:
            raise ValueError(f"Agent '{name}' not found")
        agent.enabled = False
        self._save()

    def list_all(self) -> List[ScheduledAgent]:
        return list(self._agents)

    def get(self, name: str):
        for a in self._agents:
            if a.name == name:
                return a
        return None
