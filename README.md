# Wisteria: Advanced Agentic AI 🌸

Wisteria is a highly capable, autonomous engineering agent designed to architect software, execute Python code, and generate complex assets within a secure local environment. Powered by **LangGraph** and deployed via a responsive **Chainlit** UI, Wisteria supports dynamic LLM routing across the most powerful open-weight and proprietary models available.

## 🚀 Key Features

*   **Intelligent LangGraph Orchestrator**: Uses a robust graph-based workflow to manage reasoning, tool execution, and error-recovery loops natively.
*   **Dynamic Model Routing**: Seamlessly swap between models via the UI settings.
    *   `llama-3.3-70b-versatile` (Groq)
    *   `llama-3.1-8b-instant` (Groq)
    *   `qwen-2.5-32b` (Groq)
    *   `gemini-2.0-flash-lite` (Google)
*   **Auto-Scaling Context Guardrails**: Dynamically limits input context windows and output `max_tokens` per model to strictly prevent TPM (Tokens Per Minute) API crashes.
*   **Markdown Interceptor Engine**: Bypasses strict API JSON limits by transparently intercepting and saving large artifacts (like multi-page HTML presentations) directly from the LLM's chat output stream.
*   **Local Sandbox Execution**: Natively executes Python code in a secure sandbox, reads/writes files, and conducts autonomous web research.
*   **Built-in Slash Commands**: Automate workflows using in-chat slash commands like `/compact` and `/doctor`.
*   **Langfuse Observability**: Native tracing and telemetry built-in for deep observability.

## 🛠️ Project Architecture

The codebase has been highly modularized for production readiness:

```text
.
├── app.py                      # Chainlit entry point & UI setup
├── main.py                     # Core backend endpoints (if applicable)
├── src/
│   ├── coordinator/
│   │   └── orchestrator.py     # LangGraph AgentState and logic
│   ├── services/
│   │   ├── context_manager.py  # Sliding window and TPM guardrails
│   │   ├── llm_factory.py      # Dynamic LLM provisioning
│   │   └── memory_store.py     # Conversation persistence
│   ├── tools/                  
│   │   ├── agent.py            # Sub-agent delegation
│   │   ├── file_ops.py         # Native file reading/writing/appending
│   │   ├── sandbox.py          # Code execution tool
│   │   └── web_search.py       # DuckDuckGo integration
│   └── commands/               # Slash command logic
```

## ⚙️ Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/wisteria86/AgenticAI.git
    cd AgenticAI
    ```

2.  **Create a virtual environment**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables**:
    Create a `.env` file based on `.env.sample` and add your API keys:
    ```env
    GROQ_API_KEY=your_groq_key
    GOOGLE_API_KEY=your_google_key
    
    # Optional: Langfuse Tracing
    LANGFUSE_PUBLIC_KEY=your_public_key
    LANGFUSE_SECRET_KEY=your_secret_key
    ```

## 💻 Usage

Start the Chainlit UI server:

```bash
chainlit run app.py -w
```

This will automatically launch the Agentic AI interface in your browser. From the settings menu, you can toggle the underlying model and enable or disable the Auto-Approve mechanism for sandbox code execution.

## 🛡️ Architecture Highlights

*   **Loop Prevention**: The orchestrator tracks repetitive tool calls. If an agent loops continuously (e.g., repeatedly failing to parse a specific API format), it is hard-stopped and forced to synthesize to prevent runaway billing.
*   **Strict JSON Escaping**: Bypasses 400 Bad Request API failures by forcing strict single-quote escaping for HTML attributes, supplemented by the Markdown Interceptor for massive files.

## 📝 License

MIT License
