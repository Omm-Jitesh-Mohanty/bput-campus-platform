"""
Abstract LLM client interface.
Any concrete client (Ollama, OpenAI, Anthropic) implements this.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMResponse:
    """Standardized LLM output."""
    text: str
    success: bool
    model: str = ''
    latency_ms: int = 0
    error: Optional[str] = None

    def __bool__(self):
        return self.success and bool(self.text.strip())


class BaseLLMClient(ABC):
    """Every LLM client must implement `generate`."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system: str = '',
        json_mode: bool = False,
        temperature: float = 0.3,
        max_tokens: int = 500,
    ) -> LLMResponse:
        """
        Generate text from prompt.
        Must NEVER raise — always return LLMResponse with success flag.
        """
        pass