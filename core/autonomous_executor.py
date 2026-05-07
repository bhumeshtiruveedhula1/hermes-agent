# core/autonomous_executor.py — Phase 15: Autonomous Mission Executor
# Runs a full multi-step mission without user prompting between steps.
# Each step's result is injected as context for subsequent reasoning.

import asyncio
from datetime import datetime, timezone
from typing import Callable, Optional


APPROVAL_TOOLS = {
    "fs_write", "fs_delete",
    "gmail_send", "calendar_create",
    "telegram_send", "github_create_issue",
    "whatsapp_send", "notion_create", "notion_append", "slack_send",
}


class AutonomousExecutor:
    """
    Executes multi-step plans autonomously.

    Flow:
      1. Build full plan from mission prompt via planner + critic.
      2. Broadcast plan_ready with step count.
      3. For each step:
         a. Broadcast step_start.
         b. Request approval if tool is sensitive.
         c. Execute via SecureExecutor.execute_plan (single-step dict).
         d. Broadcast step_done with result preview.
      4. Broadcast mission_complete.

    Returns a structured dict consumed by the /api/mission/run endpoint.
    Stateless — safe to share one instance across all requests.
    """

    def __init__(self, planner, critic, executor, broadcast_fn: Callable):
        self.planner   = planner
        self.critic    = critic
        self.executor  = executor
        self.broadcast = broadcast_fn

    # ── Public ──────────────────────────────────────────────────────────

    async def run_mission(
        self,
        mission_prompt: str,
        conv_id: str,
        user_id: str,
        approval_fn: Optional[Callable] = None,
        max_steps: int = 10,
    ) -> dict:
        """
        Run a complete autonomous mission.

        Returns:
            {success, steps_taken, results, final_output}
        """
        results      = []
        final_output = ""

        await self.broadcast({
            "type": "mission_started",
            "conv_id": conv_id,
            "prompt": mission_prompt[:200],
            "ts": _now(),
        })

        # ── Plan ────────────────────────────────────────────────────────
        try:
            raw_plan = self.planner.create_plan(mission_prompt)
            plan     = self.critic.review_plan(raw_plan)
        except Exception as e:
            await self.broadcast({
                "type": "mission_failed",
                "conv_id": conv_id,
                "error": f"Planning failed: {e}",
                "ts": _now(),
            })
            return _failure(f"Planning failed: {e}")

        steps = plan.get("steps", [])
        if not steps:
            await self.broadcast({
                "type": "mission_failed",
                "conv_id": conv_id,
                "error": "Planner returned empty plan",
                "ts": _now(),
            })
            return _failure("Planner returned empty plan")

        await self.broadcast({
            "type": "mission_plan_ready",
            "conv_id": conv_id,
            "goal":       plan.get("goal", ""),
            "step_count": len(steps),
            "ts": _now(),
        })

        # ── Execute steps ────────────────────────────────────────────────
        for i, step in enumerate(steps[:max_steps]):
            tool        = step.get("tool") or ""
            description = step.get("description", "")

            await self.broadcast({
                "type":        "mission_step_start",
                "conv_id":     conv_id,
                "step":        i + 1,
                "total":       min(len(steps), max_steps),
                "tool":        tool,
                "description": description[:150],
                "ts":          _now(),
            })

            # Approval gate for sensitive tools
            if tool in APPROVAL_TOOLS and approval_fn:
                try:
                    approved = await approval_fn(tool, description, conv_id)
                except Exception:
                    approved = False
                if not approved:
                    step["tool"]        = None
                    step["description"] = f"[REJECTED] User denied {tool}"
                    tool = None

            # Run single step through existing SecureExecutor in thread pool
            # (execute_plan is sync — must not block the async event loop)
            single_plan = {"goal": description, "steps": [step]}
            try:
                loop   = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None, self.executor.execute_plan, single_plan
                )
            except Exception as e:
                result = f"[ERROR] Step {i+1} failed: {e}"

            result = str(result)
            results.append({
                "step":        i + 1,
                "tool":        tool,
                "description": description,
                "result":      result,
            })
            final_output = result

            # Bug 7 fix — inject result into next step if it needs context
            if i < len(steps) - 1 and result and not result.startswith("[ERROR]"):
                next_step = steps[i + 1]
                next_desc = next_step.get("description", "")
                CONTEXT_KEYWORDS = {"save", "write", "send", "summary", "result",
                                     "summarize", "report", "append", "create", "post"}
                if any(kw in next_desc.lower() for kw in CONTEXT_KEYWORDS):
                    next_step["description"] = (
                        f"{next_desc} "
                        f"[Context from previous step: {result[:400]}]"
                    )

            await self.broadcast({
                "type":    "mission_step_done",
                "conv_id": conv_id,
                "step":    i + 1,
                "tool":    tool,
                "result":  result[:300],
                "ts":      _now(),
            })

        await self.broadcast({
            "type":         "mission_complete",
            "conv_id":      conv_id,
            "steps_taken":  len(results),
            "final_output": final_output[:500],
            "ts":           _now(),
        })

        return {
            "success":      True,
            "steps_taken":  len(results),
            "results":      results,
            "final_output": final_output,
        }


# ── Helpers ──────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _failure(reason: str) -> dict:
    return {
        "success":      False,
        "steps_taken":  0,
        "results":      [],
        "final_output": reason,
    }
