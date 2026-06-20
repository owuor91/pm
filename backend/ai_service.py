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

    def call_ai(self, prompt: str, json_mode: bool = False) -> str:
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

        if json_mode:
            payload["response_format"] = {"type": "json_object"}

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

    def call_ai_with_board_context(self, prompt: str, board_state: dict) -> str:
        """Call AI with the full board context for structured output."""
        system_prompt = """You are a helpful Kanban board assistant. The user will give you a command or question about their Kanban board. 
You can suggest board updates like creating cards, moving cards between columns, or renaming columns.

When the user asks you to make changes to the board, respond with a JSON object containing:
{
  "message": "Your response to the user",
  "boardUpdate": {
    "newCards": [{"id": "auto-generated-id", "title": "Card title", "details": "Card details", "columnId": "target-column-id"}],
    "updatedCards": [{"id": "card-id", "title": "New title", "columnId": "new-column-id"}],
    "deletedCardIds": ["card-id-to-delete"],
    "updatedColumns": [{"id": "col-id", "title": "New column name"}]
  },
  "confidence": 0.95
}

All fields in boardUpdate are optional. Only include the fields you want to change.

Current board state:
{board_state}

User request: {prompt}"""

        full_prompt = system_prompt.format(board_state=json.dumps(board_state), prompt=prompt)
        return self.call_ai(full_prompt, json_mode=True)
