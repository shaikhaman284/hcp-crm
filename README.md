# HCP CRM — AI-First Healthcare Professional Manager

A production-ready, full-stack CRM module for pharmaceutical sales teams to log, analyze, and manage HCP (Healthcare Professional) interactions — powered by LangGraph agents, Groq LLMs, FastAPI, PostgreSQL, and React.

---

## Tech Stack

```
┌─────────────────────────────────────────────────────────┐
│                      FRONTEND                           │
│  React 18 · Vite · Redux Toolkit · Axios               │
│  Dark Clinical UI · Inter Font · Custom CSS            │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTP / REST
┌───────────────────────▼─────────────────────────────────┐
│                      BACKEND                            │
│  FastAPI · Uvicorn · Python 3.11+                      │
│  SQLAlchemy (async) · Alembic · asyncpg                │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │           LangGraph Agent                        │   │
│  │  START → agent_node → tool_node → agent_node    │   │
│  │                                                  │   │
│  │  Tools:  log_interaction   edit_interaction      │   │
│  │          get_hcp_history   suggest_followup      │   │
│  │          analyze_sentiment                       │   │
│  └──────────────────┬──────────────────────────────┘   │
│                     │                                   │
│            Groq LLM (gemma2-9b-it /                    │
│                      llama-3.3-70b-versatile)           │
└───────────────────────┬─────────────────────────────────┘
                        │ asyncpg
┌───────────────────────▼─────────────────────────────────┐
│                   PostgreSQL                            │
│  Tables: hcps · hcp_interactions                       │
└─────────────────────────────────────────────────────────┘
```

---

## Prerequisites

- **Node.js** 18+
- **Python** 3.11+
- **PostgreSQL** 14+ (running locally or remote)
- **Groq API Key** — get free at https://console.groq.com

---

## Setup Instructions

### 1. Clone the repository

```bash
git clone <repo-url>
cd hcp-crm
```

---

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate
# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
```

**Edit `backend/.env` and fill in:**

```env
GROQ_API_KEY=your_groq_api_key_here        # ← Get from https://console.groq.com
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/hcp_crm
PRIMARY_MODEL=gemma2-9b-it
FALLBACK_MODEL=llama-3.3-70b-versatile
```

**Create the PostgreSQL database:**

```sql
-- In psql or pgAdmin:
CREATE DATABASE hcp_crm;
```

**Run database migrations:**

```bash
alembic upgrade head
```

**Start the backend server:**

```bash
uvicorn main:app --reload
# API running at: http://localhost:8000
# Docs at:        http://localhost:8000/docs
```

---

### 3. Frontend Setup

```bash
cd ../frontend

# Install dependencies
npm install

# Copy environment file
cp .env.example .env
# Default: VITE_API_BASE_URL=http://localhost:8000 (no changes needed)

# Start dev server
npm run dev
# App running at: http://localhost:5173
```

---

## LangGraph Agent Architecture

The agent uses a **StateGraph** with a cyclic `agent → tools → agent` loop:

```
START
  │
  ▼
agent_node   ←──────────────────┐
  │                             │
  ├── has tool_calls? → YES → tool_node
  │                             │
  └── no tool_calls? → END ─────┘
```

- **agent_node**: Calls `ChatGroq` (gemma2-9b-it primary, llama-3.3-70b-versatile fallback) bound to all 5 tools. Decides which tool to call based on user input.
- **tool_node**: Executes the chosen tool(s) via `ToolNode`. Results are fed back to the agent.
- **Session memory**: Each `session_id` maintains its own conversation history in-memory.

---

## All 5 Tools

### Tool 1 — `log_interaction`
Accepts natural language and saves a structured interaction to the DB.

**Example input:**
```
"Met Dr. Sharma today at City Hospital, discussed Oncovax efficacy for stage-3 patients,
 she was very positive, gave 3 samples and shared the clinical study brochure"
```
**Returns:** Full interaction object with generated UUID, AI summary, extracted fields.

---

### Tool 2 — `edit_interaction`
Edits an existing interaction from natural language change description.

**Example input:**
```json
{ "interaction_id": "uuid-here", "change_description": "change sentiment to negative and add follow-up call next Monday" }
```
**Returns:** Updated interaction object with list of applied changes.

---

### Tool 3 — `get_hcp_history`
Fetches last 10 interactions with an HCP (fuzzy name match) + sentiment trend + LLM summary.

**Example input:** `"Dr. Sharma"`  
**Returns:** Interaction list, `{"Positive": 3, "Neutral": 1, "Negative": 0}`, relationship summary paragraph.

---

### Tool 4 — `suggest_followup`
Generates 3-5 specific, actionable follow-up items for an interaction.

**Example input:** `"uuid-of-interaction"`  
**Returns:**
```json
["Schedule clinical efficacy demo within 2 weeks",
 "Email the Phase-3 trial data summary",
 "Follow up on sample feedback after 10 days"]
```

---

### Tool 5 — `analyze_sentiment`
Classifies any text as Positive/Neutral/Negative with confidence + reasoning.

**Example input:** `"Doctor was very engaged, asked detailed questions about dosing, requested more samples"`  
**Returns:** `{ "sentiment": "Positive", "confidence": 0.92, "reasoning": "..." }`

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/interactions` | Log new interaction |
| `GET` | `/api/interactions` | List all interactions (filter by hcp_name, sentiment) |
| `GET` | `/api/interactions/{id}` | Get single interaction |
| `PUT` | `/api/interactions/{id}` | Update interaction |
| `DELETE` | `/api/interactions/{id}` | Delete interaction |
| `GET` | `/api/hcps` | List HCPs (search param supported) |
| `POST` | `/api/hcps` | Create new HCP |
| `POST` | `/api/agent/chat` | Chat with LangGraph agent |
| `GET` | `/api/agent/history/{session_id}` | Get session chat history |
| `POST` | `/api/agent/suggest-followup/{id}` | Get AI follow-up suggestions |

Interactive API docs: **http://localhost:8000/docs**

---

## What the User Must Do

1. Fill `GROQ_API_KEY` in `backend/.env`
2. Fill `DATABASE_URL` in `backend/.env` with PostgreSQL credentials
3. Run `alembic upgrade head` (one-time)
4. Run `pip install -r requirements.txt` + `npm install`

Everything else is automated.
