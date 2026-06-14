from src.tools.web_search import search_internet
from src.tools.file_ops import read_file, write_file, append_file
from src.tools.sandbox import execute_code
from src.tools.agent import delegate_to_subagent

# Registry of all available tools
ALL_TOOLS = [
    search_internet,
    read_file,
    write_file,
    append_file,
    execute_code,
    delegate_to_subagent
]
