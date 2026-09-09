import json
import logging
from typing import List, Dict, Any, Optional
import httpx
from app.core.config import settings
from app.services.llm.base import LLMProvider, LLMResponse, ToolCall
from app.services.llm.mock_provider import MockLLMProvider

logger = logging.getLogger(__name__)

class OpenAIProvider(LLMProvider):
    """
    Production-grade LLM Provider for OpenAI and OpenAI-compatible endpoints (Groq, Together).
    Enforces deterministic tool calling, structured JSON argument parsing,
    and grounds agricultural reasoning in tool outputs.
    """
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        provider_name: str = "openai",
        timeout: float = 25.0
    ):
        self._api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.provider_name = provider_name
        self.timeout = timeout
        self._fallback_provider = MockLLMProvider()

    def _format_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert BHOOMI ToolRegistry schema into standard OpenAI function definitions."""
        formatted = []
        for t in tools:
            formatted.append({
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t.get("parameters", {"type": "object", "properties": {}})
                }
            })
        return formatted

    async def generate_response(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
    ) -> LLMResponse:
        """
        Executes an asynchronous chat completion request with tool calling capability.
        Guarantees that API keys are never leaked in logs or error messages.
        """
        payload_messages = [{"role": "system", "content": system_prompt}]
        for m in messages:
            payload_messages.append({"role": m["role"], "content": m["content"]})

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json"
        }

        body: Dict[str, Any] = {
            "model": self.model,
            "messages": payload_messages,
            "temperature": temperature,
            "max_tokens": 1024
        }

        if tools:
            body["tools"] = self._format_tools(tools)
            body["tool_choice"] = "auto"

        endpoint = f"{self.base_url}/chat/completions"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(endpoint, headers=headers, json=body)
                
                if resp.status_code != 200:
                    logger.error(
                        f"LLM Provider {self.provider_name} returned non-200 status {resp.status_code}: {resp.text}"
                    )
                    if settings.APP_ENV in ["production", "staging"]:
                        return LLMResponse(
                            content="SERVICE_UNAVAILABLE: The AI language service is temporarily unavailable or experiencing high load. Your farm data and deterministic tools remain safe. Please retry in a moment.",
                            tool_calls=None,
                            finish_reason="error",
                            usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                            provider=self.provider_name
                        )
                    return await self._fallback_provider.generate_response(
                        messages=messages, system_prompt=system_prompt, tools=tools, temperature=temperature
                    )

                data = resp.json()
                choice = data["choices"][0]
                message = choice["message"]
                content = message.get("content") or ""

                tool_calls: Optional[List[ToolCall]] = None
                raw_tool_calls = message.get("tool_calls")
                if raw_tool_calls:
                    tool_calls = []
                    for tc in raw_tool_calls:
                        func = tc.get("function", {})
                        t_name = func.get("name", "")
                        raw_args = func.get("arguments", "{}")
                        try:
                            t_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                        except json.JSONDecodeError:
                            t_args = {}
                        tool_calls.append(ToolCall(tool_name=t_name, arguments=t_args))

                usage = data.get("usage", {})
                usage_dict = {
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0)
                }

                return LLMResponse(
                    content=content,
                    tool_calls=tool_calls,
                    finish_reason=choice.get("finish_reason", "stop"),
                    usage=usage_dict,
                    provider=self.provider_name
                )

        except Exception as e:
            logger.error(f"Error calling {self.provider_name} API ({type(e).__name__}): {e}")
            if settings.APP_ENV in ["production", "staging"]:
                return LLMResponse(
                    content=f"SERVICE_UNAVAILABLE: Unable to connect to AI language service ({type(e).__name__}). Please check server network and try again.",
                    tool_calls=None,
                    finish_reason="error",
                    usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                    provider=self.provider_name
                )
            return await self._fallback_provider.generate_response(
                messages=messages, system_prompt=system_prompt, tools=tools, temperature=temperature
            )
