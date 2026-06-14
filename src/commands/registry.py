from src.commands.doctor import handle_doctor
from src.commands.memory import handle_memory
from src.commands.compact import handle_compact

COMMANDS = {
    "/doctor": handle_doctor,
    "/memory": handle_memory,
    "/compact": handle_compact
}

def process_command(message: str) -> str:
    """
    Checks if a message is a slash command and processes it.
    Returns the command output, or None if it's not a command.
    """
    if not message.startswith("/"):
        return None
        
    parts = message.split(maxsplit=1)
    command = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""
    
    if command in COMMANDS:
        return COMMANDS[command](args)
    else:
        return f"Unknown command: {command}. Available commands: {', '.join(COMMANDS.keys())}"
