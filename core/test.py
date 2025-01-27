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
    
    # Test both tools
    print("\n=== Starting Tests ===")
    
    # First test bash
    response = agent.chat(
        'Please show me the contents of the current directory using the bash tool.',
        system_prompt="You are a helpful AI assistant that uses tools to help users. Be concise but thorough."
    )
    print("\n=== Bash Test Complete ===")
    
    # Then test str_replace_editor
    response = agent.chat(
        'Create a new file called test.txt with the content "Hello World" using str_replace_editor.',
        system_prompt="You are a helpful AI assistant that uses tools to help users. Be concise but thorough."
    )
    print("\n=== Editor Test Complete ===")
    
    print("\nFinal Response:", response)
    
if __name__ == "__main__":
    main()