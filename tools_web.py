# tools_web.py
from langchain_core.tools import tool
from duckduckgo_search import DDGS

@tool
def search_web(query: str):
    """
    POWER TOOL: Searches the internet for English content.
    USE RULES:
    1. ALWAYS use this if the user asks for current events, news, or specific topics.
    2. Use this to gather facts before writing an essay.
    """
    try:
        print(f"   (Tool: Deep Searching Web for '{query}'...)")
        results = []
        
        # FIX: backend='lite' bypasses the API location glitches
        with DDGS() as ddgs:
            search_results = ddgs.text(
                query, 
                region="wt-wt",    # 'wt-wt' = No Region (Global), avoids local dictionary lookups
                safesearch="off", 
                timelimit="y",     # Past year
                backend="lite",    # <--- THE FIX: Uses lite.duckduckgo.com
                max_results=5
            )
            
            for r in search_results:
                results.append(f"SOURCE: {r['title']}\nCONTENT: {r['body']}\nLINK: {r['href']}")
        
        if not results:
            return "No results found. Try a broader query."
            
        return "\n\n".join(results)
    except Exception as e:
        return f"Search Error: {e}"