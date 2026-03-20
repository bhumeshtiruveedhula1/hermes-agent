# core/scheduler/scheduler.py

import time
from datetime import datetime, timedelta
from typing import Callable, List

from core.scheduler.scheduled_agent import ScheduledAgent
from core.audit.audit_logger import AuditLogger
from core.audit.audit_event import AuditEvent


class Scheduler:
    def __init__(self, executor, agent_provider: Callable[[], List[ScheduledAgent]]):
        self.executor = executor
        self.agent_provider = agent_provider
        self.audit = AuditLogger()

    def _is_due(self, agent: ScheduledAgent) -> bool:
        now = datetime.utcnow()

        if agent.schedule == "daily":
            return agent.last_run_at is None or now.date() > agent.last_run_at.date()

        if agent.schedule.startswith("interval:"):
            minutes = int(agent.schedule.split(":")[1])
            return agent.last_run_at is None or now - agent.last_run_at >= timedelta(minutes=minutes)

        return False

    def _build_plan(self, agent: ScheduledAgent) -> dict:
        if agent.tool_name == "fs_list":
            path = agent.metadata.get("path", "/documents") if agent.metadata else "/documents"
            return {
                "goal": f"Monitor folder: {path}",
                "steps": [{
                    "step_id": "scheduled-fs-list",
                    "description": path,
                    "tool": "fs_list"
                }]
            }

        if agent.tool_name == "fs_read":
            path = agent.metadata.get("path", "/documents") if agent.metadata else "/documents"
            return {
                "goal": f"Read file: {path}",
                "steps": [{
                    "step_id": "scheduled-fs-read",
                    "description": path,
                    "tool": "fs_read"
                }]
            }

        return {
            "goal": f"Run scheduled agent {agent.name}",
            "steps": [{
                "step_id": "scheduled-run",
                "description": "Scheduled execution",
                "tool": agent.tool_name
            }]
        }

    def run_once(self):
        agents = self.agent_provider()

        for agent in agents:
            if not agent.enabled:
                continue
            if not self._is_due(agent):
                continue

            self.audit.log(AuditEvent(
                phase="background_execution",
                action="schedule_tick",
                tool_name=agent.tool_name,
                decision="attempted",
                metadata={"agent": agent.name}
            ))

            try:
                plan = self._build_plan(agent)
                result = self.executor.execute_plan(plan)
                agent.last_run_at = datetime.utcnow()

                print(f"\n📁 [{agent.name}] result: {result}")

                self.audit.log(AuditEvent(
                    phase="background_execution",
                    action="schedule_run",
                    tool_name=agent.tool_name,
                    decision="completed",
                    metadata={"agent": agent.name, "preview": str(result)[:200]}
                ))

            except Exception as e:
                self.audit.log(AuditEvent(
                    phase="background_execution",
                    action="schedule_run",
                    tool_name=agent.tool_name,
                    decision="failed",
                    reason=str(e),
                    metadata={"agent": agent.name}
                ))