import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import shutil
import chainlit as cl
from chainlit.context import local_steps
from chainlit.step import Step
from dotenv import load_dotenv
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import chainlit.server

# Ensure output directory exists
os.makedirs("sandbox_output", exist_ok=True)

# Mount output directory and create an endpoint to list files
chainlit.server.app.mount("/output", StaticFiles(directory="sandbox_output"), name="output")

@chainlit.server.app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = os.path.join("sandbox_output", filename)
    if os.path.exists(file_path):
        return FileResponse(
            path=file_path, 
            filename=filename,
            media_type='application/octet-stream',
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    return HTMLResponse("File not found", status_code=404)

@chainlit.server.app.get("/files")
def list_files():
    files = os.listdir("sandbox_output")
    if not files:
        return HTMLResponse("<h3 style='font-family: sans-serif; padding: 20px;'>No output files generated yet.</h3>")
    
    links = [f'<li style="margin: 10px 0;"><a href="/download/{f}" style="text-decoration: none; color: #da7756; font-size: 16px;">📄 {f}</a></li>' for f in files]
    html_content = f'''
    <html>
        <head><title>Wisteria Output Files</title></head>
        <body style="font-family: sans-serif; padding: 20px; background-color: #f9f8f6;">
            <h2>📁 Generated Sandbox Files</h2>
            <ul style="list-style-type: none; padding: 0;">
                {''.join(links)}
            </ul>
        </body>
    </html>
    '''
    return HTMLResponse(html_content)

# --- GLOBAL CONTEXTVAR PATCH ---
# Chainlit 2.3.0 has a bug in Python 3.9 where it fails to initialize the `local_steps` ContextVar
# before evaluating hooks. We monkey-patch Step and MessageBase to catch it.
_orig_aenter = Step.__aenter__
async def _safe_aenter(self):
    try:
        local_steps.get()
    except LookupError:
        local_steps.set([])
    return await _orig_aenter(self)
Step.__aenter__ = _safe_aenter

_orig_enter = Step.__enter__
def _safe_enter(self):
    try:
        local_steps.get()
    except LookupError:
        local_steps.set([])
    return _orig_enter(self)
Step.__enter__ = _safe_enter

_orig_msg_init = chainlit.message.MessageBase.__post_init__
def _safe_msg_init(self):
    try:
        local_steps.get()
    except LookupError:
        local_steps.set([])
    return _orig_msg_init(self)
chainlit.message.MessageBase.__post_init__ = _safe_msg_init
# -------------------------------
from chainlit.input_widget import Select, Switch

from src.coordinator.orchestrator import AgentOrchestrator
from src.services.memory_store import MemoryManager
from langchain_core.messages import SystemMessage

load_dotenv()

@cl.data_layer
def get_data_layer():
    from json_data_layer import JsonDataLayer
    return JsonDataLayer()


def get_sandbox_files():
    output_dir = os.path.abspath(os.path.join(os.getcwd(), "sandbox_output"))
    if not os.path.exists(output_dir):
        return set()
    return set(os.listdir(output_dir))

@cl.on_chat_start
async def on_chat_start():
    # Clear previous chat files
    output_dir = os.path.abspath(os.path.join(os.getcwd(), "sandbox_output"))
    if os.path.exists(output_dir):
        for f in os.listdir(output_dir):
            file_path = os.path.join(output_dir, f)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"Failed to delete {file_path}: {e}")
    else:
        os.makedirs(output_dir, exist_ok=True)

    # Initialize Settings exactly as required
    settings = cl.ChatSettings(
        [
            Select(
                id="Model",
                label="Select AI Model",
                values=[
                    "llama-3.3-70b-versatile", 
                    "llama-3.1-8b-instant",
                    "gemini-2.0-flash-lite",
                    "qwen/qwen3-32b",
                ],
                initial_index=0,
            ),
            Switch(
                id="auto_approve",
                label="Auto-Approve Code Execution",
                initial=True,
            ),
        ]
    )
    await settings.send()

    # Initialize Memory
    memory = MemoryManager()
    
    agent = AgentOrchestrator(model_name="llama-3.3-70b-versatile")
    agent.auto_approve_code = False
    
    cl.user_session.set("memory", memory)
    cl.user_session.set("agent", agent)
    cl.user_session.set("agent_chat_history", [])
    
    await cl.Message(
        content="Hi, I am Wisteria. Nice To Meet You!\n\nYou can use action buttons below to trigger native slash commands:",
        actions=[
            cl.Action(
                name="open_files_menu", 
                label="📁 View Output Files", 
                payload={"action": "open"}
            ),
            cl.Action(
                name="cmd_doctor", 
                label="🩺 Run /doctor", 
                payload={"action": "/doctor"}
            ),
            cl.Action(
                name="cmd_compact", 
                label="🧹 Run /compact", 
                payload={"action": "/compact"}
            )
        ]
    ).send()

