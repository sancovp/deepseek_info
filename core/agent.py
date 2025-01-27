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

from .tools import load_tools

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
        
        # Load all tools
        tools = load_tools()
        for name, tool in tools.items():
            setattr(self, name, tool)
        
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
        
    def inject_proxy_user_msg(self, message: str) -> str:
        """Injects a message back to the AI as if from a user, allowing iterative tool usage."""
        print(f"\n{Fore.CYAN}💉 Injecting message:{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{message}{Style.RESET_ALL}")
        user_message = f"Here's the injection you requested: 💉\n{message}\n💉"
        return self.chat(user_message)

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
        
        # Prepare messages with tool docs
        messages = []
        base_prompt = f"You are a helpful AI assistant with access to system tools. {TOOL_DOCS}"
        if system_prompt:
            base_prompt = f"{base_prompt}\n\n{system_prompt}"
        messages.append({"role": "system", "content": base_prompt})
            
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
        
        # Process the content for system actions as we receive it
        current_content = ""
        for line in content.split('\n'):
            if '<sysAction>' in line:
                # Process any system actions in this line
                processed_line = self.process_system_actions(line)
                current_content += processed_line + '\n' if processed_line else '\n'
            else:
                current_content += line + '\n'
        
        # Update history
        self.histories[history_id].messages.append(Message(role="user", content=message))
        self.histories[history_id].messages.append(Message(role="assistant", content=current_content))
        
        return current_content
    
    def process_system_actions(self, text: str) -> str:
        """Process any system actions in the text using regex"""
        def replace_action(match):
            func_name = match.group(1)
            func_args = match.group(2)
            
            if hasattr(self, func_name):
                func = getattr(self, func_name)
                try:
                    # Clean up the args string (remove quotes if present)
                    clean_args = func_args.strip('"\'')
                    result = func(clean_args)
                    # Format result for injection
                    if isinstance(result, str) and result.startswith("Error"):
                        action_result = f"🚨<sysActionError>\n{func_name}({func_args})\n\n[RESULT]:\n\n{result}\n</sysActionError>🚨"
                    else:
                        action_result = f"<sysActionResults>\n{func_name}({func_args})\n\n[RESULT]:\n\n{result}\n</sysActionResults>"
                    
                    # Print debug info
                    print(f"\n{Fore.YELLOW}Executing sysAction: {func_name}({clean_args}){Style.RESET_ALL}")
                    print(f"{Fore.GREEN}Result: {result}{Style.RESET_ALL}")
                    
                    # Inject result back to AI and return empty string to hide original output
                    self.inject_proxy_user_msg(action_result)
                    return ""
                except Exception as e:
                    error_result = f"🚨<sysActionError>\n{func_name}({func_args})\n\n[ERROR]:\n\n{str(e)}\n</sysActionError>🚨"
                    self.inject_proxy_user_msg(error_result)
                    return ""
            unknown_result = f"🚨<sysActionError>\nUnknown action: {func_name}\n</sysActionError>🚨"
            self.inject_proxy_user_msg(unknown_result)
            return ""
            
        return re.sub(
            r'<sysAction>\s*(\w+)\s*\((.*?)\)\s*</sysAction>',
            replace_action,
            text,
            flags=re.DOTALL
        )