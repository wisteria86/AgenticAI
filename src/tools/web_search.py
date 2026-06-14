from langchain_core.tools import tool
from duckduckgo_search import DDGS

@tool
def search_internet(query: str) -> str:
    """
    Search the internet using DuckDuckGo to answer questions or find information.
    
    Args:
        query: The search query string.
        
    Returns:
        A formatted string of the top search results.
    """
    try:
        results = DDGS().text(query, max_results=5)
        if not results:
            return "No results found."
        
        formatted_results = []
        for r in results:
            formatted_results.append(f"Title: {r['title']}\nURL: {r['href']}\nSnippet: {r['body']}\n")
        
        return "\n".join(formatted_results)
    except Exception as e:
        return f"Error performing search: {str(e)}"
