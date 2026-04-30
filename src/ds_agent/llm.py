from anthropic import Anthropic
from ds_agent.config import Settings

class LLMClientError(Exception):
    """Raised when an LLM request fails."""
    pass

class LLMClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = Anthropic(api_key=settings.anthropic_api_key)

    def complete(
        self,
        user_message: str,
        system: str | None = None,
        max_tokens: int = 1024,
    ) -> str:
        if not user_message.strip():
            raise ValueError("user_message cannot be empty or just whitespace")

        kwargs = {
            "model": self._settings.anthropic_model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": user_message}],
        }
        if system is not None:
            kwargs["system"] = system

        try:
            response = self._client.messages.create(**kwargs)
        except Exception as e:
            raise LLMClientError("LLM request failed") from e

        return response.content[0].text
