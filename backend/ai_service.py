import os
import json
from typing import Optional
import httpx


class AIService:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        self.base_url = base_url or os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        self.model = "openai/gpt-4o-mini"

    def is_configured(self) -> bool:
        """Check if the AI service is properly configured."""
        return bool(self.api_key)

    def call_ai(self, prompt: str) -> str:
        """Call the OpenRouter AI API with the given prompt."""
        if not self.is_configured():
            raise ValueError("OPENROUTER_API_KEY is not set")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
        }

        try:
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except httpx.HTTPError as e:
            raise RuntimeError(f"AI API call failed: {e}")

    def test_connectivity(self) -> dict:
        """Test the AI connectivity with a simple prompt."""
        try:
            result = self.call_ai("What is 2 + 2? Respond with just the number.")
            return {
                "status": "success",
                "result": result.strip(),
                "model": self.model,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "model": self.model,
            }
