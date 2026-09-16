"""
Ollama LLM client.
Calls the local Ollama server. Handles timeouts, retries, and fallbacks.
"""
import time
import logging
import requests
from django.conf import settings

from .base import BaseLLMClient, LLMResponse

logger = logging.getLogger('ai_engine')


class OllamaClient(BaseLLMClient):
    """Local Ollama client. Fully offline-capable."""

    def __init__(self, url=None, model=None, timeout=None):
        self.url = url or getattr(settings, 'OLLAMA_URL', 'http://localhost:11434/api/generate')
        self.model = model or getattr(settings, 'OLLAMA_MODEL', 'llama3.2:3b')
        self.timeout = timeout or getattr(settings, 'LLM_TIMEOUT', 60)

    def generate(
        self,
        prompt,
        system='',
        json_mode=False,
        temperature=0.3,
        max_tokens=500,
    ):
        start = time.time()
        payload = {
            'model': self.model,
            'prompt': prompt,
            'system': system,
            'stream': False,
            'options': {
                'temperature': temperature,
                'num_predict': max_tokens,
            },
        }
        if json_mode:
            payload['format'] = 'json'

        try:
            r = requests.post(self.url, json=payload, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
            text = data.get('response', '').strip()

            return LLMResponse(
                text=text,
                success=True,
                model=self.model,
                latency_ms=int((time.time() - start) * 1000),
            )
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"Ollama not reachable: {e}")
            return LLMResponse(
                text='',
                success=False,
                model=self.model,
                latency_ms=int((time.time() - start) * 1000),
                error='Ollama server unreachable',
            )
        except requests.exceptions.Timeout:
            logger.warning(f"Ollama timeout after {self.timeout}s")
            return LLMResponse(
                text='', success=False, model=self.model,
                latency_ms=int((time.time() - start) * 1000),
                error='Ollama timeout',
            )
        except Exception as e:
            logger.exception(f"Ollama error: {e}")
            return LLMResponse(
                text='', success=False, model=self.model,
                latency_ms=int((time.time() - start) * 1000),
                error=str(e),
            )


# ===== Module-level singleton =====
_client = None


def get_llm_client() -> BaseLLMClient:
    """Return a cached LLM client. Swap this out to change providers."""
    global _client
    if _client is None:
        _client = OllamaClient()
    return _client


def generate_text(prompt, system='', json_mode=False, **kwargs) -> LLMResponse:
    """Convenience wrapper — most code should call this."""
    return get_llm_client().generate(prompt, system=system, json_mode=json_mode, **kwargs)