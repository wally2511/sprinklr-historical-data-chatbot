# Sprinklr Historical Data Chatbot

A RAG-powered chatbot that allows community managers and product teams to query historical social media engagement data from Sprinklr using natural language.

## Current Status

**Multi-Agent Architecture with Hybrid Ingestion:**
- Connected to Sprinklr API with 473,602+ cases accessible
- **Hybrid ingestion**: API for case metadata + SQLite for messages (bypasses rate limits)
- Uses v2 Search API with cursor-based pagination (newest cases first)
- Chatbot running at http://localhost:8508
- Brands available: Brand1, Brand2, Radio Christian Voice, Sharek Online
- Multi-agent system handles specific case lookups, broad searches, filtered queries, and aggregations
- Supports both OpenAI and Anthropic for summary generation during ingestion
- SQLite message database: 314K+ messages from 149K+ cases

## Features

- **Natural Language Queries**: Ask questions about your engagement data in plain English
- **Multi-Agent Architecture**: Intelligent query routing for optimal search strategies
- **Specific Case Lookup**: Query individual cases by number (e.g., "What happened in case #478117?")
- **Aggregation Queries**: Get statistics and distributions (e.g., "What are the most common themes?")
- **Semantic Search**: Find relevant conversations using AI-powered vector search
- **Filtered Search**: Combine theme, brand, and date filters
- **Theme Extraction**: Automatic categorization of conversations into 16 faith-based themes
- **Case Summaries**: AI-generated summaries for better pattern recognition
- **Date Range Filtering**: Analyze specific time periods
- **Brand Filtering**: Filter results by specific brands
- **Live Sprinklr Integration**: Full API integration with v2 Case Search, cursor pagination, and bulk message retrieval
- **Hybrid Ingestion**: API for case metadata + SQLite for message content (99%+ faster than API-only)
- **Dual LLM Support**: Anthropic Claude for chat responses, configurable OpenAI or Anthropic for ingestion summaries

## Architecture

```
User Interface (Streamlit)
    │
    ▼
┌─────────────────────────────────────────┐
│           Chatbot Engine                │
│  ┌─────────────────────────────────┐    │
│  │        Query Agent              │    │
│  │  - Analyze query type           │    │
│  │  - Extract filters (date/theme) │    │
│  │  - Generate search plan         │    │
│  └──────────────┬──────────────────┘    │
│                 │ QueryPlan              │
│                 ▼                        │
│  ┌─────────────────────────────────┐    │
│  │        Orchestrator             │    │
│  │  - Execute search strategy      │    │
│  │  - Route to appropriate method  │    │
│  └──────────────┬──────────────────┘    │
│                 │                        │
│    ┌────────────┼────────────┐          │
│    ▼            ▼            ▼          │
│ Specific    Semantic    Aggregation     │
│ Lookup      Search      (count_by_*)    │
│    │            │            │          │
│    └────────────┼────────────┘          │
│                 ▼                        │
│  ┌─────────────────────────────────┐    │
│  │       Response Agent            │    │
│  │  - Context-aware responses      │    │
│  │  - Adapts to query type         │    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
    │
    ▼
Vector Database (ChromaDB)
    │
    ▼
Data Ingestion (Sprinklr API + Theme Extraction)
```

## Query Types

| Type | Example | Behavior |
|------|---------|----------|
| **Specific Case** | "What happened in case #478117?" | Direct lookup, full conversation details |
| **Aggregation** | "What are the most common themes?" | Statistical summary with percentages |
| **Filtered Search** | "Show me anxiety cases from Brand1" | Semantic search with filters applied |
| **Broad Search** | "What questions do users ask about prayer?" | Synthesizes across many cases |

## Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys
# At minimum, set ANTHROPIC_API_KEY
```

### 3. Ingest Data

```bash
# With mock data (default)
python scripts/ingest_data.py

# RECOMMENDED: Hybrid ingestion (API cases + SQLite messages)
# Step 1: Convert Sprinklr XLSX exports to SQLite (one-time)
python scripts/xlsx_to_sqlite.py

# Step 2: Run hybrid ingestion (fast - no message API rate limits)
python scripts/ingest_data.py --live --xlsx-messages --max-cases 10000 --days 365

# API-only mode (slower - subject to rate limits)
python scripts/ingest_data.py --live --days 30 --max-cases 500
```

### 4. Run the Chatbot

```bash
streamlit run src/app.py
```

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Claude API key from console.anthropic.com |
| `USE_MOCK_DATA` | No | Set to `false` to use live Sprinklr API (default: `true`) |
| `SPRINKLR_API_KEY` | For live data | Sprinklr API key from dev.sprinklr.com |
| `SPRINKLR_API_SECRET` | For live data | Sprinklr API secret |
| `SPRINKLR_ENVIRONMENT` | For live data | Sprinklr environment (prod2, prod3, etc.) |
| `SPRINKLR_ACCESS_TOKEN` | For live data | OAuth access token |
| `OPENAI_API_KEY` | Optional | OpenAI API key (for GPT-4o provider) |
| `LLM_PROVIDER` | No | LLM provider: `anthropic` (default) or `openai` |
| `USE_MULTI_AGENT` | No | Enable multi-agent mode (default: `true`) |

### Multi-Agent Configuration

The multi-agent system can be configured via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_MULTI_AGENT` | `true` | Enable/disable multi-agent architecture |
| `MAX_CONTEXT_CASES_BROAD` | `50` | Max cases for broad/aggregation queries |
| `MAX_CONTEXT_CASES_SPECIFIC` | `10` | Max cases for specific lookups |
| `THEME_EXTRACTION_METHOD` | `keyword` | Theme extraction method (`keyword` or `llm`) |

