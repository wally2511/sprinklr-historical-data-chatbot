# Sprinklr Historical Data Chatbot

A RAG-powered chatbot that allows community managers and product teams to query historical social media engagement data from Sprinklr using natural language.

## Features

- **Natural Language Queries**: Ask questions about your engagement data in plain English
- **Semantic Search**: Find relevant conversations using AI-powered vector search
- **Case Summaries**: AI-generated summaries for better pattern recognition
- **Date Range Filtering**: Analyze specific time periods
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
│   ├── sprinklr_client.py  # Sprinklr API wrapper
│   ├── mock_data.py        # Sample data for testing
│   ├── ingestion.py        # Data ingestion pipeline
│   ├── vector_store.py     # ChromaDB operations
│   ├── chatbot.py          # RAG chatbot logic
│   └── app.py              # Streamlit interface
├── scripts/
│   └── ingest_data.py      # CLI for data ingestion
├── data/
│   └── chroma_db/          # Local vector database
├── .env.example
├── requirements.txt
└── README.md
```

## Development

### Mock Data Mode

The chatbot includes realistic sample conversations for testing without Sprinklr access. This is useful for:
- Initial development and testing
- Demos and stakeholder presentations
- Validating the RAG architecture

### Rate Limits

When using live Sprinklr data, be aware of rate limits:
- 1000 API calls per hour
- 10 API calls per second

The client includes automatic rate limiting to stay within these bounds.

## Privacy Considerations

- Conversation data may contain sensitive information
- The local ChromaDB database stores case data on disk
- Ensure appropriate access controls for the data directory
- Consider data retention policies for your organization
