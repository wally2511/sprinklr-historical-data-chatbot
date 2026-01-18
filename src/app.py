"""
Streamlit web interface for the Sprinklr Historical Data Chatbot.

Provides a chat interface with filtering options and example queries.
"""

import sys
from pathlib import Path

# Add src directory to path for imports when running directly with streamlit
src_dir = Path(__file__).parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

import streamlit as st
from datetime import datetime, timedelta

from chatbot import create_chatbot
from config import config


# Page configuration
st.set_page_config(
    page_title="Sprinklr Data Chatbot",
    page_icon="💬",
    layout="wide"
)

# Example queries - updated to match actual social media data
EXAMPLE_QUERIES = [
    "What are people commenting about on Instagram?",
    "Show me Facebook posts from Radio Christian Voice",
    "What types of interactions are we receiving?",
    "Summarize the social media comments this month",
    "What topics come up most frequently?",
    "Show me comments from Brand1",
    "What are people saying on YouTube and TikTok?",
]


def init_session_state():
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "chatbot" not in st.session_state:
        st.session_state.chatbot = None
    if "llm_provider" not in st.session_state:
        st.session_state.llm_provider = config.LLM_PROVIDER


def load_chatbot():
    """Load the chatbot, handling errors gracefully."""
    if st.session_state.chatbot is None:
        with st.spinner("Loading chatbot..."):
            st.session_state.chatbot = create_chatbot()

    return st.session_state.chatbot


