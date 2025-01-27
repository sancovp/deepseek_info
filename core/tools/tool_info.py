from .base import BaseTool

class ViewTools(BaseTool):
    """Tool to list available tools."""
    
    def __init__(self, tools_dict):
        self.tools_dict = tools_dict
    
    @property
    def name(self) -> str:
        return "view_tools"
        
    @property
    def description(self) -> str:
        return """List all available tools.
        
Example:
    <sysAction>view_tools()</sysAction>
    
Notes:
    - Shows tool names and brief descriptions
    - Use get_tool_info for detailed documentation"""
        
    def __call__(self) -> str:
        result = "Available Tools:\n\n"
        for tool_name, tool in self.tools_dict.items():
            if tool_name not in ["view_tools", "get_tool_info"]:
                brief_desc = tool.description.split("\n")[0]
                result += f"{tool_name} - {brief_desc}\n"
        return result

class GetToolInfo(BaseTool):
    """Tool to get detailed info about a specific tool."""
    
    def __init__(self, tools_dict):
        self.tools_dict = tools_dict
    
    @property
    def name(self) -> str:
        return "get_tool_info"
        
    @property
    def description(self) -> str:
        return """Get detailed documentation for a specific tool.
        
Arguments:
    tool_name: str - Name of the tool to get info about
    
Example:
    <sysAction>get_tool_info("bash")</sysAction>
    
Notes:
    - Shows full documentation including examples
    - Use view_tools to see list of available tools"""
        
    def __call__(self, tool_name: str) -> str:
        if tool_name not in self.tools_dict:
            return f"Error: Tool '{tool_name}' not found"
        return f"Documentation for {tool_name}:\n\n{self.tools_dict[tool_name].description}"