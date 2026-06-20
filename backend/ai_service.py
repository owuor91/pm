import os
import json
from typing import Optional
import httpx


class AIService:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        self.base_url = base_url or os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        self.model = os.environ.get("OPENROUTER_MODEL", "openai/gpt-oss-120b:free")

    def is_configured(self) -> bool:
        """Check if the AI service is properly configured."""
        return bool(self.api_key)

    def call_ai_messages(self, messages: list[dict], json_mode: bool = False) -> str:
        if not self.is_configured():
            raise ValueError("OPENROUTER_API_KEY is not set")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": messages,
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

    def call_ai(self, prompt: str, json_mode: bool = False) -> str:
        """Call the OpenRouter AI API with the given prompt."""
        return self.call_ai_messages([{"role": "user", "content": prompt}], json_mode=json_mode)

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

    def call_ai_with_board_context(
        self,
        prompt: str,
        board_state: dict,
        conversation: Optional[list[dict]] = None,
    ) -> str:
        """Call AI with the full board context for structured output."""
        system_prompt = (
            "You are a helpful Kanban board assistant.\n"
            "You can suggest board updates like creating cards, moving cards between columns, or renaming columns.\n\n"
            "When the user asks you to make changes to the board, respond with a JSON object containing:\n"
            "{\n"
            '  "message": "Your response to the user",\n'
            '  "boardUpdate": {\n'
            '    "newCards": [{"id": "auto-generated-id", "title": "Card title", "details": "Card details", "columnId": "target-column-id"}],\n'
            '    "updatedCards": [{"id": "card-id", "title": "New title", "details": "New details", "columnId": "new-column-id"}],\n'
            '    "deletedCardIds": ["card-id-to-delete"],\n'
            '    "updatedColumns": [{"id": "col-id", "title": "New column name"}]\n'
            "  },\n"
            '  "confidence": 0.95\n'
            "}\n\n"
            "All fields in boardUpdate are optional. Only include the fields you want to change.\n\n"
            f"Current board state (JSON): {json.dumps(board_state)}\n"
        )

        messages = [{"role": "system", "content": system_prompt}]
        if conversation:
            messages.extend(conversation)
        messages.append({"role": "user", "content": prompt})
        return self.call_ai_messages(messages, json_mode=True)
