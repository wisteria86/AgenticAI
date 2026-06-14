import os
from langchain_core.tools import tool

@tool
def read_file(path: str) -> str:
    """
    Read the contents of a file at the given local path.
    
    Args:
        path: Absolute or relative path to the file.
        
    Returns:
        The string contents of the file.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

@tool
def write_file(path: str, content: str) -> str:
    """
    Write content to a file at the given local path. Overwrites the file if it exists.
    
    Args:
        path: Absolute or relative path to the file.
        content: The text content to write.
        
    Returns:
        A success message or an error.
    """
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote to {path}"
    except Exception as e:
        return f"Error writing file: {str(e)}"

@tool
def append_file(path: str, content: str) -> str:
    """
    Append content to the end of an existing file.
    
    Args:
        path: Absolute or relative path to the file.
        content: The text content to append.
        
    Returns:
        A success message or an error.
    """
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully appended to {path}"
    except Exception as e:
        return f"Error appending to file: {str(e)}"
