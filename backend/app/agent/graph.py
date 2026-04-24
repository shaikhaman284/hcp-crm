"""
LangGraph StateGraph agent orchestration.
Flow: START → agent_node → (tool_node if tools called, else END)
      tool_node → agent_node (loop until no more tool calls)
"""

import os
import logging
from typing import Annotated, Optional, Sequence, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from app.agent.tools import ALL_TOOLS

load_dotenv()
logger = logging.getLogger(__name__)

PRIMARY_MODEL = os.getenv("PRIMARY_MODEL", "llama-3.3-70b-versatile")
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "llama-3.3-70b-versatile")

SYSTEM_PROMPT = """You are an AI assistant for a pharmaceutical CRM system specializing in Healthcare Professional (HCP) relationship management.

You have access to these tools:
1. log_interaction — Log a new HCP interaction from natural language
2. edit_interaction — Edit an existing interaction by ID with natural language changes
3. get_hcp_history — Retrieve interaction history for an HCP (supports fuzzy name matching)
4. suggest_followup — Generate follow-up action items for an interaction
5. analyze_sentiment — Analyze sentiment of any text

Guidelines:
- When a user describes a meeting, call, or other interaction with a doctor/HCP → use log_interaction
- When a user wants to change something about an existing interaction → use edit_interaction
- When a user asks about history with an HCP → use get_hcp_history
- When a user asks for follow-up suggestions → use suggest_followup
- When a user wants sentiment analysis → use analyze_sentiment
- Always be professional, concise, and pharmaceutical-industry focused
- After logging an interaction, mention the generated ID and offer to suggest follow-ups
- Format responses clearly with relevant details highlighted
- IMPORTANT: When calling edit_interaction and the user has NOT provided an explicit interaction ID,
  pass interaction_id="" and set fallback_interaction_id to the last_interaction_id shown in context."""


# ─── State ────────────────────────────────────────────────────────────────────

def _overwrite(old, new):
    """Reducer that always replaces the old value with the new one."""
    return new

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    last_interaction_id: Annotated[Optional[str], _overwrite]


# ─── LLM Setup ────────────────────────────────────────────────────────────────

def _get_llm_with_tools(model_name: str):
    """Create a ChatGroq instance bound to all tools."""
    llm = ChatGroq(
        model=model_name,
        temperature=0.2,
        max_tokens=2048,
        groq_api_key=os.getenv("GROQ_API_KEY", ""),
    )
    return llm.bind_tools(ALL_TOOLS)


def _get_llm():
    """Get LLM with fallback."""
    try:
        return _get_llm_with_tools(PRIMARY_MODEL)
    except Exception:
        return _get_llm_with_tools(FALLBACK_MODEL)


# ─── Nodes ────────────────────────────────────────────────────────────────────

async def agent_node(state: AgentState) -> AgentState:
    """Main agent reasoning node — calls LLM with tool bindings."""
    messages = list(state["messages"])
    last_id = state.get("last_interaction_id")

    # Build context-aware system prompt that includes last_interaction_id
    context_note = (
        f"\n\nSession context — last logged interaction ID: {last_id}"
        if last_id
        else ""
    )
    system_content = SYSTEM_PROMPT + context_note

    # Inject system prompt if not present
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SystemMessage(content=system_content)] + messages
    else:
        # Replace existing system message with updated context
        messages = [
            SystemMessage(content=system_content) if isinstance(m, SystemMessage) else m
            for m in messages
        ]

    llm = _get_llm()
    try:
        response = await llm.ainvoke(messages)
    except Exception as e:
        logger.error(f"Agent node LLM call failed: {e}")
        response = AIMessage(content="I'm sorry, I encountered an error. Please try again.")

    return {"messages": [response], "last_interaction_id": last_id}


def should_continue(state: AgentState) -> str:
    """Router: if last message has tool calls → go to tools, else END."""
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END


# ─── Graph Construction ───────────────────────────────────────────────────────

tool_node = ToolNode(ALL_TOOLS)

workflow = StateGraph(AgentState)
workflow.add_node("agent", agent_node)
workflow.add_node("tools", tool_node)

workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
workflow.add_edge("tools", "agent")

graph = workflow.compile()


# ─── Public API ───────────────────────────────────────────────────────────────

# In-memory session store: session_id → {messages, last_interaction_id}
_sessions: dict[str, dict] = {}


async def run_agent(message: str, session_id: str) -> dict:
    """
    Run the LangGraph agent with a user message.
    Maintains per-session conversation history and last_interaction_id.

    Returns:
        dict with 'reply', 'session_id', 'tool_used',
        'extracted_interaction' (log), and 'interaction_data' (edit)
    """
    if session_id not in _sessions:
        _sessions[session_id] = {"messages": [], "last_interaction_id": None}

    session = _sessions[session_id]
    session["messages"].append(HumanMessage(content=message))

    state = {
        "messages": session["messages"],
        "last_interaction_id": session["last_interaction_id"],
    }

    try:
        result = await graph.ainvoke(state)
    except Exception as e:
        logger.error(f"Graph invocation error: {e}")
        return {
            "reply": "I encountered an error processing your request. Please try again.",
            "session_id": session_id,
            "tool_used": None,
            "extracted_interaction": None,
            "interaction_data": None,
        }

    all_messages = result.get("messages", [])
    session["messages"] = [m for m in all_messages if not isinstance(m, SystemMessage)]

    # Find the final AI response
    reply = "I processed your request."
    tool_used = None
    extracted_interaction = None   # for log_interaction
    interaction_data = None        # for edit_interaction

    import json
    from langchain_core.messages import ToolMessage

    for msg in reversed(all_messages):
        if isinstance(msg, AIMessage) and msg.content:
            reply = msg.content
            break

    # Scan ALL ToolMessages to capture both log and edit results
    for msg in reversed(all_messages):
        if isinstance(msg, ToolMessage):
            try:
                tool_data = json.loads(msg.content)
                action = tool_data.get("tool_action")
                if action == "log_interaction" and tool_used is None:
                    tool_used = action
                    extracted_interaction = tool_data
                    # Persist the new interaction ID for this session
                    new_id = tool_data.get("id")
                    if new_id:
                        session["last_interaction_id"] = new_id
                elif action == "edit_interaction" and tool_used is None:
                    tool_used = action
                    interaction_data = tool_data
            except (json.JSONDecodeError, TypeError):
                pass

    return {
        "reply": reply,
        "session_id": session_id,
        "tool_used": tool_used,
        "extracted_interaction": extracted_interaction,
        "interaction_data": interaction_data,
    }


def get_session_history(session_id: str) -> list[dict]:
    """Get formatted chat history for a session."""
    messages = _sessions.get(session_id, {}).get("messages", [])
    result = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            result.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage) and msg.content:
            result.append({"role": "assistant", "content": msg.content})
    return result
