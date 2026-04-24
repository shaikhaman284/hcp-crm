import uuid
from datetime import date, time, datetime
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class InteractionType(str, Enum):
    Meeting = "Meeting"
    Call = "Call"
    Email = "Email"
    Conference = "Conference"
    Visit = "Visit"


class Sentiment(str, Enum):
    Positive = "Positive"
    Neutral = "Neutral"
    Negative = "Negative"


# ─── HCP Schemas ────────────────────────────────────────────────────────────

class HCPBase(BaseModel):
    name: str
    specialization: Optional[str] = None
    hospital: Optional[str] = None


class HCPCreate(HCPBase):
    pass


class HCPResponse(HCPBase):
    id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Interaction Schemas ─────────────────────────────────────────────────────

class InteractionCreate(BaseModel):
    hcp_name: str
    interaction_type: InteractionType = InteractionType.Meeting
    interaction_date: Optional[date] = None
    interaction_time: Optional[time] = None
    attendees: Optional[List[str]] = Field(default_factory=list)
    topics_discussed: Optional[str] = None
    materials_shared: Optional[List[str]] = Field(default_factory=list)
    samples_distributed: Optional[List[str]] = Field(default_factory=list)
    sentiment: Optional[Sentiment] = Sentiment.Neutral
    outcomes: Optional[str] = None
    follow_up_actions: Optional[str] = None
    ai_summary: Optional[str] = None


class InteractionUpdate(BaseModel):
    hcp_name: Optional[str] = None
    interaction_type: Optional[InteractionType] = None
    interaction_date: Optional[date] = None
    interaction_time: Optional[time] = None
    attendees: Optional[List[str]] = None
    topics_discussed: Optional[str] = None
    materials_shared: Optional[List[str]] = None
    samples_distributed: Optional[List[str]] = None
    sentiment: Optional[Sentiment] = None
    outcomes: Optional[str] = None
    follow_up_actions: Optional[str] = None
    ai_summary: Optional[str] = None


class InteractionResponse(BaseModel):
    id: uuid.UUID
    hcp_name: str
    interaction_type: InteractionType
    interaction_date: Optional[date] = None
    interaction_time: Optional[time] = None
    attendees: Optional[List[str]] = None
    topics_discussed: Optional[str] = None
    materials_shared: Optional[List[str]] = None
    samples_distributed: Optional[List[str]] = None
    sentiment: Optional[Sentiment] = None
    outcomes: Optional[str] = None
    follow_up_actions: Optional[str] = None
    ai_summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─── Agent / Chat Schemas ────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str
    timestamp: Optional[datetime] = None


class ChatRequest(BaseModel):
    message: str
    session_id: str


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    extracted_interaction: Optional[InteractionCreate] = None
    interaction_data: Optional[Dict[str, Any]] = None
    tool_used: Optional[str] = None


class FollowUpResponse(BaseModel):
    interaction_id: uuid.UUID
    follow_ups: List[str]


class SentimentAnalysisResponse(BaseModel):
    sentiment: Sentiment
    confidence: float
    reasoning: str
