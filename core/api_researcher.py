# core/api_researcher.py — Phase 16: Auto-Integration Builder
# Used ONLY for unknown integrations not in integration_knowledge.py.
# Searches the web and extracts API details via LLM extraction.
#
# Pattern: mirrors tools_web.search_web usage from existing codebase.
# LLM call pattern: mirrors plugin_designer.py (SystemMessage + HumanMessage).

import json
from langchain_core.messages import SystemMessage, HumanMessage


class APIResearcher:
    """
    Researches an unknown API using web search + LLM structured extraction.
    Returns a dict usable directly by IntegrationBuilder.build().
    """

    def __init__(self, llm, search_fn):
        """
        llm       : the Qwen LLM instance (same as planner/plugin_designer uses)
        search_fn : tools_web.search_web — the existing search tool
        """
        self.llm    = llm
        self.search = search_fn

    def research(self, integration_name: str) -> dict:
        """
        Research an unknown API and return structured integration info.

        Returns dict with keys:
          pip_packages, env_vars, auth_type, zero_cred,
          base_url, key_endpoints, free_tier, notes
        """
        print(f"[RESEARCHER] Researching: {integration_name}")

        # Two targeted web searches — broad docs + auth/pricing specifics
        try:
            search1 = self.search.invoke(
                {"query": f"{integration_name} Python API package documentation quickstart"}
            )
        except Exception as e:
            search1 = f"Search failed: {e}"

        try:
            search2 = self.search.invoke(
                {"query": f"{integration_name} API authentication key free tier sign up"}
            )
        except Exception as e:
            search2 = f"Search failed: {e}"

        combined = f"SEARCH 1 (docs + packages):\n{search1}\n\nSEARCH 2 (auth + pricing):\n{search2}"

        extraction_prompt = f"""
You are extracting API integration information for: {integration_name}

From the search results below, extract EXACTLY this JSON structure.
Output ONLY valid JSON. No explanation. No markdown fences.

{{
  "pip_packages": ["package_name"],
  "auth_type": "api_key | oauth | bearer | none",
  "zero_cred": false,
  "env_vars": {{
    "SERVICE_API_KEY": {{
      "description": "what this variable is",
      "where": "step-by-step instructions to get it",
      "example": "example format or value"
    }}
  }},
  "base_url": "https://api.example.com/v1",
  "key_endpoints": [
    {{
      "name": "action_name",
      "method": "GET",
      "path": "/endpoint",
      "description": "what this endpoint does"
    }}
  ],
  "free_tier": true,
  "notes": "rate limits, sandboxes, premium requirements, important gotchas"
}}

Rules:
- If auth_type is "none", set zero_cred to true and env_vars to {{}}
- Use SCREAMING_SNAKE_CASE for env var key names (e.g. OPENAI_API_KEY)
- pip_packages must be real PyPI package names that can be pip-installed
- List 3-6 key_endpoints covering the most useful read + write actions
- If the API has no free tier, set free_tier to false and note it
- Do NOT use null — use empty string "" or empty list [] as defaults

Search results:
{combined[:3500]}
"""
        response = self.llm.invoke([
            SystemMessage(content=(
                "You extract API metadata into clean JSON. "
                "Output JSON only — no preamble, no explanation, no markdown. "
                "/no_think"
            )),
            HumanMessage(content=extraction_prompt)
        ])

        raw = response.content.strip()

        # Strip markdown fences if model added them despite instructions
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        try:
            result = json.loads(raw)
            print(
                f"[RESEARCHER] Extracted: packages={result.get('pip_packages')}, "
                f"auth={result.get('auth_type')}, zero_cred={result.get('zero_cred')}"
            )
            # Ensure all expected keys exist with sensible defaults
            result.setdefault("pip_packages", ["requests"])
            result.setdefault("auth_type",    "api_key")
            result.setdefault("zero_cred",    False)
            result.setdefault("env_vars",     {})
            result.setdefault("base_url",     "")
            result.setdefault("key_endpoints",[])
            result.setdefault("free_tier",    True)
            result.setdefault("notes",        "")
            return result

        except json.JSONDecodeError as e:
            print(f"[RESEARCHER] JSON parse failed: {e}. Using safe fallback.")
            # Return a safe, actionable fallback so the pipeline can continue
            env_key = f"{integration_name.upper().replace('-','_').replace(' ','_')}_API_KEY"
            return {
                "pip_packages": ["requests"],
                "auth_type":    "api_key",
                "zero_cred":    False,
                "env_vars": {
                    env_key: {
                        "description": f"API key for {integration_name}",
                        "where": (
                            f"Sign up at the {integration_name} website and "
                            f"navigate to API / Developer settings to get your key"
                        ),
                        "example": "your_api_key_here"
                    }
                },
                "base_url":      f"https://api.{integration_name.lower().replace(' ','-')}.com/v1",
                "key_endpoints": [
                    {
                        "name":        f"{integration_name.lower().replace(' ','_')}_query",
                        "method":      "GET",
                        "path":        "/query",
                        "description": f"Query the {integration_name} API"
                    }
                ],
                "free_tier": True,
                "notes": (
                    f"Research extraction failed for '{integration_name}'. "
                    "The generated code is a best-effort template — review and edit "
                    "core/integrations/{integration_name}.py before activating."
                )
            }
