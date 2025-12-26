# core/summarizer.py

from langchain_core.messages import SystemMessage, HumanMessage

class MemorySummarizer:
    def __init__(self, llm):
        self.llm = llm

    def summarize_session(self, session_messages: list) -> str:
        prompt = [
            SystemMessage(content="""
You summarize AI assistant sessions.

Rules:
- Extract only long-term useful knowledge
- Ignore chit-chat
- Focus on decisions, preferences, outcomes
- Be concise
"""),
            HumanMessage(content=str(session_messages))
        ]

        response = self.llm.invoke(prompt)
        return response.content.strip()
