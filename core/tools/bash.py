import subprocess
from .base import BaseTool

class BashTool(BaseTool):
    """Execute bash commands."""
    
    @property
    def name(self) -> str:
        return "bash"
        
    @property
    def description(self) -> str:
        return """Execute a bash command and return its output.
        
Arguments:
    command: str - The bash command to execute

Example:
    <sysAction>bash("ls -la")</sysAction>
    
Notes:
    - Command output and errors are returned as text
    - Commands run in the current working directory
    - One command at a time, wait for result before next command"""
        
    def __call__(self, command: str) -> str:
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            return result.stdout if result.returncode == 0 else f"Error: {result.stderr}"
        except Exception as e:
            return f"Error executing command: {str(e)}"