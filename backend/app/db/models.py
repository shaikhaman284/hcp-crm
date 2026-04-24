import uuid
import enum
from datetime import datetime, date, time
from sqlalchemy import (
    Column, String, Text, Date, Time, DateTime, Enum as SAEnum,
    ForeignKey, ARRAY
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class InteractionTypeEnum(str, enum.Enum):
    Meeting = "Meeting"
    Call = "Call"
    Email = "Email"
    Conference = "Conference"
    Visit = "Visit"


class SentimentEnum(str, enum.Enum):
    Positive = "Positive"
    Neutral = "Neutral"
    Negative = "Negative"


class HCP(Base):
    __tablename__ = "hcps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    specialization = Column(String(255), nullable=True)
    hospital = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class HCPInteraction(Base):
    __tablename__ = "hcp_interactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hcp_name = Column(String(255), nullable=False, index=True)
    interaction_type = Column(
        SAEnum(InteractionTypeEnum, name="interaction_type_enum"),
        nullable=False,
        default=InteractionTypeEnum.Meeting,
    )
    interaction_date = Column(Date, nullable=True)
    interaction_time = Column(Time, nullable=True)
    attendees = Column(ARRAY(Text), nullable=True, default=list)
    topics_discussed = Column(Text, nullable=True)
    materials_shared = Column(ARRAY(Text), nullable=True, default=list)
    samples_distributed = Column(ARRAY(Text), nullable=True, default=list)
    sentiment = Column(
        SAEnum(SentimentEnum, name="sentiment_enum"),
        nullable=True,
        default=SentimentEnum.Neutral,
    )
    outcomes = Column(Text, nullable=True)
    follow_up_actions = Column(Text, nullable=True)
    ai_summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
