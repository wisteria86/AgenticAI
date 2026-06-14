import os
import time
from collections import deque
from typing import Annotated, Literal, TypedDict
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

# Services
from src.services.llm_factory import create_llm
from src.services.context_manager import manage_context_window

# Tools Registry
from src.tools import ALL_TOOLS

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]

class AgentOrchestrator:
    # Gemini free tier: 5 requests per minute
    RATE_LIMIT = 5
    RATE_WINDOW = 60  # seconds

    def __init__(self, model_name=None):
        self.auto_approve_code = False
        self._call_timestamps = deque()
        
        if os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"):
            print("[Agent] Langfuse native observability enabled via @observe decorator.")
        else:
            print("[Agent] Warning: Langfuse keys missing. Traces won't be sent.")
            
        self.llm, self.model_name = create_llm(model_name)
        
        # Bind tools to the LLM
        self.tools = ALL_TOOLS
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        
        # Build the state graph
        builder = StateGraph(AgentState)
        builder.add_node("llm", self.call_llm)
        builder.add_node("tools", self.call_tools)
        
        # Define the edges
        builder.add_edge(START, "llm")
        builder.add_conditional_edges(
            "llm",
            self.route_after_llm,
            {"tools": "tools", "end": END}
        )
        builder.add_edge("tools", "llm") # Loop back to LLM after tools
        
        self.graph = builder.compile()

    def _wait_for_rate_limit(self):
        """Sliding-window rate limiter for Gemini free tier quota."""
        now = time.time()
        while self._call_timestamps and self._call_timestamps[0] <= now - self.RATE_WINDOW:
            self._call_timestamps.popleft()

        if len(self._call_timestamps) >= self.RATE_LIMIT:
            wait_time = self._call_timestamps[0] - (now - self.RATE_WINDOW) + 1
            print(f"[Agent] Rate limit reached ({self.RATE_LIMIT} req/{self.RATE_WINDOW}s). Waiting {wait_time:.1f}s...")
            import chainlit as cl
            if hasattr(self, 'current_step') and self.current_step:
                out = self.current_step.content or ""
                self.current_step.content = out + f"\n⏳ Waiting {int(wait_time)}s for rate limit..." if out else f"⏳ Waiting {int(wait_time)}s for rate limit..."
                try:
                    cl.run_sync(self.current_step.update())
                except Exception:
                    pass
                
            time.sleep(wait_time)
            
            if hasattr(self, 'current_step') and self.current_step:
                self.current_step.content = (self.current_step.content or "") + " Resumed."
                try:
                    cl.run_sync(self.current_step.update())
                except Exception:
                    pass

        self._call_timestamps.append(time.time())

    def call_llm(self, state: AgentState):
        """Node for reasoning and deciding on tool use."""
        self._wait_for_rate_limit()
        print("[Agent] Reasoning...")
        
        raw_messages = state["messages"]
        system_messages, other_messages = manage_context_window(raw_messages, getattr(self, "model_name", ""))
        
        if not system_messages:
            system_prompt = SystemMessage(
                content="""# ROLE AND IDENTITY
                    You are Wisteria, a Principal Autonomous Systems Engineer. 
                    You operate within a secure local environment, capable of executing Python code, manipulating files, and architecting software. 

                    # COMMUNICATION DIRECTIVES (CRITICAL)
                    - NEVER apologize. 
                    - NEVER use preamble or postamble (e.g., "Certainly!", "Here is the updated code:", "Let me know if you need anything else!").
                    - NEVER preach or provide unsolicited ethical advice.
                    - Be concise, highly technical, and emotionally neutral. 
                    - Output text as if you are a senior engineer speaking to another senior engineer.

                    # COGNITIVE SEPARATION (THE THINKING BLOCK)
                    Before taking ANY action, invoking ANY tool, or writing ANY final response, you MUST output a `<thinking>` block.
                    Inside this block, you must:
                    1. Analyze the user's request.
                    2. Identify the necessary tools or file modifications.
                    3. Plan the exact steps to achieve the goal.
                    4. Catch potential edge cases (e.g., missing dependencies, context limits).

                    Example:
                    <thinking>
                    The user wants a Python script to scrape a website. I need to use the `execute_code` tool. I should use `requests` and `BeautifulSoup`. I will save the output to `sandbox_output/scraper.py`.
                    </thinking>

                    - For short snippets (under 15 lines): Output the code directly in the chat using standard markdown.
                    - CRITICAL FOR LARGE FILES: Groq API tools will crash with '400 Bad Request' if you try to pass massive HTML payloads as JSON arguments. 
                    - To completely bypass tools for large files, simply output a markdown code block directly in your chat response. The system will intercept it and save it!
                    - The VERY FIRST LINE inside the markdown code block MUST be a comment containing the exact filename.
                    Example for HTML:
                    ```html
                    <!-- filename: sandbox_output/strategic_presentation.html -->
                    <!DOCTYPE html>...
                    ```
                    Example for Python:
                    ```python
                    # filename: sandbox_output/script.py
                    print("Hello")
                    ```

                    # TOOL INVOCATION DIRECTIVE & JSON SAFETY (CRITICAL)
                    Your text output MUST END immediately after the `</thinking>` tag when you intend to use a tool. 
                    Do not write any text, code blocks, or XML tags after your thinking process concludes. 
                    You must pass the arguments natively to the backend API payload.
                    CRITICAL JSON ESCAPING: If you must use `write_file` or `append_file` for HTML, NEVER use double quotes (`"`) inside HTML tags or attributes. You MUST use single quotes (`'`) for all HTML attributes (e.g., `<div class='max-w-5xl'>`) to prevent breaking the internal JSON payload parser.

                    CORRECT BEHAVIOR EXAMPLE:
                        <thinking>
                        I need to write the HTML presentation. I will use the `write_file` tool.
                        </thinking>
                        [END OF MESSAGE - DO NOT GENERATE ANY MORE TEXT]               
                        
                    # ERROR RECOVERY
                    If a tool execution fails or returns an error, do not immediately ask the user for help. 
                    1. Open a new `<thinking>` block.
                    2. Analyze the exact traceback.
                    3. Write a correction and invoke the tool again. 
                    Only ask the user for intervention if you fail 3 times consecutively.
                    
                    # UI/UX ENGINEERING STANDARDS (CRITICAL)
                    Whenever you are tasked with generating web pages, HTML artifacts, or presentations, you must natively apply the following modern design system without the user asking:
                    1. Framework: Always inject Tailwind CSS via CDN (`<script src="https://cdn.tailwindcss.com"></script>`). Do not write raw CSS unless absolutely necessary.
                    2. Typography: Always import and use 'Inter' for body text and 'Playfair Display' for headers.
                    3. Layouts: Never leave raw text floating. Always wrap content in centered containers (`max-w-5xl`, `mx-auto`). Use CSS Grid (`grid-cols-2`, `gap-8`) for multi-point data. 
                    4. Spacing: Apply generous, modern padding (e.g., `p-12`, `mb-8`). 
                    5. Color Theory: Default to modern "Dark Mode" aesthetic (e.g., `bg-slate-900` backgrounds, `text-slate-300` body, `text-white` headers) or clean minimal light mode (`bg-gray-50`). 
                    6. Polish: Add subtle rounding (`rounded-xl`), borders (`border-slate-800`), and shadows to cards or tables.
                    
                    """
            )
            system_messages = [system_prompt]
            
        messages = system_messages + other_messages
        
        import chainlit as cl
        if hasattr(self, 'current_step') and self.current_step:
            out = self.current_step.content or ""
            if not out.endswith("🧠 Thinking..."):
                self.current_step.content = out + "\n🧠 Thinking..." if out else "🧠 Thinking..."
                try:
                    cl.run_sync(self.current_step.update())
                except Exception:
                    pass
            
        # Hard-Stop on Repeated Tools (Loop Prevention)
        tool_messages = [m for m in messages if isinstance(m, ToolMessage)]
        if len(tool_messages) >= 2:
            if tool_messages[-1].name == tool_messages[-2].name and isinstance(messages[-1], ToolMessage):
                warning = SystemMessage(
                    content=f"SYSTEM WARNING: You are caught in a loop. Do not use the '{tool_messages[-1].name}' tool again. Immediately synthesize the information you have or write the file."
                )
                messages.append(warning)
                
        for attempt in range(3):
            try:
                time.sleep(5.0)
                response = self.llm_with_tools.invoke(messages)
                
                # INTERCEPT: Auto-save markdown code blocks with filename comments
                if response.content:
                    import re
                    pattern = r'```[a-zA-Z]*\n(?:<!--\s*filename:\s*(.*?)\s*-->|#\s*filename:\s*(.*?)\s*\n)(.*?)(?:```|\Z)'
                    blocks = re.findall(pattern, response.content, re.DOTALL | re.IGNORECASE)
                    
                    saved_files = []
                    for b in blocks:
                        fname_html = b[0].strip() if b[0] else None
                        fname_py = b[1].strip() if b[1] else None
                        content = b[2]
                        fname = fname_html or fname_py
                        if fname:
                            try:
                                import os
                                os.makedirs(os.path.dirname(os.path.abspath(fname)), exist_ok=True)
                                with open(fname, "w", encoding="utf-8") as f:
                                    f.write(content.strip() + "\n")
                                saved_files.append(fname)
                            except: pass
                    
                    if saved_files:
                        # Replace massive text blocks with a placeholder to save UI/Context tokens
                        response.content = re.sub(pattern, lambda m: f"\n\n[System: Auto-saved {m.group(1) or m.group(2)} to disk]\n\n", response.content, flags=re.DOTALL | re.IGNORECASE)
                        print(f"[Agent] Auto-saved intercepted markdown files: {saved_files}")
                        if hasattr(self, 'current_step') and self.current_step:
                            out = self.current_step.content or ""
                            self.current_step.content = out + f"\n💾 Auto-saved: {', '.join(saved_files)}"
                            try:
                                cl.run_sync(self.current_step.update())
                            except: pass
                            
                return {"messages": [response]}
            except Exception as e:
                error_str = str(e)
                if "tool_use_failed" in error_str or "validation failed" in error_str:
                    print(f"[Agent] Groq tool parsing failed ({error_str}), retrying (attempt {attempt+1}/3)...")
                    messages.append(SystemMessage(
                        content="SYSTEM EXCEPTION: Your previous tool call failed validation. "
                                "You MUST use the native JSON tool schema. Do NOT use `<function=...>` XML tags. "
                                "The tool name must be EXACTLY the function name, without arguments appended to it."
                    ))
                    continue
                
                if "429" in error_str or "quota" in error_str.lower() or "ResourceExhausted" in error_str:
                    error_msg = "Error: You have exceeded your API quota for this model. Please select a different model."
                else:
                    error_msg = f"Error communicating with LLM: {error_str}"
                
                print(f"[Agent] {error_msg}")
                if hasattr(self, 'current_step') and self.current_step:
                    out = self.current_step.content or ""
                    self.current_step.content = out + f"\n❌ {error_msg}" if out else f"❌ {error_msg}"
                    try:
                        cl.run_sync(self.current_step.update())
                    except Exception:
                        pass
                return {"messages": [AIMessage(content=error_msg)]}
        
        if hasattr(self, 'current_step') and self.current_step:
            out = self.current_step.content or ""
            self.current_step.content = out + "\n❌ Failed to format tool calls." if out else "❌ Failed to format tool calls."
            try:
                cl.run_sync(self.current_step.update())
            except Exception:
                pass
        return {"messages": [AIMessage(content="Error: The model repeatedly failed to format its tool calls correctly.")]}

    def call_tools(self, state: AgentState):
        """Node for executing tools with Human-in-the-Loop (HITL) safety check."""
        messages = state["messages"]
        last_message = messages[-1]
        
        tool_responses = []
        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            
            print(f"\n[Agent] Action: Attempting to call '{tool_name}'")
            
            if tool_name == "execute_code":
                code_to_run = tool_args.get('code', '')
                print("--------------------------------------------------")
                print("[HITL SAFETY] Agent requested to run the following code:")
                print(code_to_run)
                print("--------------------------------------------------")
                
                if not self.auto_approve_code:
                    print("[HITL] Execution denied because Auto-Approve is OFF.")
                    tool_responses.append(
                        ToolMessage(
                            content="Error: The human user has not granted permission to execute code in this session. "
                                    "Do not attempt to run code. Provide the code to the user instead.",
                            tool_call_id=tool_call["id"],
                            name=tool_name
                        )
                    )
                    continue
                else:
                    print("[HITL] Auto-Approve is ON. Executing...")
            
            import chainlit as cl
            if hasattr(self, 'current_step') and self.current_step:
                out = self.current_step.content or ""
                self.current_step.content = out + f"\n⚙️ Executing '{tool_name}'..." if out else f"⚙️ Executing '{tool_name}'..."
                try:
                    cl.run_sync(self.current_step.update())
                except Exception:
                    pass
                
            try:
                tool_instance = next(t for t in self.tools if t.name == tool_name)
                print(f"[Agent] Executing {tool_name}...")
                result = tool_instance.invoke(tool_args)
                
                if hasattr(self, 'current_step') and self.current_step:
                    self.current_step.content = (self.current_step.content or "") + f" (Done)"
                    try:
                        cl.run_sync(self.current_step.update())
                    except Exception:
                        pass
                    
                tool_responses.append(
                    ToolMessage(
                        content=str(result),
                        tool_call_id=tool_call["id"],
                        name=tool_name
                    )
                )
            except Exception as e:
                print(f"[Agent] Tool {tool_name} failed: {e}")
                if hasattr(self, 'current_step') and self.current_step:
                    out = self.current_step.content or ""
                    self.current_step.content = out + f"\n❌ Error executing {tool_name}: {str(e)[:200]}"
                    try:
                        cl.run_sync(self.current_step.update())
                    except Exception:
                        pass
                    
                tool_responses.append(
                    ToolMessage(
                        content=f"Error executing {tool_name}: {str(e)}",
                        tool_call_id=tool_call["id"],
                        name=tool_name
                    )
                )
                
        return {"messages": tool_responses}

    def route_after_llm(self, state: AgentState) -> Literal["tools", "end"]:
        messages = state["messages"]
        last_message = messages[-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return "end"

    def run(self, user_input: str, chat_history: list = None):
        """Entry point to run the agent with the given input."""
        import chainlit as cl
        self.current_step = cl.Message(content="🤖 Processing Request...", author="System")
        try:
            cl.run_sync(self.current_step.send())
        except Exception:
            pass

        if chat_history is None:
            chat_history = []
            
        messages = chat_history + [HumanMessage(content=user_input)]
        
        print("[Agent] Starting orchestrator graph...")
        result = self.graph.invoke({"messages": messages})
        
        if hasattr(self, 'current_step') and self.current_step:
            out = self.current_step.content or ""
            self.current_step.content = out + "\n✅ Finished." if out else "✅ Finished."
            try:
                cl.run_sync(self.current_step.update())
            except Exception:
                pass
                
        final_message = result["messages"][-1].content
        return final_message, result["messages"]
