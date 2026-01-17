"""
Data ingestion pipeline for processing and storing Sprinklr cases.

Handles fetching data from Sprinklr or mock data, generating AI summaries,
and storing in the vector database.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import anthropic

from config import config
from vector_store import VectorStore
from sprinklr_client import SprinklrClient
from mock_data import generate_mock_cases


class IngestionPipeline:
    """Pipeline for ingesting case data into the vector store."""

    def __init__(self):
        """Initialize the ingestion pipeline."""
        self.vector_store = VectorStore()
        self.claude_client = None

        if config.validate_anthropic_config():
            self.claude_client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    def _format_conversation(self, messages: List[Dict[str, Any]]) -> str:
        """Format messages into a readable conversation string."""
        lines = []
        for msg in messages:
            role = msg.get("role", "unknown").upper()
            sender = msg.get("sender", "")
            content = msg.get("content", "")
            if sender:
                lines.append(f"{role} ({sender}): {content}")
            else:
                lines.append(f"{role}: {content}")
        return "\n".join(lines)

    def _generate_summary_with_claude(self, conversation: str) -> str:
        """
        Generate a summary of the conversation using Claude.

        Args:
            conversation: Formatted conversation text

        Returns:
            AI-generated summary
        """
        if not self.claude_client:
            return self._generate_simple_summary(conversation)

        try:
            response = self.claude_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=300,
                messages=[
                    {
                        "role": "user",
                        "content": f"""Summarize this conversation in 2-3 sentences. Focus on:
1. The main topic or question the user asked about
2. Key themes (faith, prayer, doubt, relationships, etc.)
3. The outcome or resolution

Conversation:
{conversation}

