"""
Streamlit web interface for the Sprinklr Historical Data Chatbot.

Provides a chat interface with filtering options and example queries.
"""

import streamlit as st
from datetime import datetime, timedelta

from .chatbot import create_chatbot
from .config import config


# Page configuration
st.set_page_config(
    page_title="Sprinklr Data Chatbot",
    page_icon="💬",
    layout="wide"
)

# Example queries
EXAMPLE_QUERIES = [
    "What were the most common questions about faith sharing?",
    "Summarize the types of conversations we had this month",
    "What questions do people ask about prayer?",
    "How do we typically handle conversations about doubt?",
    "What topics come up most frequently?",
    "Show me examples of conversations about grief and loss",
    "What were the outcomes of conversations about relationships?",
]


def init_session_state():
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "chatbot" not in st.session_state:
        st.session_state.chatbot = None


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
        st.error(
            "Chatbot could not be initialized. Please check your ANTHROPIC_API_KEY "
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
                        st.markdown(
                            f"**{source['id']}** ({date_display})\n"
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
                        st.markdown(
                            f"**{source['id']}** ({date_display})\n"
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
