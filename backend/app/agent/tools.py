"""
LangGraph Agent Tools — 5 mandatory tools for HCP CRM AI assistant.
Each tool is a proper LangChain @tool decorated function that interacts
with the PostgreSQL database via SQLAlchemy and calls Groq LLM.
"""

import os
import json
import uuid
import logging
from datetime import date, time, datetime
from typing import Optional, Any

from dotenv import load_dotenv
from langchain_core.tools import tool
from groq import Groq

from app.db.database import AsyncSessionLocal
from app.db.models import HCPInteraction, HCP, SentimentEnum, InteractionTypeEnum
from sqlalchemy import select, or_, func

load_dotenv()

logger = logging.getLogger(__name__)

PRIMARY_MODEL = os.getenv("PRIMARY_MODEL", "llama-3.3-70b-versatile")
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "llama-3.3-70b-versatile")

_groq_client: Optional[Groq] = None


def get_groq_client() -> Groq:
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY", "")
        _groq_client = Groq(api_key=api_key)
    return _groq_client


def call_groq(prompt: str, system: str = "", json_mode: bool = False) -> str:
    """Call Groq with primary model, fall back to secondary on error."""
    client = get_groq_client()
    kwargs: dict[str, Any] = {
        "messages": [
            {"role": "system", "content": system or "You are a helpful AI assistant for a pharmaceutical CRM."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 2048,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    for model in [PRIMARY_MODEL, FALLBACK_MODEL]:
        try:
            kwargs["model"] = model
            resp = client.chat.completions.create(**kwargs)
            return resp.choices[0].message.content or ""
        except Exception as e:
            logger.warning(f"Groq model {model} failed: {e}")

    return "{}" if json_mode else "I encountered an error processing your request."


def _safe_enum(value: Optional[str], enum_cls, default):
    """Safely coerce a string to an Enum member."""
    if not value:
        return default
    try:
        return enum_cls(value.strip().capitalize())
    except ValueError:
        return default


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except (ValueError, AttributeError):
            continue
    return None


def _parse_time(value: Optional[str]) -> Optional[time]:
    if not value:
        return None
    for fmt in ("%H:%M", "%H:%M:%S", "%I:%M %p", "%I:%M%p"):
        try:
            return datetime.strptime(value.strip(), fmt).time()
        except (ValueError, AttributeError):
            continue
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL 1 — log_interaction
# ═══════════════════════════════════════════════════════════════════════════════

@tool
async def log_interaction(natural_language_input: str) -> str:
    """
    Log a new HCP interaction from a natural language description.
    Accepts descriptions like 'Met Dr. Sharma today, discussed Oncovax efficacy,
    she was positive, gave 3 samples'. Extracts structured data using LLM,
    generates an AI summary, and saves to the database.

    Args:
        natural_language_input: Free-form text describing the interaction.

    Returns:
        JSON string with the saved interaction object including generated ID.
    """
    today = date.today().isoformat()

    system_prompt = """You are an expert pharmaceutical CRM data extractor.
Extract structured interaction data from the user's natural language description and return ONLY valid JSON.
Today's date is """ + today + """.

Return JSON with these exact keys (use null for missing data):
{
  "hcp_name": "string",
  "interaction_type": "Meeting|Call|Email|Conference|Visit",
  "interaction_date": "YYYY-MM-DD or null",
  "interaction_time": "HH:MM or null",
  "attendees": ["list", "of", "names"],
  "topics_discussed": "string description",
  "materials_shared": ["list", "of", "materials"],
  "samples_distributed": ["list", "of", "samples"],
  "sentiment": "Positive|Neutral|Negative",
  "outcomes": "string description of outcomes",
  "follow_up_actions": "string description of follow-up actions",
  "ai_summary": "2-3 sentence professional summary of the interaction"
}"""

    raw = call_groq(natural_language_input, system=system_prompt, json_mode=True)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {}

    interaction_date = _parse_date(data.get("interaction_date"))
    interaction_time = _parse_time(data.get("interaction_time"))
    interaction_type = _safe_enum(data.get("interaction_type"), InteractionTypeEnum, InteractionTypeEnum.Meeting)
    sentiment = _safe_enum(data.get("sentiment"), SentimentEnum, SentimentEnum.Neutral)

    new_interaction = HCPInteraction(
        id=uuid.uuid4(),
        hcp_name=data.get("hcp_name") or "Unknown HCP",
        interaction_type=interaction_type,
        interaction_date=interaction_date or date.today(),
        interaction_time=interaction_time,
        attendees=data.get("attendees") or [],
        topics_discussed=data.get("topics_discussed") or "",
        materials_shared=data.get("materials_shared") or [],
        samples_distributed=data.get("samples_distributed") or [],
        sentiment=sentiment,
        outcomes=data.get("outcomes") or "",
        follow_up_actions=data.get("follow_up_actions") or "",
        ai_summary=data.get("ai_summary") or "",
    )

    async with AsyncSessionLocal() as session:
        session.add(new_interaction)

        # Upsert HCP record
        existing_hcp = await session.execute(
            select(HCP).where(HCP.name.ilike(new_interaction.hcp_name))
        )
        if not existing_hcp.scalars().first():
            session.add(HCP(id=uuid.uuid4(), name=new_interaction.hcp_name))

        await session.commit()
        await session.refresh(new_interaction)

    result = {
        "id": str(new_interaction.id),
        "hcp_name": new_interaction.hcp_name,
        "interaction_type": new_interaction.interaction_type.value,
        "interaction_date": str(new_interaction.interaction_date) if new_interaction.interaction_date else None,
        "interaction_time": str(new_interaction.interaction_time) if new_interaction.interaction_time else None,
        "attendees": new_interaction.attendees or [],
        "topics_discussed": new_interaction.topics_discussed,
        "materials_shared": new_interaction.materials_shared or [],
        "samples_distributed": new_interaction.samples_distributed or [],
        "sentiment": new_interaction.sentiment.value if new_interaction.sentiment else "Neutral",
        "outcomes": new_interaction.outcomes,
        "follow_up_actions": new_interaction.follow_up_actions,
        "ai_summary": new_interaction.ai_summary,
        "created_at": str(new_interaction.created_at),
        "tool_action": "log_interaction",
    }
    return json.dumps(result)


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL 2 — edit_interaction
# ═══════════════════════════════════════════════════════════════════════════════

@tool
async def edit_interaction(
    interaction_id: str,
    change_description: str,
    fallback_interaction_id: Optional[str] = None,
) -> str:
    """
    Edit an existing HCP interaction using a natural language change description.
    Example: 'change sentiment to negative and add follow-up meeting on Monday'.

    Args:
        interaction_id: UUID of the interaction to edit. Pass empty string if unknown.
        change_description: Natural language description of what to change.
        fallback_interaction_id: ID of the most recently logged interaction in this
            session — used automatically when interaction_id is not provided.

    Returns:
        JSON string with the updated interaction object.
    """
    # If no explicit ID given, fall back to the most recently logged one
    resolved_id = (interaction_id or "").strip() or (fallback_interaction_id or "").strip()
    if not resolved_id:
        return json.dumps({"error": "No interaction ID provided and no recent interaction found in session."})

    async with AsyncSessionLocal() as session:
        try:
            target_uuid = uuid.UUID(resolved_id)
        except ValueError:
            return json.dumps({"error": f"Invalid interaction ID format: {resolved_id}"})

        result = await session.execute(
            select(HCPInteraction).where(HCPInteraction.id == target_uuid)
        )
        interaction = result.scalars().first()

        if not interaction:
            return json.dumps({"error": f"Interaction {resolved_id} not found"})

        current_data = {
            "hcp_name": interaction.hcp_name,
            "interaction_type": interaction.interaction_type.value,
            "interaction_date": str(interaction.interaction_date) if interaction.interaction_date else None,
            "interaction_time": str(interaction.interaction_time) if interaction.interaction_time else None,
            "attendees": interaction.attendees or [],
            "topics_discussed": interaction.topics_discussed,
            "materials_shared": interaction.materials_shared or [],
            "samples_distributed": interaction.samples_distributed or [],
            "sentiment": interaction.sentiment.value if interaction.sentiment else "Neutral",
            "outcomes": interaction.outcomes,
            "follow_up_actions": interaction.follow_up_actions,
            "ai_summary": interaction.ai_summary,
        }

        system_prompt = """You are a CRM data editor. Given the CURRENT interaction data and a CHANGE DESCRIPTION,
return ONLY the fields that need to be updated as a JSON object. 
Only include fields that are actually being changed. Use the same field names as the current data.
Valid values: interaction_type: Meeting|Call|Email|Conference|Visit, sentiment: Positive|Neutral|Negative.
Dates: YYYY-MM-DD. Times: HH:MM."""

        prompt = f"""Current interaction data:
{json.dumps(current_data, indent=2)}

Change description: {change_description}

Return ONLY the fields to update as JSON:"""

        raw = call_groq(prompt, system=system_prompt, json_mode=True)

        try:
            updates = json.loads(raw)
        except json.JSONDecodeError:
            updates = {}

        # Apply updates
        if "hcp_name" in updates:
            interaction.hcp_name = updates["hcp_name"]
        if "interaction_type" in updates:
            interaction.interaction_type = _safe_enum(updates["interaction_type"], InteractionTypeEnum, interaction.interaction_type)
        if "interaction_date" in updates:
            parsed = _parse_date(updates["interaction_date"])
            if parsed:
                interaction.interaction_date = parsed
        if "interaction_time" in updates:
            parsed_t = _parse_time(updates["interaction_time"])
            if parsed_t:
                interaction.interaction_time = parsed_t
        if "attendees" in updates and isinstance(updates["attendees"], list):
            interaction.attendees = updates["attendees"]
        if "topics_discussed" in updates:
            interaction.topics_discussed = updates["topics_discussed"]
        if "materials_shared" in updates and isinstance(updates["materials_shared"], list):
            interaction.materials_shared = updates["materials_shared"]
        if "samples_distributed" in updates and isinstance(updates["samples_distributed"], list):
            interaction.samples_distributed = updates["samples_distributed"]
        if "sentiment" in updates:
            interaction.sentiment = _safe_enum(updates["sentiment"], SentimentEnum, interaction.sentiment)
        if "outcomes" in updates:
            interaction.outcomes = updates["outcomes"]
        if "follow_up_actions" in updates:
            interaction.follow_up_actions = updates["follow_up_actions"]
        if "ai_summary" in updates:
            interaction.ai_summary = updates["ai_summary"]

        await session.commit()
        await session.refresh(interaction)

    result_data = {
        "id": str(interaction.id),
        "hcp_name": interaction.hcp_name,
        "interaction_type": interaction.interaction_type.value,
        "interaction_date": str(interaction.interaction_date) if interaction.interaction_date else None,
        "interaction_time": str(interaction.interaction_time) if interaction.interaction_time else None,
        "attendees": interaction.attendees or [],
        "topics_discussed": interaction.topics_discussed,
        "materials_shared": interaction.materials_shared or [],
        "samples_distributed": interaction.samples_distributed or [],
        "sentiment": interaction.sentiment.value if interaction.sentiment else "Neutral",
        "outcomes": interaction.outcomes,
        "follow_up_actions": interaction.follow_up_actions,
        "ai_summary": interaction.ai_summary,
        "updated_at": str(interaction.updated_at),
        "tool_action": "edit_interaction",
        "changes_applied": list(updates.keys()),
    }
    return json.dumps(result_data)


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL 3 — get_hcp_history
# ═══════════════════════════════════════════════════════════════════════════════

@tool
async def get_hcp_history(hcp_name: str) -> str:
    """
    Retrieve the last 10 interactions with a specific HCP (supports fuzzy name matching).
    Returns interaction history, sentiment trend analysis, and an LLM-generated relationship summary.

    Args:
        hcp_name: Name (or partial name) of the Healthcare Professional.

    Returns:
        JSON string with interactions list, sentiment counts, and relationship summary.
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(HCPInteraction)
            .where(HCPInteraction.hcp_name.ilike(f"%{hcp_name}%"))
            .order_by(HCPInteraction.interaction_date.desc().nullslast(), HCPInteraction.created_at.desc())
            .limit(10)
        )
        interactions = result.scalars().all()

    if not interactions:
        return json.dumps({
            "hcp_name": hcp_name,
            "interactions": [],
            "sentiment_trend": {"Positive": 0, "Neutral": 0, "Negative": 0},
            "relationship_summary": f"No interactions found for HCP matching '{hcp_name}'.",
            "tool_action": "get_hcp_history",
        })

    interaction_list = []
    sentiment_counts = {"Positive": 0, "Neutral": 0, "Negative": 0}

    for i in interactions:
        sentiment_val = i.sentiment.value if i.sentiment else "Neutral"
        sentiment_counts[sentiment_val] = sentiment_counts.get(sentiment_val, 0) + 1
        interaction_list.append({
            "id": str(i.id),
            "interaction_type": i.interaction_type.value,
            "interaction_date": str(i.interaction_date) if i.interaction_date else None,
            "topics_discussed": i.topics_discussed,
            "sentiment": sentiment_val,
            "outcomes": i.outcomes,
            "ai_summary": i.ai_summary,
        })

    # Generate relationship summary
    summary_prompt = f"""Based on the following {len(interactions)} interactions with {hcp_name}, 
write a concise 2-3 sentence relationship summary for a pharmaceutical sales rep:

Interactions:
{json.dumps(interaction_list, indent=2)}

Sentiment distribution: {sentiment_counts}

Focus on: overall relationship quality, key topics, and engagement level."""

    relationship_summary = call_groq(
        summary_prompt,
        system="You are a pharmaceutical CRM analyst. Write concise, professional relationship summaries.",
    )

    return json.dumps({
        "hcp_name": hcp_name,
        "interactions": interaction_list,
        "total_interactions": len(interaction_list),
        "sentiment_trend": sentiment_counts,
        "relationship_summary": relationship_summary.strip(),
        "tool_action": "get_hcp_history",
    })


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL 4 — suggest_followup
# ═══════════════════════════════════════════════════════════════════════════════

@tool
async def suggest_followup(interaction_id: str) -> str:
    """
    Generate 3-5 specific, actionable follow-up items for an HCP interaction.
    Based on topics discussed, sentiment, and outcomes from the interaction record.

    Args:
        interaction_id: UUID of the interaction to generate follow-ups for.

    Returns:
        JSON string with an array of follow-up action strings.
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(HCPInteraction).where(HCPInteraction.id == uuid.UUID(interaction_id))
        )
        interaction = result.scalars().first()

    if not interaction:
        return json.dumps({
            "error": f"Interaction {interaction_id} not found",
            "follow_ups": [],
            "tool_action": "suggest_followup",
        })

    prompt = f"""Generate 3-5 specific, actionable follow-up actions for a pharmaceutical sales rep 
after this HCP interaction. Each follow-up should be concrete and time-bound where possible.

HCP: {interaction.hcp_name}
Type: {interaction.interaction_type.value}
Date: {interaction.interaction_date}
Topics Discussed: {interaction.topics_discussed}
Sentiment: {interaction.sentiment.value if interaction.sentiment else 'Neutral'}
Outcomes: {interaction.outcomes}
Current Follow-up Notes: {interaction.follow_up_actions}

Return ONLY a JSON object with this structure:
{{
  "follow_ups": [
    "Follow-up action 1",
    "Follow-up action 2",
    "Follow-up action 3"
  ]
}}"""

    raw = call_groq(
        prompt,
        system="You are a pharmaceutical sales strategy expert. Generate specific, actionable follow-up actions. Return valid JSON only.",
        json_mode=True,
    )

    try:
        data = json.loads(raw)
        follow_ups = data.get("follow_ups", [])
        if not isinstance(follow_ups, list):
            follow_ups = []
    except (json.JSONDecodeError, AttributeError):
        follow_ups = [
            f"Schedule a follow-up meeting with {interaction.hcp_name} within 2 weeks",
            "Send a summary email with discussed materials",
            "Update CRM with any new product preferences noted",
        ]

    return json.dumps({
        "interaction_id": interaction_id,
        "hcp_name": interaction.hcp_name,
        "follow_ups": follow_ups,
        "tool_action": "suggest_followup",
    })


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL 5 — analyze_sentiment
# ═══════════════════════════════════════════════════════════════════════════════

@tool
async def analyze_sentiment(text: str) -> str:
    """
    Analyze the sentiment of free-form text (topics discussed, outcomes, or any notes).
    Classifies as Positive, Neutral, or Negative with confidence score and reasoning.

    Args:
        text: Free-form text to analyze for sentiment.

    Returns:
        JSON string with sentiment label, confidence score (0-1), and reasoning.
    """
    prompt = f"""Analyze the sentiment of the following pharmaceutical sales interaction text.

Text: {text}

Return ONLY a JSON object with exactly these fields:
{{
  "sentiment": "Positive|Neutral|Negative",
  "confidence": 0.85,
  "reasoning": "Brief explanation of why this sentiment was chosen"
}}

Consider:
- HCP engagement level and enthusiasm
- Receptiveness to products/information
- Tone of conversation
- Outcomes and agreements reached"""

    raw = call_groq(
        prompt,
        system="You are a sentiment analysis expert for pharmaceutical sales interactions. Return valid JSON only.",
        json_mode=True,
    )

    try:
        data = json.loads(raw)
        sentiment_str = data.get("sentiment", "Neutral")
        # Normalize
        if sentiment_str.lower() in ["positive"]:
            sentiment_str = "Positive"
        elif sentiment_str.lower() in ["negative"]:
            sentiment_str = "Negative"
        else:
            sentiment_str = "Neutral"

        confidence = float(data.get("confidence", 0.7))
        confidence = max(0.0, min(1.0, confidence))
        reasoning = data.get("reasoning", "Sentiment analyzed based on text content.")
    except (json.JSONDecodeError, ValueError, TypeError):
        sentiment_str = "Neutral"
        confidence = 0.5
        reasoning = "Unable to determine sentiment with high confidence."

    return json.dumps({
        "sentiment": sentiment_str,
        "confidence": confidence,
        "reasoning": reasoning,
        "tool_action": "analyze_sentiment",
    })


# Export all tools for the agent graph
ALL_TOOLS = [
    log_interaction,
    edit_interaction,
    get_hcp_history,
    suggest_followup,
    analyze_sentiment,
]
