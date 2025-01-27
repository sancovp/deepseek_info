from .base import BaseTool
from .bash import BashTool
from .editor import StrReplaceEditor
from .tool_info import ViewTools, GetToolInfo

def load_tools():
    """Load all available tools."""
    tools = {
        "bash": BashTool(),
        "str_replace_editor": StrReplaceEditor(),
    }
    
    # Add tool management tools
    tools["view_tools"] = ViewTools(tools)
    tools["get_tool_info"] = GetToolInfo(tools)
    
    return tools