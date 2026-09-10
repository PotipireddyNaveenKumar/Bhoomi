import os
import logging
from typing import Optional
from app.core.config import settings
from app.services.llm.base import LLMProvider
from app.services.llm.mock_provider import MockLLMProvider
from app.services.llm.openai_provider import OpenAIProvider
from app.services.llm.gemini_provider import GeminiProvider

logger = logging.getLogger(__name__)

def get_llm_provider(provider_name: Optional[str] = None) -> LLMProvider:
    """
    Factory function resolving the active LLM Provider.
    Configurable via LLM_PROVIDER environment variable or app settings.
    Clean fallback to MockLLMProvider ensures CI/CD and offline tests never fail.
    """
    name = (provider_name or os.environ.get("LLM_PROVIDER") or settings.LLM_PROVIDER).lower().strip()
    
    if name == "openai":
        api_key = os.environ["OPENAI_API_KEY"] if "OPENAI_API_KEY" in os.environ else settings.OPENAI_API_KEY
        if api_key and not api_key.startswith("your_"):
            return OpenAIProvider(
                api_key=api_key,
                base_url="https://api.openai.com/v1",
                model="gpt-4o-mini",
                provider_name="openai"
            )
        if settings.is_production:
            raise RuntimeError(
                "Production configuration error: OPENAI_API_KEY must be provided when LLM_PROVIDER='openai'. "
                "Silent fallback to MockLLMProvider is disabled in production."
            )
        logger.info("OpenAI API key not provided or placeholder detected. Using MockLLMProvider.")
        return MockLLMProvider()

    elif name == "gemini":
        api_key = os.environ["GEMINI_API_KEY"] if "GEMINI_API_KEY" in os.environ else settings.GEMINI_API_KEY
        if api_key and not api_key.startswith("your_"):
            return GeminiProvider(
                api_key=api_key,
                model=os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
            )
        if settings.is_production:
            raise RuntimeError(
                "Production configuration error: GEMINI_API_KEY must be provided when LLM_PROVIDER='gemini'. "
                "Silent fallback to MockLLMProvider is disabled in production."
            )
        logger.info("Gemini API key not provided or placeholder detected. Using MockLLMProvider.")
        return MockLLMProvider()

    elif name == "groq":
        api_key = os.environ["GROQ_API_KEY"] if "GROQ_API_KEY" in os.environ else settings.GROQ_API_KEY
        if api_key and not api_key.startswith("your_"):
            groq_model = os.environ.get("GROQ_MODEL") or getattr(settings, "GROQ_MODEL", "qwen/qwen3.8-27b")
            return OpenAIProvider(
                api_key=api_key,
                base_url="https://api.groq.com/openai/v1",
                model=groq_model,
                provider_name="groq"
            )
        if settings.is_production:
            raise RuntimeError(
                "Production configuration error: GROQ_API_KEY must be provided when LLM_PROVIDER='groq'. "
                "Silent fallback to MockLLMProvider is disabled in production."
            )
        logger.info("Groq API key not provided or placeholder detected. Using MockLLMProvider.")
        return MockLLMProvider()

    else:
        if settings.is_production and name not in ("mock", ""):
            raise RuntimeError(
                f"Production configuration error: LLM provider '{name}' is not supported in production."
            )
        return MockLLMProvider()
