import json
import logging
from typing import List, Dict, Any, Optional
import httpx
from app.services.llm.base import LLMProvider, LLMResponse, ToolCall
from app.services.llm.mock_provider import MockLLMProvider

logger = logging.getLogger(__name__)

class GeminiProvider(LLMProvider):
    """
    Google Gemini Provider for BHOOMI AI Agent.
    Connects to Google Generative AI API with structured tool invocation,
    low-temperature factual reasoning, and automatic fallback protection.
    """
    def __init__(
        self,
        api_key: str,
        model: Optional[str] = None,
        timeout: float = 25.0
    ):
        import os
        self._api_key = api_key
        self.model = model or os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
        self.timeout = timeout
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/openai"
        self._fallback_provider = MockLLMProvider()

    def _format_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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
                    logger.warning(
                        f"Gemini API returned status {resp.status_code}. Falling back to MockLLMProvider."
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
                    provider="gemini"
                )

        except Exception as e:
            logger.warning(f"Error calling Gemini API ({type(e).__name__}). Falling back safely to MockLLMProvider.")
            return await self._fallback_provider.generate_response(
                messages=messages, system_prompt=system_prompt, tools=tools, temperature=temperature
            )
