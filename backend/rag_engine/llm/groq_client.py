"""
groq_client.py
Thin wrapper around the Groq API (OpenAI-compatible) for chat completions.
Centralizes model selection, retries, and error handling so chains don't
each reimplement API call logic.
"""

import os
import time
import logging
from typing import List, Dict, Optional

from dotenv import load_dotenv
from groq import Groq, GroqError

# Ensures GROQ_API_KEY is available even when this module is imported/run
# standalone (e.g. `python -m rag_engine.llm.groq_client`), without relying
# on api.core.config having already called load_dotenv() first. Safe to
# call multiple times — subsequent calls are no-ops if vars are already set.
load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "openai/gpt-oss-20b"


class GroqClient:
    """Wraps the Groq chat completions API with retry logic."""

    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_MODEL,
                 max_retries: int = 3, timeout: int = 30):
        resolved_key = api_key or os.environ.get("GROQ_API_KEY")
        if not resolved_key:
            raise ValueError("GROQ_API_KEY not set. Pass api_key or set the env var.")

        self.client = Groq(api_key=resolved_key)
        self.model = model
        self.max_retries = max_retries
        self.timeout = timeout

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> str:
        """
        Send a chat completion request. messages follow OpenAI-style format:
        [{"role": "system"|"user"|"assistant", "content": "..."}]
        """
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=self.timeout,
                )
                return response.choices[0].message.content.strip()
            except GroqError as exc:
                last_error = exc
                wait = 2 ** attempt
                logger.warning(
                    "Groq API call failed (attempt %d/%d): %s. Retrying in %ds",
                    attempt, self.max_retries, exc, wait,
                )
                time.sleep(wait)

        logger.error("Groq API call failed after %d attempts: %s", self.max_retries, last_error)
        raise RuntimeError(f"Groq API call failed: {last_error}")

    def complete(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        """Convenience method for single-turn prompts."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return self.chat(messages, **kwargs)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    client = GroqClient()
    answer = client.complete(
        "In one sentence, what is retrieval-augmented generation?",
        system_prompt="You are a concise research assistant.",
    )
    print(answer)