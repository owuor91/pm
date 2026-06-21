from pydantic import BaseModel
from typing import Optional, List, Literal


class CardUpdate(BaseModel):
    id: str
    title: Optional[str] = None
    details: Optional[str] = None
    columnId: Optional[str] = None


class NewCard(BaseModel):
    id: Optional[str] = None
    title: str
    details: Optional[str] = None
    columnId: str


class ColumnUpdate(BaseModel):
    id: str
    title: Optional[str] = None


class BoardUpdate(BaseModel):
    newCards: Optional[List[NewCard]] = None
    updatedCards: Optional[List[CardUpdate]] = None
    deletedCardIds: Optional[List[str]] = None
    updatedColumns: Optional[List[ColumnUpdate]] = None


class AIResponse(BaseModel):
    message: str
    boardUpdate: Optional[BoardUpdate] = None
    confidence: Optional[float] = None


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AIChatRequest(BaseModel):
    userId: int
    prompt: str
    messages: Optional[List[ChatMessage]] = None


class AIChatResponse(BaseModel):
    message: str
    boardState: str
    applied: bool
    confidence: Optional[float] = None