Summary:"""
                    }
                ]
            )
            return response.content[0].text.strip()

        except Exception as e:
            print(f"Warning: Claude API error, using simple summary: {e}")
            return self._generate_simple_summary(conversation)

    def _generate_simple_summary(self, conversation: str) -> str:
        """Generate a simple summary without AI (fallback)."""
        # Extract first user message as main topic
        lines = conversation.split("\n")
        user_message = ""
        for line in lines:
            if line.startswith("USER:"):
                user_message = line.replace("USER:", "").strip()
                break

        if user_message:
            return f"User asked: {user_message[:200]}..."
        return "Conversation about faith-related topics."

    def _build_searchable_text(self, case: Dict[str, Any], full_conversation: str) -> str:
        """
        Build searchable text from all available case fields.

        Combines multiple fields to create a rich text for semantic search,
        even when individual fields are short (like social media comments).
        """
        parts = []

        # Add channel context
        channel = case.get("channel", "")
        if channel:
            parts.append(f"This is a {channel} interaction.")

        # Add brand context
        brand = case.get("brand", "")
        if brand:
            parts.append(f"Brand: {brand}.")

        # Add subject if meaningful
        subject = case.get("subject", "")
        if subject and len(subject) > 10:
            parts.append(f"Subject: {subject}")

        # Add description/message content
        description = case.get("description", "")
        if description:
            parts.append(f"Message content: {description}")

        # Add conversation if available
        if full_conversation.strip():
            parts.append(f"Conversation: {full_conversation}")

        return " ".join(parts)

    def process_case(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single case for storage.

        Args:
            case: Raw case data with messages

        Returns:
            Processed case with summary and formatted conversation
        """
        # Format the conversation
        messages = case.get("messages", [])
        full_conversation = self._format_conversation(messages)

        # Build searchable text combining all fields
        searchable_text = self._build_searchable_text(case, full_conversation)

        # Generate summary based on available content
        if full_conversation.strip() and len(full_conversation) > 100:
            # Rich conversation - use AI summary
            summary = self._generate_summary_with_claude(full_conversation)
        else:
            # Short content (social media comments) - use the searchable text as summary
            summary = searchable_text

        return {
            "id": case.get("id", ""),
            "case_number": case.get("case_number"),
            "summary": summary,
            "full_conversation": full_conversation,
            "description": case.get("description", ""),
            "subject": case.get("subject", ""),
            "created_at": case.get("created_at", ""),
            "channel": case.get("channel", ""),
            "brand": case.get("brand", ""),
            "theme": case.get("theme", ""),
            "outcome": case.get("outcome", ""),
            "topics": case.get("topics", []),
            "sentiment": case.get("sentiment", 0),
            "language": case.get("language", ""),
            "country": case.get("country", ""),
            "message_count": len(messages),
        }

    def ingest_mock_data(
        self,
        num_cases: int = 50,
        days_back: int = 30,
        clear_existing: bool = True
    ) -> int:
        """
        Ingest mock data for testing.

        Args:
            num_cases: Number of mock cases to generate
            days_back: Days back to spread cases
            clear_existing: Whether to clear existing data

        Returns:
            Number of cases ingested
        """
        print(f"Generating {num_cases} mock cases...")

        if clear_existing:
            print("Clearing existing data...")
            self.vector_store.clear()

        # Generate mock cases
        cases = generate_mock_cases(num_cases, days_back)

        # Process and store cases
        processed_cases = []
        for i, case in enumerate(cases):
            print(f"Processing case {i + 1}/{num_cases}...")
            processed = self.process_case(case)
            processed_cases.append(processed)

        print(f"Storing {len(processed_cases)} cases in vector store...")
        count = self.vector_store.add_cases_batch(processed_cases)

        print(f"Successfully ingested {count} cases.")
        return count

    def ingest_live_data(
        self,
        days_back: int = 30,
        max_cases: Optional[int] = None,
        clear_existing: bool = True
    ) -> int:
        """
        Ingest live data from Sprinklr API.

        Args:
            days_back: Number of days of historical data to fetch
            max_cases: Maximum number of cases to fetch (None for all)
            clear_existing: Whether to clear existing data

        Returns:
            Number of cases ingested
        """
        if not config.validate_sprinklr_config():
            raise ValueError(
                "Sprinklr API credentials not configured. "
                "Please set SPRINKLR_API_KEY and SPRINKLR_ACCESS_TOKEN in .env"
            )

        print(f"Fetching cases from the last {days_back} days...")

        if clear_existing:
            print("Clearing existing data...")
            self.vector_store.clear()

        # Initialize Sprinklr client
        client = SprinklrClient()

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        # Fetch and process cases
        processed_cases = []
        case_count = 0

        for case in client.fetch_cases_with_messages(
            start_date=start_date,
            end_date=end_date,
            max_cases=max_cases
        ):
            case_count += 1

            # Extract metadata using client helper
            metadata = SprinklrClient.extract_case_metadata(case)
            brand = metadata.get("brand", "Unknown")

            print(f"Processing case {case_count}: #{metadata.get('case_number')} ({brand})...")

            # Format messages from Sprinklr API format
            # New format has: content.text, senderProfile, senderType
            messages = []
            for msg in case.get("messages", []):
                # Get message text from content.text
                content = msg.get("content", {})
                text = content.get("text", "") if isinstance(content, dict) else ""

                # Determine role - check senderType or infer from profile
                sender_type = msg.get("senderType", "")
                if sender_type == "AGENT" or sender_type == "BRAND":
                    role = "agent"
                else:
                    # Default to user for PROFILE or unknown
                    role = "user"

                # Get sender name for context
                sender_profile = msg.get("senderProfile", {})
                sender_name = sender_profile.get("name", "Unknown")

                if text:
                    messages.append({
                        "role": role,
                        "content": text,
                        "sender": sender_name
                    })

            # Map Sprinklr data to our format
            formatted_case = {
                "id": metadata.get("case_id", ""),
                "case_number": metadata.get("case_number"),
                "messages": messages,
                "description": metadata.get("description", ""),
                "subject": metadata.get("subject", ""),
                "created_at": datetime.fromtimestamp(
                    metadata.get("created_time", 0) / 1000
                ).isoformat() if metadata.get("created_time") else "",
                "channel": metadata.get("channel", ""),
                "brand": metadata.get("brand", ""),
                "theme": "",  # Would need NLP to extract
                "outcome": metadata.get("status", ""),
                "topics": [],  # Would need NLP to extract
                "sentiment": metadata.get("sentiment", 0),
                "language": metadata.get("language", ""),
                "country": metadata.get("country", ""),
            }

            processed = self.process_case(formatted_case)
            processed_cases.append(processed)

            # Batch insert every 50 cases
            if len(processed_cases) >= 50:
                print(f"Storing batch of {len(processed_cases)} cases...")
                self.vector_store.add_cases_batch(processed_cases)
                processed_cases = []

        # Insert remaining cases
        if processed_cases:
            print(f"Storing final batch of {len(processed_cases)} cases...")
            self.vector_store.add_cases_batch(processed_cases)

        total = self.vector_store.get_case_count()
        print(f"Successfully ingested {total} cases.")
        return total

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the ingested data."""
        count = self.vector_store.get_case_count()
        themes = self.vector_store.get_all_themes()
        date_range = self.vector_store.get_date_range()

        return {
            "total_cases": count,
            "themes": themes,
            "date_range": {
                "start": date_range[0],
                "end": date_range[1]
            }
        }
