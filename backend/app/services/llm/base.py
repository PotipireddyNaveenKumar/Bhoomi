from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class ToolCall(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]

class LLMResponse(BaseModel):
    content: str
    tool_calls: Optional[List[ToolCall]] = None
    finish_reason: str = "stop"
    usage: Optional[Dict[str, int]] = None
    provider: str

class LLMProvider(ABC):
    @abstractmethod
    async def generate_response(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
    ) -> LLMResponse:
        """Generate response from language model with structured tool invocation capability."""
        pass
