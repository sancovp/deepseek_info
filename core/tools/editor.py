import json
import re
from pathlib import Path
from .base import BaseTool

class StrReplaceEditor(BaseTool):
    """File editing tool."""
    
    @property
    def name(self) -> str:
        return "str_replace_editor"
        
    @property
    def description(self) -> str:
        return """Edit files with various commands.
        
Commands:
1. view - View file contents
   Required: path
   Optional: view_range=[start,end]
   Example: <sysAction>str_replace_editor('command="view", path="/path/to/file"')</sysAction>
   
2. create - Create new file
   Required: path, file_text
   Example: <sysAction>str_replace_editor('command="create", path="/path/to/file", file_text="content"')</sysAction>
   
3. str_replace - Replace text in file
   Required: path, old_str, new_str
   Example: <sysAction>str_replace_editor('command="str_replace", path="/path/to/file", old_str="old", new_str="new"')</sysAction>
   
4. insert - Insert text at line
   Required: path, insert_line, new_str
   Example: <sysAction>str_replace_editor('command="insert", path="/path/to/file", insert_line=5, new_str="new line"')</sysAction>
   
Notes:
- All paths must be absolute (start with /)
- str_replace requires EXACT match of old_str
- One command at a time
- Wait for results before next command"""
        
    def __call__(self, command_str: str) -> str:
        try:
            # Parse command string into params
            params = {}
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