def main():
    """Main application entry point."""
    init_session_state()

    # Header
    st.title("💬 Sprinklr Historical Data Chatbot")
    st.markdown(
        "Ask questions about your historical engagement data in natural language."
    )

    # Sidebar configuration
    with st.sidebar:
        st.header("Settings")

        # Data mode indicator
        if config.USE_MOCK_DATA:
            st.info("📊 Using mock data for testing")
        else:
            st.success("🔗 Connected to Sprinklr API")

        st.divider()

        # LLM Provider selector
        st.subheader("LLM Provider")
        providers = ["Anthropic (Claude)", "OpenAI (ChatGPT)"]
        provider_index = 0 if st.session_state.llm_provider == "anthropic" else 1
        selected_provider = st.selectbox(
            "Provider",
            providers,
            index=provider_index,
            key="provider_select"
        )
        new_provider = "anthropic" if "Anthropic" in selected_provider else "openai"

        # Handle provider change
        if new_provider != st.session_state.llm_provider:
            st.session_state.llm_provider = new_provider
            if st.session_state.chatbot:
                try:
                    st.session_state.chatbot.set_provider(new_provider)
                    st.session_state.messages = []  # Clear chat history on provider change
                    st.success(f"Switched to {selected_provider}")
                except ValueError as e:
                    st.error(str(e))
                    # Revert to previous provider
                    st.session_state.llm_provider = "anthropic" if new_provider == "openai" else "openai"

        st.divider()

        # Filters section
        st.subheader("Filters")

        # Date range filter
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "From",
                value=datetime.now() - timedelta(days=30),
                key="start_date"
            )
        with col2:
            end_date = st.date_input(
                "To",
                value=datetime.now(),
                key="end_date"
            )

        # Theme filter
        chatbot = load_chatbot()
        if chatbot:
            themes = ["All"] + chatbot.get_available_themes()
            selected_theme = st.selectbox("Theme", themes, key="theme")
            if selected_theme == "All":
                selected_theme = None
        else:
            selected_theme = None

        # Brand filter (multi-select)
        if chatbot:
            brands = chatbot.get_available_brands()
            if brands:
                selected_brands = st.multiselect(
                    "Brands",
                    options=brands,
                    default=brands,  # All selected by default
                    key="brands",
                    help="Select one or more brands to filter results"
                )
            else:
                selected_brands = None
        else:
            selected_brands = None

        st.divider()

        # Stats section
        st.subheader("Data Stats")
        if chatbot:
            case_count = chatbot.get_case_count()
            st.metric("Total Cases", case_count)

            date_range = chatbot.get_date_range()
            if date_range[0] and date_range[1]:
                st.text(f"Date range: {date_range[0][:10]} to {date_range[1][:10]}")
        else:
            st.warning("Chatbot not initialized")

        st.divider()

        # Clear conversation button
        if st.button("Clear Conversation", type="secondary"):
            st.session_state.messages = []
            if chatbot:
                chatbot.clear_history()
            st.rerun()

    # Main chat area
    if not chatbot:
        provider_name = "OPENAI_API_KEY" if st.session_state.llm_provider == "openai" else "ANTHROPIC_API_KEY"
        st.error(
            f"Chatbot could not be initialized. Please check your {provider_name} "
            "in the .env file."
        )
        st.stop()

    # Check if data is loaded
    if chatbot.get_case_count() == 0:
        st.warning(
            "No data has been ingested yet. Please run the ingestion script first:\n\n"
            "```bash\npython scripts/ingest_data.py\n```"
        )

    # Example queries section
    with st.expander("Example Queries", expanded=len(st.session_state.messages) == 0):
        cols = st.columns(2)
        for i, query in enumerate(EXAMPLE_QUERIES):
            col = cols[i % 2]
            if col.button(query, key=f"example_{i}", use_container_width=True):
                st.session_state.pending_query = query
                st.rerun()

    # Display conversation history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

            # Show sources if available
            if message["role"] == "assistant" and "sources" in message:
                with st.expander("View Sources"):
                    for source in message["sources"]:
                        date_str = source.get('date', '') or 'Unknown'
                        date_display = date_str[:10] if len(date_str) >= 10 else date_str
                        summary_str = source.get('summary', '') or 'No summary'
                        st.markdown(
                            f"**{source['id']}** ({date_display})\n"
                            f"Theme: {source.get('theme', 'Unknown')} | "
                            f"Summary: {summary_str[:100]}..."
                        )

    # Handle pending query from example buttons
    if "pending_query" in st.session_state:
        query = st.session_state.pending_query
        del st.session_state.pending_query

        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": query})

        # Display user message
        with st.chat_message("user"):
            st.markdown(query)

        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Searching and analyzing..."):
                response = chatbot.chat(
                    message=query,
                    start_date=start_date.isoformat() if start_date else None,
                    end_date=end_date.isoformat() if end_date else None,
                    theme=selected_theme,
                    brands=selected_brands,
                    include_sources=True
                )

            st.markdown(response["response"])

            # Show sources
            if "sources" in response and response["sources"]:
                with st.expander(f"View Sources ({response['cases_found']} cases found)"):
                    for source in response["sources"]:
                        date_str = source.get('date', '') or 'Unknown'
                        date_display = date_str[:10] if len(date_str) >= 10 else date_str
                        summary_str = source.get('summary', '') or 'No summary'
                        brand_str = source.get('brand', 'Unknown')
                        st.markdown(
                            f"**{source['id']}** ({date_display})\n"
                            f"Brand: {brand_str} | "
                            f"Theme: {source.get('theme', 'Unknown')} | "
                            f"Summary: {summary_str[:100]}..."
                        )

        # Add assistant response to history
        st.session_state.messages.append({
            "role": "assistant",
            "content": response["response"],
            "sources": response.get("sources", [])
        })

        st.rerun()

    # Chat input
    if prompt := st.chat_input("Ask a question about your engagement data..."):
        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Searching and analyzing..."):
                response = chatbot.chat(
                    message=prompt,
                    start_date=start_date.isoformat() if start_date else None,
                    end_date=end_date.isoformat() if end_date else None,
                    theme=selected_theme,
                    brands=selected_brands,
                    include_sources=True
                )

            st.markdown(response["response"])

            # Show sources
            if "sources" in response and response["sources"]:
                with st.expander(f"View Sources ({response['cases_found']} cases found)"):
                    for source in response["sources"]:
                        date_str = source.get('date', '') or 'Unknown'
                        date_display = date_str[:10] if len(date_str) >= 10 else date_str
                        summary_str = source.get('summary', '') or 'No summary'
                        brand_str = source.get('brand', 'Unknown')
                        st.markdown(
                            f"**{source['id']}** ({date_display})\n"
                            f"Brand: {brand_str} | "
                            f"Theme: {source.get('theme', 'Unknown')} | "
                            f"Summary: {summary_str[:100]}..."
                        )

        # Add assistant response to history
        st.session_state.messages.append({
            "role": "assistant",
            "content": response["response"],
            "sources": response.get("sources", [])
        })


if __name__ == "__main__":
    main()
