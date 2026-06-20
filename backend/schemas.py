from pydantic import BaseModel
from typing import Optional, Dict, Any, List


class CardUpdate(BaseModel):
    """Represents an update to a card in the Kanban board."""
    id: str
    title: Optional[str] = None
    details: Optional[str] = None
    columnId: Optional[str] = None


class ColumnUpdate(BaseModel):
    """Represents an update to a column in the Kanban board."""
    id: str
    title: Optional[str] = None


class BoardUpdate(BaseModel):
    """Represents updates to apply to the Kanban board."""
    newCards: Optional[List[Dict[str, Any]]] = None
    updatedCards: Optional[List[CardUpdate]] = None
    deletedCardIds: Optional[List[str]] = None
    updatedColumns: Optional[List[ColumnUpdate]] = None


class AIResponse(BaseModel):
    """Structured response from the AI with optional board updates."""
    message: str
    boardUpdate: Optional[BoardUpdate] = None
    confidence: Optional[float] = None


class AIRequest(BaseModel):
    """Request to the AI with board context and user prompt."""
    userId: int
    prompt: str