@cl.action_callback("open_files_menu")
async def on_action(action):
    files = os.listdir("sandbox_output")
    if not files:
        await cl.Message(content="No files have been generated yet.").send()
        return
        
    elements = []
    for f in files:
        file_path = os.path.join("sandbox_output", f)
        # Using cl.File provides a native Chainlit attachment with a working download button
        elements.append(cl.File(name=f, path=file_path, display="inline"))
    
    await cl.Message(
        content="Here are the generated files. Click on any file below to securely download it:",
        elements=elements
    ).send()

@cl.action_callback("cmd_doctor")
async def on_action_doctor(action):
    from src.commands.registry import process_command
    response = process_command("/doctor")
    await cl.Message(content=response).send()

@cl.action_callback("cmd_compact")
async def on_action_compact(action):
    from src.commands.registry import process_command
    response = process_command("/compact")
    await cl.Message(content=response).send()

@cl.on_settings_update
async def setup_agent(settings):
    model_choice = settings["Model"]
    auto_approve = settings.get("auto_approve", False)
    
    # Reinitialize agent with new model and settings
    agent = AgentOrchestrator(model_name=model_choice)
    agent.auto_approve_code = auto_approve
    cl.user_session.set("agent", agent)
    await cl.Message(content=f"⚙️ Settings updated: Model set to **{model_choice}**. Auto-approve is **{'ON' if auto_approve else 'OFF'}**.").send()

@cl.on_message
async def on_message(message: cl.Message):
    memory = cl.user_session.get("memory")
    agent = cl.user_session.get("agent")
    history = cl.user_session.get("agent_chat_history")
    
    if not agent or not memory:
        await cl.Message(content="System not initialized properly.").send()
        return

    # Native File Ingestion
    if message.elements:
        output_dir = os.path.abspath(os.path.join(os.getcwd(), "sandbox_output"))
        os.makedirs(output_dir, exist_ok=True)
        
        for element in message.elements:
            if hasattr(element, "path") and element.path:
                target_path = os.path.join(output_dir, element.name)
                shutil.copy2(element.path, target_path)
                
                injection_msg = f"The user uploaded a file named '{element.name}'. It is located at '/output/{element.name}'. If you need to know its contents, use your execute_code tool to write a python script to read or analyze it."
                history.append(SystemMessage(content=injection_msg))

    prompt = message.content
    if not prompt and message.elements:
        prompt = "Please review the file I just uploaded."
        
    from src.commands.registry import process_command
    command_response = process_command(prompt)
    if command_response is not None:
        await cl.Message(content=command_response).send()
        return
        
    past_memories = memory.retrieve_memory(prompt, n_results=1)
    augmented_input = prompt
    if past_memories:
        augmented_input = f"User Request: {prompt}\n\nRelevant past context: {past_memories[0]}"
        
    try:
        res = await cl.make_async(agent.run)(augmented_input, history)
        final_response, updated_history = res

        cl.user_session.set("agent_chat_history", updated_history)
        memory.store_memory(f"User: {prompt}\nAgent: {final_response}")
        
        await cl.Message(content=final_response).send()

    except Exception as e:
        await cl.Message(content=f"Error running Wisteria: {e}", author="System").send()
