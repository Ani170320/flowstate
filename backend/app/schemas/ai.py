import uuid
from typing import List, Optional
from pydantic import BaseModel, Field


class SubtaskItem(BaseModel):
    title: str
    description: Optional[str] = None


class SubtaskGenerationRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=255, description="High-level task or feature summary")
    description: Optional[str] = Field(None, max_length=5000, description="Optional extra requirements or context")
    labels: Optional[List[str]] = Field(default_factory=list)


class SubtaskGenerationResponse(BaseModel):
    suggested_title: str
    description: str
    estimated_hours: int = 8
    priority: str = "medium"
    subtasks: List[SubtaskItem] = Field(default_factory=list)
    labels: List[str] = Field(default_factory=list)


class AssigneeSuggestionRequest(BaseModel):
    task_title: str
    task_description: Optional[str] = None
    department: Optional[str] = None


class AssigneeSuggestionResponse(BaseModel):
    recommended_user_id: Optional[str] = None
    recommended_user_name: Optional[str] = None
    confidence: float = 0.85
    reasoning: str
    suggested_hours: int = 8


class AIChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str


class AIChatRequest(BaseModel):
    messages: List[AIChatMessage] = Field(..., min_length=1)
    context_scope: Optional[str] = "workspace"


class AIChatResponse(BaseModel):
    reply: str
    references: Optional[List[dict]] = None


class SprintRetroRequest(BaseModel):
    timeframe_days: int = Field(default=14, ge=1, le=90)


class SprintRetroResponse(BaseModel):
    markdown_report: str
    summary: str
    highlights: List[str] = Field(default_factory=list)
    bottlenecks: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
