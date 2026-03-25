from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from ..models.domain import ModelInvocationError, ModelResult

logger = logging.getLogger("backend.adapters")


class BaseModelAdapter(ABC):
    @abstractmethod
    async def invoke(
        self,
        model_id: str,
        prompt: str,
        parameters: dict,
        max_tokens: int,
    ) -> ModelResult:
        pass


class MockModelAdapter(BaseModelAdapter):
    async def invoke(
        self,
        model_id: str,
        prompt: str,
        parameters: dict,
        max_tokens: int,
    ) -> ModelResult:
        content = f"[MOCK RESPONSE for {model_id}]: {prompt[:80]}..."
        return ModelResult(
            content=content,
            tokens_used=len(content.split()) + 10,
            model_id=model_id,
            finish_reason="end_turn",
        )


class ConfigErrorAdapter(BaseModelAdapter):
    def __init__(self, message: str):
        self.message = message

    async def invoke(
        self,
        model_id: str,
        prompt: str,
        parameters: dict,
        max_tokens: int,
    ) -> ModelResult:
        raise ModelInvocationError(self.message)


class LiteLLMAdapter(BaseModelAdapter):
    async def invoke(
        self,
        model_id: str,
        prompt: str,
        parameters: dict,
        max_tokens: int,
    ) -> ModelResult:
        try:
            import litellm

            response = await litellm.acompletion(
                model=model_id,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                **parameters,
            )
            return ModelResult(
                content=response.choices[0].message.content,
                tokens_used=response.usage.total_tokens,
                model_id=model_id,
                finish_reason=response.choices[0].finish_reason,
            )
        except Exception as exc:
            logger.error("Model invocation failed for %s: %s", model_id, exc)
            raise ModelInvocationError(f"Model {model_id} invocation failed: {exc}") from exc


class AnthropicAdapter(BaseModelAdapter):
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def invoke(
        self,
        model_id: str,
        prompt: str,
        parameters: dict,
        max_tokens: int,
    ) -> ModelResult:
        try:
            import anthropic

            client = anthropic.AsyncAnthropic(api_key=self.api_key)
            response = await client.messages.create(
                model=model_id,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
                **parameters,
            )
            return ModelResult(
                content=response.content[0].text,
                tokens_used=response.usage.input_tokens + response.usage.output_tokens,
                model_id=model_id,
                finish_reason=response.stop_reason,
            )
        except Exception as exc:
            logger.error("Anthropic invocation failed for %s: %s", model_id, exc)
            raise ModelInvocationError(f"Model {model_id} invocation failed: {exc}") from exc


class GeminiAdapter(BaseModelAdapter):
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def invoke(
        self,
        model_id: str,
        prompt: str,
        parameters: dict,
        max_tokens: int,
    ) -> ModelResult:
        try:
            import google.generativeai as genai

            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(model_id)
            response = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(max_output_tokens=max_tokens),
            )
            return ModelResult(
                content=response.text,
                tokens_used=response.usage_metadata.total_token_count if hasattr(response, "usage_metadata") else 0,
                model_id=model_id,
                finish_reason="stop",
            )
        except Exception as exc:
            logger.error("Gemini invocation failed for %s: %s", model_id, exc)
            raise ModelInvocationError(f"Model {model_id} invocation failed: {exc}") from exc


def get_adapter(adapter_type: str, settings=None) -> BaseModelAdapter:
    if adapter_type == "mock":
        if not (settings and getattr(settings, "allow_mock_adapter", False)):
            return ConfigErrorAdapter(
                "Mock adapter is disabled. Set ALLOW_MOCK_ADAPTER=true only for non-production testing.",
            )
        return MockModelAdapter()
    elif adapter_type == "litellm":
        return LiteLLMAdapter()
    elif adapter_type == "anthropic":
        if settings and settings.anthropic_api_key:
            return AnthropicAdapter(settings.anthropic_api_key)
        return ConfigErrorAdapter("ANTHROPIC_API_KEY is required when MODEL_ADAPTER_TYPE=anthropic.")
    elif adapter_type == "gemini":
        if settings and settings.google_api_key:
            return GeminiAdapter(settings.google_api_key)
        return ConfigErrorAdapter("GOOGLE_API_KEY is required when MODEL_ADAPTER_TYPE=gemini.")
    else:
        return ConfigErrorAdapter(f"Unsupported MODEL_ADAPTER_TYPE: {adapter_type}")
