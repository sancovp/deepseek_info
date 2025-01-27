from typing import Optional, Dict, Any, List
from openai import OpenAI
import os
from pydantic import BaseModel
import re
from colorama import Fore, Style, init

init()

class Message(BaseModel):
    role: str
    content: str

class History(BaseModel):
    messages: List[Message] = []
    id: str
    project: Optional[str] = None
    profile: Optional[str] = None

class Agent:
    def __init__(
        self,
        name: str,
        api_key: str,
        model: str = "deepseek-reasoner",
        base_url: str = "https://api.deepseek.com",
        debug: bool = True
    ):
        self.name = name
        self.debug = debug
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.model = model
        self.histories: Dict[str, History] = {}
        self.current_history_id: Optional[str] = None
        self.current_profile: Optional[str] = None
        
    def create_history(self, project: Optional[str] = None) -> str:
        """Create a new conversation history and return its ID"""
        from datetime import datetime
        history_id = f"{self.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.histories[history_id] = History(
            id=history_id,
            project=project,
            messages=[]
        )
        return history_id
        
    def chat(
        self,
        message: str,
        history_id: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> str:
        """Chat with the model and get both reasoning and final response"""
        
        # Create or get history
        if not history_id:
            history_id = self.create_history()
        self.current_history_id = history_id
        
        # Prepare messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
            
        # Add history messages
        messages.extend([
            {"role": msg.role, "content": msg.content}
            for msg in self.histories[history_id].messages
        ])
        
        # Add new message
        messages.append({"role": "user", "content": message})
        
        if self.debug:
            print(f"\n{Fore.BLUE}Sending messages:{Style.RESET_ALL}")
            for msg in messages:
                print(f"{msg['role']}: {msg['content'][:100]}...")
        
        # Get streaming response
        try:
            print(f"\n{Fore.YELLOW}Sending request to DeepSeek API...{Style.RESET_ALL}")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=2000,
                stream=True,
                timeout=30
            )
            print(f"{Fore.GREEN}Got response from API{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Error calling DeepSeek API: {str(e)}{Style.RESET_ALL}")
            raise
        
        # Collect reasoning and content
        reasoning_content = ""
        content = ""
        
        print(f"\n{Fore.CYAN}🤔 Reasoning:{Style.RESET_ALL}")
        for chunk in response:
            if hasattr(chunk.choices[0].delta, 'reasoning_content'):
                if chunk.choices[0].delta.reasoning_content:
                    reasoning = chunk.choices[0].delta.reasoning_content
                    reasoning_content += reasoning
                    print(reasoning, end='', flush=True)
            else:
                if hasattr(chunk.choices[0].delta, 'content'):
                    if chunk.choices[0].delta.content:
                        content_chunk = chunk.choices[0].delta.content
                        content += content_chunk
                        
        print(f"\n{Fore.GREEN}💭 Response:{Style.RESET_ALL}\n{content}")
        
        # Update history
        self.histories[history_id].messages.append(Message(role="user", content=message))
        self.histories[history_id].messages.append(Message(role="assistant", content=content))
        
        return content
    
    def process_system_actions(self, text: str) -> str:
        """Process any system actions in the text using regex"""
        def replace_action(match):
            func_name = match.group(1)
            func_args = match.group(2)
            
            if hasattr(self, func_name):
                func = getattr(self, func_name)
                try:
                    result = func(func_args)
                    return f"Action {func_name} executed: {result}"
                except Exception as e:
                    return f"Error executing {func_name}: {str(e)}"
            return f"Unknown action: {func_name}"
            
        return re.sub(
            r'<sysAction>\s*(\w+)\s*\((.*?)\)\s*</sysAction>',
            replace_action,
            text,
            flags=re.DOTALL
        )