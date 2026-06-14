import os
from dotenv import load_dotenv

# Load environment variables early so API keys are available
load_dotenv()

from agent import AgentOrchestrator
from memory import MemoryManager
from voice import listen, speak

def main():
    print("="*60)
    print("🤖 Autonomous AI Agent - Enterprise Lite Capstone")
    print("="*60)
    print("Features: LangGraph ReAct, Langfuse Tracing, Hardened Docker Sandbox, ChromaDB Memory, Voice Interface")
    print("Make sure Docker is running and your .env is configured!\n")

    # Initialize components
    try:
        memory = MemoryManager()
        agent = AgentOrchestrator()
    except Exception as e:
        print(f"[Fatal Error] Failed to initialize components: {e}")
        return

    chat_history = []
    
    while True:
        print("\n" + "-"*60)
        user_input = input("\nEnter your command (or type 'voice' to speak, 'exit' to quit): ").strip()
        
        if user_input.lower() == 'exit':
            print("Goodbye!")
            break
        elif user_input.lower() == 'voice':
            user_input = listen()
            if not user_input:
                continue
        elif not user_input:
            continue
            
        # Optional: Add memory context before invoking the agent
        past_memories = memory.retrieve_memory(user_input, n_results=1)
        augmented_input = user_input
        if past_memories:
            print(f"[Memory] Found past context: {past_memories[0][:100]}...")
            augmented_input = f"User Request: {user_input}\n\nRelevant past context: {past_memories[0]}"
            
        # Run the agent
        try:
            final_response, chat_history = agent.run(augmented_input, chat_history)
            
            # Store this interaction in memory
            memory.store_memory(f"User: {user_input}\nAgent: {final_response}")
            
            # Speak and print the response
            print(f"\n[Agent Final Answer]:\n{final_response}\n")
            speak(final_response)
            
        except Exception as e:
            print(f"[Main] Error running agent: {e}")

if __name__ == "__main__":
    main()
