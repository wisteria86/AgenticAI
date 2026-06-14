import os
import tempfile
import docker
from langchain_core.tools import tool

try:
    client = docker.from_env()
except Exception as e:
    print(f"Warning: Docker not available or running. Some tools may fail. Error: {e}")
    client = None

@tool
def execute_code(code: str) -> str:
    """
    Execute Python code in an isolated, secure Docker sandbox.
    
    This function:
    1. Writes the code to a temporary file.
    2. Spawns a 'python-sandbox' docker container.
    3. Runs the code with memory limits, no internet access, and a hard 30-second timeout.
    
    Args:
        code: A string containing valid Python code to execute.
        
    Returns:
        The standard output (and standard error) of the executed script.
    """
    if not client:
        return "Error: Docker client is not initialized. Cannot run sandbox."
    
    temp_dir = tempfile.mkdtemp()
    script_path = os.path.join(temp_dir, "script.py")
    
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(code)
        
    output_dir = os.path.abspath(os.path.join(os.getcwd(), "sandbox_output"))
    os.makedirs(output_dir, exist_ok=True)
        
    container = None
    try:
        container = client.containers.run(
            image="python-sandbox",
            command=["python", "/app/script.py"],
            volumes={
                temp_dir: {'bind': '/app', 'mode': 'ro'},
                output_dir: {'bind': '/output', 'mode': 'rw'}
            },
            network_mode="none",
            mem_limit="512m",
            detach=True,
            remove=False
        )
        
        result = container.wait(timeout=30)
        logs = container.logs().decode("utf-8")
        
        if result['StatusCode'] != 0:
            return f"Execution failed with status code {result['StatusCode']}.\nLogs/Traceback:\n{logs}"
            
        return logs

    except docker.errors.ContainerError as e:
        return f"Container error: {str(e)}"
    except Exception as e:
        if "timeout" in str(e).lower():
            if container:
                container.kill()
            return "Error: Execution timed out after 30 seconds."
        return f"Error executing code: {str(e)}"
    finally:
        if container:
            try:
                container.remove(force=True)
            except:
                pass