### Sprinklr API Setup

1. Register at https://dev.sprinklr.com/
2. Create a new application
3. Note your API Key and generate an API Secret
4. Complete OAuth authorization to get access tokens
5. Ensure your account has permissions to view cases and messages

## Example Queries

**Specific Case Lookup:**
- "What happened in case #478117?"
- "Show me the details of case #475141"

**Aggregation Queries:**
- "What are the most common themes?"
- "How many cases per brand?"
- "What's the distribution of topics in our conversations?"

**Filtered Search:**
- "Show me anxiety cases from Brand1"
- "What prayer requests did we get last week?"
- "Find grief-related conversations from Radio Christian Voice"

**Broad Analysis:**
- "What questions do people ask about faith?"
- "Summarize the types of conversations we had this month"
- "What are the common concerns users bring up?"

## Project Structure

```
sprinklr-chatbot/
├── src/
│   ├── __init__.py
│   ├── config.py           # Configuration management
│   ├── sprinklr_client.py  # Sprinklr API wrapper (v1 + v2 search, message retrieval)
│   ├── xlsx_parser.py      # Parse Sprinklr XLSX message exports
│   ├── mock_data.py        # Sample data for testing
│   ├── ingestion.py        # Data ingestion pipeline with hybrid mode
│   ├── vector_store.py     # ChromaDB operations + aggregations
│   ├── chatbot.py          # RAG chatbot with multi-agent support
│   ├── app.py              # Streamlit interface
│   ├── agents/             # Multi-agent system
│   │   ├── __init__.py
│   │   ├── query_agent.py      # Query analysis and plan generation
│   │   ├── response_agent.py   # Context-aware response generation
│   │   └── orchestrator.py     # Agent coordination
│   └── services/           # Shared services
│       ├── __init__.py
│       ├── theme_extractor.py  # Keyword-based theme extraction
│       └── message_store.py    # SQLite message lookups
├── scripts/
│   ├── ingest_data.py      # CLI for data ingestion (supports hybrid mode)
│   ├── xlsx_to_sqlite.py   # Convert XLSX exports to SQLite database
│   ├── resume_ingestion.py # Wait for rate limit reset and resume
│   ├── test_api.py         # Test API connectivity
│   └── test_chatbot.py     # Test chatbot with current data
├── data/
│   ├── chroma_db/          # Local vector database
│   └── messages.db         # SQLite message database (from XLSX)
├── docs/
│   └── SPRINKLR_API_REFERENCE.md  # API documentation
├── .env.example
├── requirements.txt
└── README.md
```

## Sprinklr API Endpoints

The client implements the following Sprinklr API endpoints:

### Case Search (v2) - Primary
```
POST https://api3.sprinklr.com/{env}/api/v2/search/CASE
```
- Filter-based queries with `createdTime` sorting (newest first)
- Cursor-based pagination (cursor expires after 5 minutes)
- Returns cases sorted by creation date descending

### Case Search (v1) - Legacy
```
POST https://api3.sprinklr.com/{env}/api/v1/case/search
```
- Offset-based pagination with `start` and `rows`
- Date filtering with `sinceDate`/`untilDate` (milliseconds)

### Message Retrieval (Bulk)
```
GET /api/v2/case/associated-messages?id={case_id}  # Get message IDs
POST /api/v2/message/bulk-fetch                     # Fetch messages in bulk
```
The bulk fetch API retrieves all messages in a single call, reducing API usage from N+1 calls to just 2 calls per case.

## Development

### Mock Data Mode

The chatbot includes realistic sample conversations for testing without Sprinklr access. This is useful for:
- Initial development and testing
- Demos and stakeholder presentations
- Validating the RAG architecture

### Hybrid Ingestion Mode (Recommended)

Hybrid ingestion bypasses the rate-limited message API by loading message content from pre-exported XLSX files converted to SQLite:

```bash
# Step 1: Export messages from Sprinklr UI as XLSX files to data_import/
# Step 2: Convert to SQLite (one-time, ~5 minutes for 300K+ messages)
python scripts/xlsx_to_sqlite.py

# Step 3: Run hybrid ingestion
python scripts/ingest_data.py --live --xlsx-messages --max-cases 10000 --days 365
```

**Performance comparison:**
| Mode | 10,000 cases | Rate limit impact |
|------|--------------|-------------------|
| API-only | ~10+ hours | Heavy (message bulk fetch) |
| Hybrid | ~30 minutes | Minimal (case search only) |

### Rate Limits

When using live Sprinklr data, be aware of rate limits:
- **Hourly limit:** ~1000 API calls per hour (API returns 403 "Developer Over Rate")
- **Per-second limit:** 10 API calls per second

The client includes:
- Automatic rate limiting to stay within these bounds
- Auto-retry on 403/429 errors with 5-minute waits (up to 3 retries)
- Unified error handling for all API endpoints

**API calls per case (API-only mode):**
- 1 search call to find cases (paginated)
- 1 call to get message IDs for a case
- 1 bulk fetch call to get all messages (regardless of count)

**API calls per case (Hybrid mode):**
- 1 search call to find cases (paginated)
- 0 message API calls (loaded from SQLite)

For large ingestion batches, use the resume script to wait for rate limit reset:

```bash
# Check if rate limit has reset
python scripts/resume_ingestion.py --check-only

# Wait for reset and resume ingestion
python scripts/resume_ingestion.py --max-cases 100 --days 90

# Just try once without waiting
python scripts/resume_ingestion.py --no-wait --max-cases 50
```

## Privacy Considerations

- Conversation data may contain sensitive information
- The local ChromaDB database stores case data on disk
- Ensure appropriate access controls for the data directory
- Consider data retention policies for your organization
