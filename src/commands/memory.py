from src.services.memory_store import MemoryManager

def handle_memory(args: str) -> str:
    """
    Interact with the vector database.
    """
    if not args:
        return "Usage: `/memory search <query>` or `/memory add <text>`"
        
    parts = args.split(maxsplit=1)
    action = parts[0].lower()
    
    try:
        memory = MemoryManager()
    except Exception as e:
        return f"Failed to initialize memory manager: {e}"
        
    if action == "search":
        if len(parts) < 2:
            return "Usage: `/memory search <query>`"
        query = parts[1]
        results = memory.retrieve_memory(query)
        if not results:
            return "No memories found."
        
        # Format the results
        if isinstance(results, list):
            formatted_results = "\n- ".join(results)
        else:
            formatted_results = str(results)
            
        return f"**Found Memories:**\n- {formatted_results}"
        
    elif action == "add":
        if len(parts) < 2:
            return "Usage: `/memory add <text>`"
        text = parts[1]
        memory.store_memory(text)
        return "Memory added successfully."
        
    else:
        return f"Unknown memory action: {action}. Use 'search' or 'add'."
