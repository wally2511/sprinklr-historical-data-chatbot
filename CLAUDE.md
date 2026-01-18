# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RAG chatbot that enables natural language queries against Sprinklr historical engagement data. Uses ChromaDB for vector storage with sentence-transformers embeddings, and Claude for response generation.

## Current State & Implemented Features

**Status**: Multi-agent architecture with compound search implemented

### Implemented Features
- **Multi-Agent Architecture**: Query Agent, Response Agent, and Orchestrator for intelligent query processing
- **Compound Search**: Multi-step search strategies for complex queries (e.g., "What are the main themes and show me examples?")
- **Specific Case Lookup**: Query specific cases like "case #54123"
- **Dynamic Context Size**: Adjusts results based on query type (1 for specific, 10 for filtered, 100 for broad)
- **Aggregations**: Statistical queries like "most common questions in last 30 days"

### Multi-Agent Architecture
```
User Query → Query Agent (analyze, plan) → Orchestrator → Response Agent
                                              ↓
                              [Specific Lookup | Semantic Search | Aggregation]
                                              ↓
                              Compound queries execute multiple steps
```

### Compound Search Strategies
For complex queries, the system automatically detects and executes multi-step searches:
- **Hierarchical**: Overview first, then drill into details (e.g., "themes and examples")
- **Comparative**: Side-by-side analysis (e.g., "compare Brand1 and Brand2")
- **Timeline**: Changes over time (e.g., "what changed between last month and this month")

### Remaining Known Issues
1. **Themes empty for live data**: `src/ingestion.py:270` hardcodes `"theme": ""` - needs theme extraction

### Agent Files
- `src/agents/query_agent.py` - Query analysis, compound detection, and planning
- `src/agents/response_agent.py` - Context-aware response generation with compound synthesis
- `src/agents/orchestrator.py` - Agent coordination and multi-step execution

## Commands

### Setup
```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
cp .env.example .env           # Then edit with API keys
```

### Run Application
```bash
streamlit run src/app.py
# OR
python run.py
```

### Data Ingestion (required before first use)
```bash
# Mock data (default)
python scripts/ingest_data.py

# With parameters
python scripts/ingest_data.py --cases 100 --days 60

# Live Sprinklr data
python scripts/ingest_data.py --live --days 30 --max-cases 500

# Append mode (don't clear existing)
python scripts/ingest_data.py --no-clear

# Check data stats
python scripts/ingest_data.py --stats
```

### Testing/Debugging
```bash
python scripts/test_api.py          # Verify Sprinklr API
python scripts/test_chatbot.py      # Test chatbot with stored data
python scripts/inspect_data.py      # Inspect ChromaDB contents
python scripts/debug_messages.py    # Debug message retrieval
```

## Architecture

```
Streamlit UI (app.py)
    ↓
Chatbot Engine (chatbot.py) - RAG pipeline with Claude
    ├─ Query → Semantic search → Context building → LLM response
    └─ Maintains 20-message conversation history
    ↓
Vector Store (vector_store.py) - ChromaDB wrapper
    ├─ Stores: embeddings, summaries, full conversations, metadata
    ├─ Search with filters: date range, theme, brands
    └─ Persistent storage at data/chroma_db/
    ↓
Data Sources
    ├─ SprinklrClient (sprinklr_client.py) - API with rate limiting
    └─ Mock Data Generator (mock_data.py) - Testing data
```

### Key Data Flow

1. **Ingestion** (`ingestion.py`): Fetch cases → Get messages → Generate AI summary → Batch store in ChromaDB
2. **Query** (`chatbot.py`): User query → Vector search (top 10) → Build context → Claude response → Return with sources

### Configuration (`config.py`)

- `USE_MOCK_DATA`: Toggle between mock and live Sprinklr data
- `USE_MULTI_AGENT`: Enable multi-agent architecture (default: true)
- `ENABLE_COMPOUND_SEARCH`: Enable compound multi-step search strategies (default: true)
- `MAX_COMPOUND_STEPS`: Maximum steps in compound search (default: 4)
- `MAX_TOTAL_CASES_COMPOUND`: Maximum total cases in compound results (default: 50)
- Rate limits: 1000 calls/hour, 10 calls/second (enforced by `RateLimiter` class)
- Models: `claude-sonnet-4-20250514` for chat, `all-MiniLM-L6-v2` for embeddings

## Key Implementation Details

### Sprinklr API Endpoints
- Case search: `POST /api/v1/case/search` (paginated)
- Message IDs: `GET /api/v2/case/associated-messages?id={case_id}`
- Bulk messages: `POST /api/v2/message/bulk-fetch`

### Rate Limiting
Sprinklr enforces hourly limits. Use `scripts/resume_ingestion.py` to continue after 403 "Developer Over Rate" errors.

### Vector Store Metadata
ChromaDB stores: `case_number`, `brand`, `channel`, `theme`, `outcome`, `sentiment`, `language`, `country`, `created_at`, `full_conversation` (truncated to 5000 chars), `description`, `subject`

### Session State (Streamlit)
- `st.session_state.messages`: Chat history
- `st.session_state.chatbot`: Singleton chatbot instance
