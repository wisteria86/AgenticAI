def handle_compact(args: str) -> str:
    """
    Command to instruct the user on context compression.
    Since actual history is managed in the UI session, we return a system message.
    """
    return (
        "**Context Compression:**\n"
        "Your chat history naturally truncates via sliding window during inference.\n"
        "If you want to fully clear the history to save tokens, please use the 'New Chat' button in the Chainlit UI."
    )
