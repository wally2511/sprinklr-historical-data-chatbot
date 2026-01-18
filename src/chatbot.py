"""
RAG Chatbot engine for querying historical engagement data.

Uses semantic search to find relevant cases and Claude to generate responses.
"""

from typing import List, Dict, Any, Optional
import anthropic
import openai

from config import config
from vector_store import VectorStore


SYSTEM_PROMPT = """You are an AI assistant helping community managers and product teams analyze historical social media engagement data. You have access to conversation cases from Sprinklr that contain interactions between users and agents.

Your role is to:
1. Answer questions about patterns, trends, and themes in the conversations
2. Summarize the types of questions and concerns users have
3. Identify common topics and how they were handled
4. Provide insights that can help improve community engagement

When answering:
- Base your responses on the actual case data provided in the context
- Be specific and cite examples when relevant
- If asked about something not covered in the provided cases, say so clearly
- Provide actionable insights when possible

The cases below are from real conversations and contain summaries and full conversation text."""


class Chatbot:
    """RAG-powered chatbot for querying engagement data."""

    def __init__(self, provider: str = None):
        """Initialize the chatbot with specified LLM provider."""
        self.vector_store = VectorStore()
        self.llm_client = None
        self.conversation_history: List[Dict[str, str]] = []
        self.provider = provider or config.LLM_PROVIDER
        self._init_llm_client()

    def _init_llm_client(self):
        """Initialize the LLM client based on the current provider."""
        if self.provider == "openai":
            if config.validate_openai_config():
                self.llm_client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
            else:
                raise ValueError(
                    "OpenAI API key not configured. "
                    "Please set OPENAI_API_KEY in .env"
                )
        else:  # anthropic (default)
            if config.validate_anthropic_config():
                self.llm_client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
            else:
                raise ValueError(
                    "Anthropic API key not configured. "
                    "Please set ANTHROPIC_API_KEY in .env"
                )

    def _call_llm(self, system_prompt: str, messages: List[Dict[str, str]]) -> str:
        """
        Call the LLM with the given prompt and messages.

        Args:
            system_prompt: System prompt for the LLM
            messages: List of conversation messages

        Returns:
            LLM response text
        """
        if self.provider == "openai":
            # OpenAI format: system message + user/assistant messages
            openai_messages = [{"role": "system", "content": system_prompt}]
            openai_messages.extend(messages)
            response = self.llm_client.chat.completions.create(
                model=config.OPENAI_MODEL,
                max_tokens=1500,
                messages=openai_messages
            )
            return response.choices[0].message.content
        else:
            # Anthropic format: separate system parameter
            response = self.llm_client.messages.create(
                model=config.CLAUDE_MODEL,
                max_tokens=1500,
                system=system_prompt,
                messages=messages
            )
            return response.content[0].text

    def set_provider(self, provider: str):
        """
        Switch to a different LLM provider.

        Args:
            provider: "anthropic" or "openai"
        """
        if provider != self.provider:
            self.provider = provider
            self._init_llm_client()
            self.clear_history()

    def _build_context(self, cases: List[Dict[str, Any]]) -> str:
        """
        Build context string from retrieved cases.

        Args:
            cases: List of case dictionaries from vector search

        Returns:
            Formatted context string
        """
        if not cases:
            return "No relevant cases found in the database."

        context_parts = []
        for i, case in enumerate(cases, 1):
            metadata = case.get("metadata", {})
            context_parts.append(f"""
--- Case {i} (#{metadata.get('case_number', 'Unknown')}) ---
Date: {metadata.get('created_at', 'Unknown')}
Brand: {metadata.get('brand', 'Unknown')}
Channel: {metadata.get('channel', 'Unknown')}
Theme: {metadata.get('theme', 'Unknown')}
Topics: {metadata.get('topics', 'Unknown')}
Outcome: {metadata.get('outcome', 'Unknown')}
Subject: {metadata.get('subject', 'Unknown')}

Summary: {case.get('summary', 'No summary available')}

Description: {metadata.get('description', 'No description')}

Conversation:
{metadata.get('full_conversation', 'No conversation text available')}
""")

        return "\n".join(context_parts)

    def search_cases(
        self,
        query: str,
        n_results: int = 10,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        theme: Optional[str] = None,
        brands: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant cases.

        Args:
            query: Natural language query
            n_results: Maximum number of results
            start_date: Optional date filter (ISO format)
            end_date: Optional date filter (ISO format)
            theme: Optional theme filter
            brands: Optional list of brands to filter by

        Returns:
            List of matching cases
        """
        return self.vector_store.search(
            query=query,
            n_results=n_results,
            start_date=start_date,
            end_date=end_date,
            theme=theme,
            brands=brands
        )

    def chat(
        self,
        message: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        theme: Optional[str] = None,
        brands: Optional[List[str]] = None,
        include_sources: bool = True
    ) -> Dict[str, Any]:
        """
        Process a chat message and generate a response.

        Args:
            message: User's question
            start_date: Optional date filter
            end_date: Optional date filter
            theme: Optional theme filter
            brands: Optional list of brands to filter by
            include_sources: Whether to include source cases in response

        Returns:
            Dictionary with response and metadata
        """
        # Search for relevant cases
        cases = self.search_cases(
            query=message,
            n_results=config.MAX_CONTEXT_CASES,
            start_date=start_date,
            end_date=end_date,
            theme=theme,
            brands=brands
        )

        # Build context from cases
        context = self._build_context(cases)

        # Prepare messages for Claude
        user_message = f"""Based on the following case data, please answer this question:

{message}

--- CASE DATA ---
{context}
--- END CASE DATA ---

Please provide a helpful, specific answer based on the cases above. If the cases don't contain enough information to answer the question fully, say so."""

        # Add to conversation history
        self.conversation_history.append({"role": "user", "content": user_message})

        # Generate response with LLM
        try:
            assistant_message = self._call_llm(SYSTEM_PROMPT, self.conversation_history)

            # Add response to history
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_message
            })

            # Keep history manageable (last 10 exchanges)
            if len(self.conversation_history) > 20:
                self.conversation_history = self.conversation_history[-20:]

            result = {
                "response": assistant_message,
                "cases_found": len(cases),
            }

            if include_sources:
                result["sources"] = [
                    {
                        "id": f"#{case.get('metadata', {}).get('case_number', 'Unknown')}",
                        "summary": case.get("summary", ""),
                        "brand": case.get("metadata", {}).get("brand", ""),
                        "theme": case.get("metadata", {}).get("theme", ""),
                        "date": case.get("metadata", {}).get("created_at", ""),
                    }
                    for case in cases  # Include all sources sent to LLM
                ]

            return result

        except Exception as e:
            return {
                "response": f"I encountered an error generating a response: {str(e)}",
                "cases_found": len(cases),
                "error": str(e)
            }

    def clear_history(self) -> None:
        """Clear the conversation history."""
        self.conversation_history = []

    def get_available_themes(self) -> List[str]:
        """Get all available themes for filtering."""
        return self.vector_store.get_all_themes()

    def get_available_brands(self) -> List[str]:
        """Get all available brands for filtering."""
        return self.vector_store.get_all_brands()

    def get_date_range(self) -> tuple[Optional[str], Optional[str]]:
        """Get the date range of available data."""
        return self.vector_store.get_date_range()

    def get_case_count(self) -> int:
        """Get the total number of cases in the database."""
        return self.vector_store.get_case_count()


def create_chatbot(provider: str = None) -> Optional[Chatbot]:
    """
    Create a chatbot instance, handling configuration errors gracefully.

    Args:
        provider: LLM provider ("anthropic" or "openai"), defaults to config setting

    Returns:
        Chatbot instance or None if configuration is missing
    """
    try:
        return Chatbot(provider=provider)
    except ValueError as e:
        print(f"Warning: {e}")
        return None
