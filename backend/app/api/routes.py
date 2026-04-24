"""
FastAPI routes — all REST endpoints and agent chat endpoints.
"""

import uuid
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.database import get_db
from app.db.models import HCPInteraction, HCP, SentimentEnum, InteractionTypeEnum
from app.models.schemas import (
    InteractionCreate,
    InteractionUpdate,
    InteractionResponse,
    HCPCreate,
    HCPResponse,
    ChatRequest,
    ChatResponse,
    FollowUpResponse,
)
from app.agent.graph import run_agent, get_session_history
from app.agent.tools import suggest_followup

logger = logging.getLogger(__name__)
router = APIRouter()


# ═══════════════════════════════════════════════════════════════════════════════
# HCP ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/hcps", response_model=List[HCPResponse])
async def list_hcps(
    search: Optional[str] = Query(None, description="Search HCPs by name"),
    db: AsyncSession = Depends(get_db),
):
    """List all HCPs, optionally filtered by name search."""
    query = select(HCP).order_by(HCP.name)
    if search:
        query = query.where(HCP.name.ilike(f"%{search}%"))
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/hcps", response_model=HCPResponse, status_code=201)
async def create_hcp(hcp_data: HCPCreate, db: AsyncSession = Depends(get_db)):
    """Create a new HCP record."""
    # Check for duplicate
    existing = await db.execute(select(HCP).where(HCP.name.ilike(hcp_data.name)))
    if existing.scalars().first():
        raise HTTPException(status_code=409, detail=f"HCP '{hcp_data.name}' already exists")
    hcp = HCP(id=uuid.uuid4(), **hcp_data.model_dump())
    db.add(hcp)
    await db.flush()
    await db.refresh(hcp)
    return hcp


# ═══════════════════════════════════════════════════════════════════════════════
# INTERACTION ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/interactions", response_model=InteractionResponse, status_code=201)
async def create_interaction(
    data: InteractionCreate, db: AsyncSession = Depends(get_db)
):
    """Log a new HCP interaction."""
    interaction = HCPInteraction(
        id=uuid.uuid4(),
        hcp_name=data.hcp_name,
        interaction_type=InteractionTypeEnum(data.interaction_type.value),
        interaction_date=data.interaction_date,
        interaction_time=data.interaction_time,
        attendees=data.attendees or [],
        topics_discussed=data.topics_discussed,
        materials_shared=data.materials_shared or [],
        samples_distributed=data.samples_distributed or [],
        sentiment=SentimentEnum(data.sentiment.value) if data.sentiment else SentimentEnum.Neutral,
        outcomes=data.outcomes,
        follow_up_actions=data.follow_up_actions,
        ai_summary=data.ai_summary,
    )

    # Auto-upsert HCP
    existing_hcp = await db.execute(
        select(HCP).where(HCP.name.ilike(data.hcp_name))
    )
    if not existing_hcp.scalars().first():
        db.add(HCP(id=uuid.uuid4(), name=data.hcp_name))

    db.add(interaction)
    await db.flush()
    await db.refresh(interaction)
    return interaction


@router.get("/interactions", response_model=List[InteractionResponse])
async def list_interactions(
    hcp_name: Optional[str] = Query(None),
    sentiment: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List all interactions with optional filters."""
    query = select(HCPInteraction).order_by(HCPInteraction.created_at.desc()).limit(limit).offset(offset)
    if hcp_name:
        query = query.where(HCPInteraction.hcp_name.ilike(f"%{hcp_name}%"))
    if sentiment:
        try:
            query = query.where(HCPInteraction.sentiment == SentimentEnum(sentiment))
        except ValueError:
            pass
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/interactions/{interaction_id}", response_model=InteractionResponse)
async def get_interaction(interaction_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get a single interaction by ID."""
    result = await db.execute(
        select(HCPInteraction).where(HCPInteraction.id == interaction_id)
    )
    interaction = result.scalars().first()
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")
    return interaction


@router.put("/interactions/{interaction_id}", response_model=InteractionResponse)
async def update_interaction(
    interaction_id: uuid.UUID,
    data: InteractionUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing interaction (partial update supported)."""
    result = await db.execute(
        select(HCPInteraction).where(HCPInteraction.id == interaction_id)
    )
    interaction = result.scalars().first()
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "interaction_type" and value is not None:
            value = InteractionTypeEnum(value.value if hasattr(value, 'value') else value)
        elif field == "sentiment" and value is not None:
            value = SentimentEnum(value.value if hasattr(value, 'value') else value)
        setattr(interaction, field, value)

    await db.flush()
    await db.refresh(interaction)
    return interaction


@router.delete("/interactions/{interaction_id}", status_code=204)
async def delete_interaction(
    interaction_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    """Delete an interaction by ID."""
    result = await db.execute(
        select(HCPInteraction).where(HCPInteraction.id == interaction_id)
    )
    interaction = result.scalars().first()
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")
    await db.delete(interaction)


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT / CHAT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/agent/chat", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest):
    """Send a message to the LangGraph AI agent."""
    try:
        result = await run_agent(request.message, request.session_id)
        return ChatResponse(
            reply=result["reply"],
            session_id=result["session_id"],
            extracted_interaction=result.get("extracted_interaction"),
            interaction_data=result.get("interaction_data"),
            tool_used=result.get("tool_used"),
        )
    except Exception as e:
        logger.error(f"Agent chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")


@router.get("/agent/history/{session_id}")
async def get_chat_history(session_id: str):
    """Get the chat history for a session."""
    history = get_session_history(session_id)
    return {"session_id": session_id, "messages": history, "count": len(history)}


@router.post("/agent/suggest-followup/{interaction_id}", response_model=FollowUpResponse)
async def suggest_followup_endpoint(
    interaction_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    """Generate AI follow-up suggestions for a specific interaction."""
    # Verify interaction exists
    result = await db.execute(
        select(HCPInteraction).where(HCPInteraction.id == interaction_id)
    )
    interaction = result.scalars().first()
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")

    try:
        import json
        raw = await suggest_followup.ainvoke({"interaction_id": str(interaction_id)})
        data = json.loads(raw) if isinstance(raw, str) else raw
        follow_ups = data.get("follow_ups", [])
    except Exception as e:
        logger.error(f"Follow-up suggestion error: {e}", exc_info=True)
        follow_ups = [
            "Schedule a follow-up call within one week",
            "Send product information materials via email",
            "Update CRM with key discussion points",
        ]

    return FollowUpResponse(interaction_id=interaction_id, follow_ups=follow_ups)
