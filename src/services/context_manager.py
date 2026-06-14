from langchain_core.messages import HumanMessage, ToolMessage, AIMessage, SystemMessage

def apply_context_guardrails(messages, max_chars=8000):
    """Token Estimation Guardrail: roughly 1 token ≈ 4 chars."""
    processed_messages = []
    for msg in messages:
        if isinstance(msg.content, str) and len(msg.content) > max_chars:
            print(f"[Agent] Guardrail triggered: Truncating message of length {len(msg.content)} chars.")
            truncated_text = msg.content[:max_chars] + f"\n\n[System: The following content was truncated due to context limits (exceeded {max_chars} chars)...]"
            
            if isinstance(msg, HumanMessage):
                kwargs = {k: v for k, v in msg.additional_kwargs.items() if k not in ["content"]}
                processed_messages.append(HumanMessage(content=truncated_text, **kwargs))
            elif isinstance(msg, ToolMessage):
                kwargs = {k: v for k, v in msg.additional_kwargs.items() if k not in ["content", "tool_call_id", "name"]}
                processed_messages.append(ToolMessage(content=truncated_text, tool_call_id=msg.tool_call_id, name=msg.name, **kwargs))
            elif isinstance(msg, AIMessage):
                kwargs = {k: v for k, v in msg.additional_kwargs.items() if k not in ["content", "tool_calls"]}
                processed_messages.append(AIMessage(content=truncated_text, tool_calls=msg.tool_calls, **kwargs))
            else:
                processed_messages.append(msg)
        else:
            processed_messages.append(msg)
    return processed_messages

def manage_context_window(raw_messages, current_model: str):
    """
    Splits messages, applies model-aware sliding window truncation, 
    and applies token estimation guardrails.
    Returns the processed list of messages.
    """
    system_messages = [m for m in raw_messages if isinstance(m, SystemMessage)]
    other_messages = [m for m in raw_messages if not isinstance(m, SystemMessage)]
    
    current_model = str(current_model).lower()
    
    if "8b" in current_model:
        N_MESSAGES = 4
        max_chars_limit = 3000
    elif "70b" in current_model or "qwen" in current_model:
        # STRICT TPM GUARDRAIL: These models have a 6000 TPM limit on Groq.
        # We must restrict input history so (Input + Max Output) < 6000.
        N_MESSAGES = 4
        max_chars_limit = 1500
    elif "gemini" in current_model:
        N_MESSAGES = 12
        max_chars_limit = 8000
    else:
        N_MESSAGES = 6
        max_chars_limit = 4000
    
    # Sliding Window Truncation
    if len(other_messages) > N_MESSAGES:
        other_messages = other_messages[-N_MESSAGES:]
        # Ensure we don't start with a ToolMessage separated from its AIMessage
        while other_messages and isinstance(other_messages[0], ToolMessage):
            other_messages.pop(0)
            
    # Token Estimation Guardrail
    other_messages = apply_context_guardrails(other_messages, max_chars=max_chars_limit)
    
    return system_messages, other_messages
