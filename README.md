# Sprinklr Historical Data Chatbot

A RAG-powered chatbot that allows community managers and product teams to query historical social media engagement data from Sprinklr using natural language.

## Current Status

**Live Data Integration Complete:**
- Connected to Sprinklr API with 473,602+ cases accessible
- 100 cases ingested with full conversation transcripts
- Chatbot running at http://localhost:8502
- Brands available: Brand1, Radio Christian Voice, Sharek Online
- Date range: August 2025 to January 2026
- Rate limit recovery script available for resuming ingestion

## Features

- **Natural Language Queries**: Ask questions about your engagement data in plain English
- **Semantic Search**: Find relevant conversations using AI-powered vector search
- **Case Summaries**: AI-generated summaries for better pattern recognition
- **Date Range Filtering**: Analyze specific time periods
- **Brand Filtering**: Filter results by specific brands
- **Live Sprinklr Integration**: Full API integration with v1 Case Search and message retrieval
- **Mock Data Mode**: Test the chatbot without Sprinklr API access

## Architecture

```
User Interface (Streamlit)
    │
    ▼
Chatbot Engine (Claude LLM + RAG)
    │
    ▼
Vector Database (ChromaDB)
    │
    ▼
Data Ingestion (Sprinklr API or Mock Data)
```

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

# With live Sprinklr data (requires API credentials)
python scripts/ingest_data.py --live --days 30
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

### Sprinklr API Setup

1. Register at https://dev.sprinklr.com/
2. Create a new application
3. Note your API Key and generate an API Secret
4. Complete OAuth authorization to get access tokens
5. Ensure your account has permissions to view cases and messages

## Example Queries

- "What were the most common questions about faith sharing last week?"
- "Summarize the types of conversations we had this month"
- "What questions do people ask about prayer?"
- "How many conversations involved doubt or questioning?"
- "What were the main topics discussed in October?"

## Project Structure

```
sprinklr-chatbot/
├── src/
│   ├── __init__.py
│   ├── config.py           # Configuration management
│   ├── sprinklr_client.py  # Sprinklr API wrapper (v1 + v2 search, message retrieval)
│   ├── mock_data.py        # Sample data for testing
│   ├── ingestion.py        # Data ingestion pipeline
│   ├── vector_store.py     # ChromaDB operations
│   ├── chatbot.py          # RAG chatbot logic
│   └── app.py              # Streamlit interface
├── scripts/
│   ├── ingest_data.py      # CLI for data ingestion
│   ├── resume_ingestion.py # Wait for rate limit reset and resume
│   ├── test_api.py         # Test API connectivity
│   └── test_chatbot.py     # Test chatbot with current data
├── data/
│   └── chroma_db/          # Local vector database
├── .env.example
├── requirements.txt
└── README.md
```

## Sprinklr API Endpoints

The client implements the following Sprinklr API endpoints:

### Case Search (v1) - Primary
```
POST https://api3.sprinklr.com/{env}/api/v1/case/search
```
- Proper pagination with `start` and `rows`
- Date filtering with `sinceDate`/`untilDate` (milliseconds)

### Case Search (v2) - Alternative
```
POST https://api3.sprinklr.com/{env}/api/v2/search/CASE
```
- Pagination with `page.start` (1-indexed) and `page.size`

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

### Rate Limits

When using live Sprinklr data, be aware of rate limits:
- **Hourly limit:** ~1000 API calls per hour (API returns 403 "Developer Over Rate")
- **Per-second limit:** 10 API calls per second

The client includes automatic rate limiting to stay within these bounds.

**API calls per case (with bulk fetch):**
- 1 search call to find cases (paginated)
- 1 call to get message IDs for a case
- 1 bulk fetch call to get all messages (regardless of count)

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
