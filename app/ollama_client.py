"""Ollama client for interacting with Ollama models."""

import json
import asyncio
from collections.abc import AsyncGenerator
from typing import Any

import httpx
from pydantic import BaseModel

from app.settings import get_settings

settings = get_settings()


class OllamaResponse(BaseModel):
    """Response model for Ollama API calls."""

    model: str
    created_at: str
    response: str
    done: bool
    context: list[int] | None = None
    total_duration: int | None = None
    load_duration: int | None = None
    prompt_eval_count: int | None = None
    prompt_eval_duration: int | None = None
    eval_count: int | None = None
    eval_duration: int | None = None


class OllamaClient:
    """Client for interacting with Ollama API."""

    def __init__(self, base_url: str | None = None):
        # Default to localhost for direct Ollama installation
        self.base_url = base_url or settings.ollama_base_url
        self.default_model = settings.ollama_model
        
        # Configure structured timeout for better LLM processing
        self.timeout = httpx.Timeout(
            connect=settings.ollama_timeout_connect,
            read=settings.ollama_timeout_read,  # Long timeout for LLM processing
            write=settings.ollama_timeout_write,
            pool=settings.ollama_timeout_pool,
        )
        self.max_retries = settings.ollama_max_retries

    def _trim_to_sentence_boundary(self, text: str, max_length: int = 1500) -> str:
        """Trim text to max_length at sentence boundary."""
        if len(text) <= max_length:
            return text

        # Find the last sentence boundary within max_length
        truncated = text[:max_length]

        # Look for sentence endings (., !, ?) and trim at the last complete sentence
        sentence_endings = [".", "!", "?"]
        last_sentence_end = -1

        for ending in sentence_endings:
            pos = truncated.rfind(ending)
            if pos > last_sentence_end:
                last_sentence_end = pos

        if last_sentence_end > 0:
            # Include the sentence ending
            return truncated[: last_sentence_end + 1]
        else:
            # No sentence ending found, trim at word boundary
            last_space = truncated.rfind(" ")
            if last_space > 0:
                return truncated[:last_space]
            else:
                # No space found, just truncate
                return truncated

    async def _make_request(
        self, method: str, endpoint: str, data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Make HTTP request to Ollama API with retry logic."""
        url = f"{self.base_url}{endpoint}"
        
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    if method.upper() == "GET":
                        response = await client.get(url)
                    elif method.upper() == "POST":
                        response = await client.post(url, json=data)
                    else:
                        raise ValueError(f"Unsupported HTTP method: {method}")

                    response.raise_for_status()
                    return response.json()
                    
            except (httpx.TimeoutException, httpx.ConnectTimeout, httpx.ReadTimeout) as e:
                last_exception = e
                if attempt < self.max_retries:
                    # Exponential backoff: 2^attempt seconds
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise Exception(f"Ollama request timed out after {self.max_retries + 1} attempts: {str(e)}") from e
            except Exception as e:
                # For non-timeout errors, don't retry
                raise Exception(f"Ollama request failed: {str(e)}") from e
        
        # This should never be reached, but just in case
        if last_exception:
            raise Exception(f"Ollama request failed after all retries: {str(last_exception)}") from last_exception

    async def list_models(self) -> list[dict[str, Any]]:
        """List available models."""
        try:
            response = await self._make_request("GET", "/api/tags")
            return response.get("models", [])
        except Exception as e:
            raise Exception(f"Failed to list models: {str(e)}") from e

    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        system: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> str:
        """Generate text using Ollama model."""
        model = model or self.default_model

        data = {"model": model, "prompt": prompt, "stream": False}

        if system:
            data["system"] = system

        if options:
            data["options"] = options

        try:
            response = await self._make_request("POST", "/api/generate", data)
            return response.get("response", "")
        except Exception as e:
            raise Exception(f"Failed to generate text: {str(e)}") from e

    async def generate_stream(
        self,
        prompt: str,
        model: str | None = None,
        system: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> AsyncGenerator[str, None]:
        """Generate text stream using Ollama model."""
        model = model or self.default_model

        data = {"model": model, "prompt": prompt, "stream": True}

        if system:
            data["system"] = system

        if options:
            data["options"] = options

        url = f"{self.base_url}/api/generate"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("POST", url, json=data) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.strip():
                            try:
                                chunk = json.loads(line)
                                if chunk.get("done", False):
                                    break
                                yield chunk.get("response", "")
                            except json.JSONDecodeError:
                                continue
        except (httpx.TimeoutException, httpx.ConnectTimeout, httpx.ReadTimeout) as e:
            raise Exception(f"Ollama stream request timed out: {str(e)}") from e
        except Exception as e:
            raise Exception(f"Failed to generate text stream: {str(e)}") from e

    async def summarize(self, text: str, language_hint: str | None = None) -> str:
        """Summarize text using Ollama model with deterministic output.

        Args:
            text: The text to summarize
            language_hint: Optional language hint for the source text

        Returns:
            A summary ≤1500 characters, trimmed at sentence boundary
        """
        # Determine the source language for the system prompt
        source_language = language_hint if language_hint else "the source language"

        # System prompt as specified: deterministic, no markdown, ≤1500 chars, preserve key facts
        system_prompt = f"""You are a precise summarization assistant. Create a summary that:
- Captures the key facts and main ideas from the text
- Is written in {source_language} (unless the source is in English, then use English)
- Is deterministic and factual
- Does not use markdown formatting
- Is concise and well-structured
- Preserves essential information while being brief"""

        user_prompt = f"Please summarize the following text:\n\n{text}"

        # Optimization options for faster processing
        optimization_options = {
            "temperature": 0.1,  # Lower temperature for more deterministic output
            "top_p": 0.9,        # Nucleus sampling for efficiency
            "num_predict": 400,  # Limit output tokens to ~1500 chars
            "num_ctx": 4096,     # Context window size
            "repeat_penalty": 1.1,  # Prevent repetition
        }

        try:
            # Generate the summary with optimization options
            summary = await self.generate(
                prompt=user_prompt, 
                model=self.default_model, 
                system=system_prompt,
                options=optimization_options
            )

            # Post-process to ensure ≤1500 characters at sentence boundary
            trimmed_summary = self._trim_to_sentence_boundary(summary, max_length=1500)

            return trimmed_summary

        except Exception as e:
            raise Exception(f"Failed to summarize text: {str(e)}") from e

    async def summarize_text(
        self,
        text: str,
        model: str | None = None,
        max_length: int | None = None,
        language: str = "en",
    ) -> str:
        """Summarize text using Ollama model (legacy method for backward compatibility)."""
        model = model or self.default_model

        # Create a system prompt for summarization
        system_prompt = f"""You are a helpful AI assistant that creates concise summaries.
        Create a summary in {language} that captures the key points and main ideas.
        """

        if max_length:
            system_prompt += f" Keep the summary under {max_length} characters."

        user_prompt = f"Please summarize the following text:\n\n{text}"

        return await self.generate(
            prompt=user_prompt, model=model, system=system_prompt
        )

    async def check_health(self) -> bool:
        """Check if Ollama service is healthy."""
        try:
            await self._make_request("GET", "/api/tags")
            return True
        except Exception:
            return False

    async def get_model_info(self, model: str | None = None) -> dict[str, Any]:
        """Get information about a specific model."""
        model = model or self.default_model

        try:
            response = await self._make_request("POST", "/api/show", {"name": model})
            return response
        except Exception as e:
            raise Exception(f"Failed to get model info: {str(e)}") from e

    async def pull_model(self, model: str) -> dict[str, Any]:
        """Pull a model from Ollama library."""
        try:
            response = await self._make_request("POST", "/api/pull", {"name": model})
            return response
        except Exception as e:
            raise Exception(f"Failed to pull model: {str(e)}") from e
