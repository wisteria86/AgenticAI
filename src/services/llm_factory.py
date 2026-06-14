import os
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI

def get_max_tokens_for_model(model_name: str) -> int:
    name = model_name.lower()
    if "qwen" in name:
        return 2500  # Extremely Strict 6000 TPM limit on Groq
    if "70b" in name:
        return 2500  # Extremely Strict 6000 TPM limit on Groq
    if "gemini" in name:
        return 8192
    if "8b" in name:
        return 8192
    return 3300  # Safe default

def create_llm(model_name=None):
    """
    Factory function to initialize the LLM based on environment variables.
    Returns a tuple of (llm_instance, actual_model_name).
    """
    if model_name and "gemini" in model_name.lower():
        provider = "gemini"
    else:
        provider = os.getenv("LLM_PROVIDER", "groq").lower()
        
    print(f"[Agent] Initializing with provider: {provider.upper()}")
    
    if provider == "groq":
        actual_model = model_name if model_name else "llama-3.3-70b-versatile"
        llm = ChatGroq(
            model_name=actual_model,
            temperature=0.2,
            api_key=os.getenv("GROQ_API_KEY"),
            max_retries=3,
            max_tokens=get_max_tokens_for_model(actual_model)
        )
    else:
        actual_model = model_name if model_name else "gemini-2.0-flash-lite"
        llm = ChatGoogleGenerativeAI(
            model=actual_model,
            temperature=0.2,
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            max_retries=3,
            max_tokens=get_max_tokens_for_model(actual_model)
        )
        
    return llm, actual_model
