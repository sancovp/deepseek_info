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

TOOL_DOCS = """Available Tools:

1. bash(command: str) -> str
   Execute a bash command and return its output.
   - command: The bash command to execute
   Example: <sysAction>bash("ls -la")</sysAction>

2. str_replace_editor(command: str, path: str, ...) -> str
   Edit files with various commands:
   - command: The action to perform (view/create/str_replace/insert/undo_edit)
   - path: Full path to the file
   Additional parameters based on command:
   * view: view_range=[start,end] (optional)
   * create: file_text=content
   * str_replace: old_str=existing, new_str=replacement
   * insert: insert_line=N, new_str=content
   Example: <sysAction>str_replace_editor(command="view", path="/path/to/file")</sysAction>

Important Notes:
- For str_replace, old_str must match EXACTLY (watch whitespace!)
- Make sure paths are absolute (start with /)
- One tool action at a time, wait for results
"""

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
        
        # Set up the tools
        import subprocess
        import json
        import os
        from pathlib import Path
        
        def bash(self, command: str) -> str:
            """Execute a bash command and return its output"""
            try:
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
                return result.stdout if result.returncode == 0 else f"Error: {result.stderr}"
            except Exception as e:
                return f"Error executing command: {str(e)}"
                
        def str_replace_editor(self, command_str: str) -> str:
            """Execute editor commands with proper argument parsing"""
            try:
                # Parse the command string into a dict
                import re
                params = {}
                # Extract named parameters (key="value" or key=value)
                pattern = r'(\w+)=(?:"([^"]*?)"|([^,\s]*?)(?=\s*(?:\w+=|$)))'
                matches = re.finditer(pattern, command_str)
                for match in matches:
                    key = match.group(1)
                    value = match.group(2) if match.group(2) is not None else match.group(3)
                    params[key] = value
                
                if "command" not in params:
                    return "Error: command parameter is required"
                    
                if params["command"] == "view":
                    if "path" not in params:
                        return "Error: path parameter is required"
                    path = Path(params["path"])
                    if not path.exists():
                        return f"Error: {path} does not exist"
                    if path.is_file():
                        content = path.read_text()
                        if "view_range" in params:
                            try:
                                range_list = json.loads(params["view_range"])
                                lines = content.splitlines()
                                content = "\n".join(lines[range_list[0]-1:range_list[1]])
                            except:
                                return "Error: Invalid view_range format"
                        return content
                    else:
                        return "\n".join(str(p) for p in path.glob("**/*") if not p.name.startswith("."))
                        
                elif params["command"] == "create":
                    if "path" not in params or "file_text" not in params:
                        return "Error: path and file_text parameters are required"
                    path = Path(params["path"])
                    if path.exists():
                        return f"Error: {path} already exists"
                    path.write_text(params["file_text"])
                    return f"Created {path}"
                    
                elif params["command"] == "str_replace":
                    if not all(k in params for k in ["path", "old_str", "new_str"]):
                        return "Error: path, old_str, and new_str parameters are required"
                    path = Path(params["path"])
                    if not path.exists():
                        return f"Error: {path} does not exist"
                    content = path.read_text()
                    if params["old_str"] not in content:
                        return "Error: old_str not found exactly as specified"
                    new_content = content.replace(params["old_str"], params["new_str"])
                    path.write_text(new_content)
                    return f"Replaced content in {path}"
                    
                elif params["command"] == "insert":
                    if not all(k in params for k in ["path", "insert_line", "new_str"]):
                        return "Error: path, insert_line, and new_str parameters are required"
                    path = Path(params["path"])
                    if not path.exists():
                        return f"Error: {path} does not exist"
                    try:
                        insert_line = int(params["insert_line"])
                    except:
                        return "Error: insert_line must be an integer"
                    lines = path.read_text().splitlines()
                    if insert_line < 0 or insert_line > len(lines):
                        return f"Error: insert_line must be between 0 and {len(lines)}"
                    lines.insert(insert_line, params["new_str"])
                    path.write_text("\n".join(lines))
                    return f"Inserted content at line {insert_line} in {path}"
                    
                else:
                    return f"Error: Unknown command {params['command']}"
                    
            except Exception as e:
                return f"Error: {str(e)}"
        
        # Add the tools to self
        self.bash = bash.__get__(self)
        self.str_replace_editor = str_replace_editor.__get__(self)
        
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