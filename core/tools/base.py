from abc import ABC, abstractmethod

class BaseTool(ABC):
    """Base class for all tools."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """The name of the tool as it will be called in sysAction"""
        pass
        
    @property
    @abstractmethod
    def description(self) -> str:
        """Detailed description of how to use the tool, shown by get_tool_info"""
        pass
        
    @abstractmethod
    def __call__(self, *args, **kwargs):
        """Execute the tool's functionality"""
        pass