import os
import docker

def handle_doctor(args: str) -> str:
    """
    Checks the health of the environment (API keys, Docker, etc.).
    """
    output = ["## AgentAI Doctor Report\n"]
    
    # Check LLM Providers
    groq_key = os.getenv("GROQ_API_KEY")
    gemini_key = os.getenv("GOOGLE_API_KEY")
    
    output.append(f"**Groq API Key**: {'✅ Set' if groq_key else '❌ Missing'}")
    output.append(f"**Gemini API Key**: {'✅ Set' if gemini_key else '❌ Missing'}")
    
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    output.append(f"**Active Provider**: {provider.upper()}")
    
    # Check Docker for sandbox
    try:
        client = docker.from_env()
        client.ping()
        output.append("**Docker Client**: ✅ Running and connected")
    except Exception as e:
        output.append(f"**Docker Client**: ❌ Not running or unavailable ({e})")
        
    return "\n".join(output)
