from langchain_core.tools import tool

@tool
def delegate_to_subagent(task: str) -> str:
    """
    Spawn a sub-agent to perform a specific task in parallel or to offload complex work.
    
    Args:
        task: A detailed description of the task the sub-agent needs to accomplish.
        
    Returns:
        The final response from the sub-agent after completing the task.
    """
    # Import locally to avoid circular imports since AgentOrchestrator imports tools
    from src.coordinator.orchestrator import AgentOrchestrator
    
    print(f"[SubAgent] Spawning new sub-agent for task: {task}")
    
    try:
        # Create a new agent instance
        sub_agent = AgentOrchestrator()
        
        # Initialize an empty history and run
        history = []
        result = sub_agent.run(task, history)
        
        if result:
            final_response, _ = result
            return f"Sub-Agent completed task. Result:\n{final_response}"
        else:
            return "Sub-Agent failed to return a result."
            
    except Exception as e:
        return f"Error executing sub-agent: {str(e)}"
