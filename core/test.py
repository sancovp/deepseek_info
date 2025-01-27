from agent import Agent
import os
from dotenv import load_dotenv

load_dotenv()

def main():
    agent = Agent(
        name="test_agent",
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        model="deepseek-reasoner"
    )
    
    # Test basic chat
    response = agent.chat(
        "What is 2+2?",
        system_prompt="You are a helpful AI assistant."
    )
    print("\nTest complete!")
    
if __name__ == "__main__":
    main()