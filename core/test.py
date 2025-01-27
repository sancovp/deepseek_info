from agent import Agent
import os
from dotenv import load_dotenv

load_dotenv()

class TestMethods:
    @staticmethod
    def echo(text: str) -> str:
        """Test function that just echoes back text"""
        return f"You said: {text}"

def main():
    agent = Agent(
        name="test_agent",
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        model="deepseek-reasoner"
    )
    
    # Add test function
    agent.echo = TestMethods.echo
    
    # Test with sysAction that should trigger injection
    print("\n=== Starting Test ===")
    response = agent.chat(
        'Let me test the echo function <sysAction>echo("hello")</sysAction> and then tell me what happened.',
        system_prompt="You are a helpful AI assistant that tests functions and reports results clearly."
    )
    print("\n=== Test Complete ===")
    print("\nFinal Response:", response)
    
if __name__ == "__main__":
    main()