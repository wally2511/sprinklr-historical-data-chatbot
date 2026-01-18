"""
Data ingestion pipeline for processing and storing Sprinklr cases.

Handles fetching data from Sprinklr or mock data, generating AI summaries,
and storing in the vector database.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from config import config
from vector_store import VectorStore
from sprinklr_client import SprinklrClient
from mock_data import generate_mock_cases
from services.theme_extractor import ThemeExtractor, extract_theme_keywords
from services.message_store import MessageStore, find_message_database


class IngestionPipeline:
    """Pipeline for ingesting case data into the vector store."""

    def __init__(self):
        """Initialize the ingestion pipeline."""
        self.vector_store = VectorStore()
        self.llm_client = None
        self.llm_provider = config.LLM_PROVIDER

        # Initialize LLM client based on provider setting
        if self.llm_provider == "openai" and config.validate_openai_config():
            import openai
            self.llm_client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
        elif config.validate_anthropic_config():
            import anthropic
            self.llm_client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

        # Initialize theme extractor (uses keyword-based extraction by default)
        self.theme_extractor = ThemeExtractor(
            llm_client=self.llm_client if self.llm_provider == "anthropic" else None,
            method="keyword"  # Use "llm" for more accurate but slower extraction
        )

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

    def _generate_summary_with_llm(self, conversation: str) -> str:
        """Generate a summary optimized for semantic search retrieval."""
        if not self.llm_client:
            return self._generate_simple_summary(conversation)

        prompt = f"""Write a 1-2 sentence summary of this conversation for semantic search retrieval.

Focus on:
- What the user asked or discussed
- The nature of the interaction (question, complaint, request, etc.)
- Any resolution or response provided

Do NOT include channel names, brand names, or case numbers - just summarize the conversation content.

Conversation:
{conversation}

Summary:"""

        try:
            if self.llm_provider == "openai":
                response = self.llm_client.chat.completions.create(
                    model=config.OPENAI_MODEL,
                    max_tokens=150,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.choices[0].message.content.strip()
            else:
                # Anthropic/Claude
                response = self.llm_client.messages.create(
                    model=config.CLAUDE_MODEL,
                    max_tokens=150,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text.strip()

        except Exception as e:
            print(f"Warning: LLM API error, using simple summary: {e}")
            return self._generate_simple_summary(conversation)

    def _generate_simple_summary(self, conversation: str) -> str:
        """Generate a simple summary from conversation content (fallback)."""
        if not conversation or not conversation.strip():
            return "No conversation content available."

        # Extract all message content (strip role prefixes)
        content_parts = []
        for line in conversation.split("\n"):
            line = line.strip()
            if not line:
                continue
            # Remove role prefix like "USER (Name):" or "AGENT:"
            if ":" in line:
                content = line.split(":", 1)[1].strip()
                if content and len(content) > 2:
                    content_parts.append(content)

        if not content_parts:
            return "Brief interaction with minimal content."

        # Combine and truncate
        combined = " | ".join(content_parts)
        if len(combined) > 200:
            return combined[:197] + "..."
        return combined

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

        # Generate summary based on conversation content only
        if full_conversation.strip() and len(full_conversation) > 50:
            summary = self._generate_summary_with_llm(full_conversation)
        else:
            summary = self._generate_simple_summary(full_conversation)

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

        for case in client.fetch_cases_with_messages_batched(
            start_date=start_date,
            end_date=end_date,
            max_cases=max_cases,
            case_batch_size=50,  # Batch 50 cases before bulk message fetch
            message_bulk_limit=500  # Max messages per bulk fetch request
        ):
            case_count += 1

            # Extract metadata using client helper
            metadata = SprinklrClient.extract_case_metadata(case)
            brand = metadata.get("brand", "Unknown")

            print(f"Processing case {case_count}: #{metadata.get('case_number')} ({brand})...")

            # Format messages from Sprinklr API format
            # Key fields: content.text, senderProfile, brandPost
            messages = []
            for msg in case.get("messages", []):
                # Get message text from content.text
                content = msg.get("content", {})
                text = content.get("text", "") if isinstance(content, dict) else ""

                # Determine role using brandPost field (most reliable)
                # brandPost=True means it's a brand/agent message
                # brandPost=False means it's a user/fan message
                is_brand_post = msg.get("brandPost", False)
                role = "agent" if is_brand_post else "user"

                # Get sender name for context
                sender_profile = msg.get("senderProfile", {})
                sender_name = sender_profile.get("name", "Unknown")

                if text:
                    messages.append({
                        "role": role,
                        "content": text,
                        "sender": sender_name
                    })

            # Format conversation for theme extraction
            conversation_text = self._format_conversation(messages)

            # Extract theme from conversation content
            extracted_theme = self.theme_extractor.extract_theme(conversation_text) if conversation_text else "general"

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
                "theme": extracted_theme,
                "outcome": metadata.get("status", ""),
                "topics": [],  # Could add topic extraction later
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

    def ingest_hybrid(
        self,
        db_path: Optional[str] = None,
        days_back: int = 365,
        max_cases: Optional[int] = None,
        clear_existing: bool = True,
        skip_api_fallback: bool = False
    ) -> int:
        """
        Ingest data using API for cases and SQLite database for messages.

        This hybrid approach:
        1. Fetches case metadata from Sprinklr API (not rate-limited)
        2. Loads message content from SQLite database (converted from XLSX)
        3. Optionally falls back to API bulk fetch if messages not in database

        Args:
            db_path: Path to SQLite message database.
                    If None, auto-discovers from data/messages.db
            days_back: Number of days of historical data to fetch
            max_cases: Maximum number of cases to fetch (None for all)
            clear_existing: Whether to clear existing data
            skip_api_fallback: If True, skip cases not found in message DB

        Returns:
            Number of cases ingested
        """
        if not config.validate_sprinklr_config():
            raise ValueError(
                "Sprinklr API credentials not configured. "
                "Please set SPRINKLR_API_KEY and SPRINKLR_ACCESS_TOKEN in .env"
            )

        # Find message database
        if not db_path:
            db_path = find_message_database()
            if not db_path:
                raise FileNotFoundError(
                    "Message database not found. Run 'python scripts/xlsx_to_sqlite.py' first "
                    "to convert XLSX files to SQLite database."
                )

        print(f"Initializing hybrid ingestion...")
        print(f"  Message DB: {db_path}")
        print(f"  Days back: {days_back}")
        print(f"  Max cases: {max_cases or 'unlimited'}")
        print(f"  Skip API fallback: {skip_api_fallback}")
        print()

        # Load message store from SQLite
        message_store = MessageStore(db_path)

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
        xlsx_hits = 0
        api_fallbacks = 0
        no_messages = 0

        # Use search_cases_v2 to get cases (with pagination)
        cursor = None

        while True:
            if max_cases and case_count >= max_cases:
                break

            # Fetch batch of cases
            search_result = client.search_cases_v2(
                start_date=start_date,
                end_date=end_date,
                size=100,
                cursor=cursor
            )

            cases = search_result.get("data", [])
            cursor = search_result.get("cursor")

            if not cases:
                break

            for case in cases:
                if max_cases and case_count >= max_cases:
                    break

                case_id = case.get("id")
                if not case_id:
                    continue

                # Extract metadata using client helper
                metadata = SprinklrClient.extract_case_metadata(case)
                case_number = metadata.get("case_number")
                brand = metadata.get("brand", "Unknown")

                case_count += 1
                print(f"Processing case {case_count}: #{case_number} ({brand})...", end=" ")

                # Try to get messages from XLSX store first
                messages = []
                if case_number and message_store.has_messages_for_case(case_number):
                    messages = message_store.get_messages_for_case(case_number)
                    xlsx_hits += 1
                    print(f"[DB: {len(messages)} messages]")
                else:
                    if skip_api_fallback:
                        # Skip this case - not in message DB
                        no_messages += 1
                        print(f"[Skipped - not in DB]")
                        continue
                    else:
                        # Fall back to API bulk fetch
                        try:
                            api_messages = client.get_case_messages(case_id)
                            for msg in api_messages:
                                content = msg.get("content", {})
                                text = content.get("text", "") if isinstance(content, dict) else ""
                                is_brand_post = msg.get("brandPost", False)
                                sender_profile = msg.get("senderProfile", {})
                                sender_name = sender_profile.get("name", "Unknown")

                                if text:
                                    messages.append({
                                        "role": "agent" if is_brand_post else "user",
                                        "content": text,
                                        "sender": sender_name
                                    })

                            if messages:
                                api_fallbacks += 1
                                print(f"[API: {len(messages)} messages]")
                            else:
                                no_messages += 1
                                print("[No messages]")
                        except Exception as e:
                            no_messages += 1
                            print(f"[Error: {e}]")

                # Format conversation for theme extraction
                conversation_text = self._format_conversation(messages)

                # Extract theme from conversation content
                extracted_theme = self.theme_extractor.extract_theme(conversation_text) if conversation_text else "general"

                # Map data to our format
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
                    "theme": extracted_theme,
                    "outcome": metadata.get("status", ""),
                    "topics": [],
                    "sentiment": metadata.get("sentiment", 0),
                    "language": metadata.get("language", ""),
                    "country": metadata.get("country", ""),
                }

                processed = self.process_case(formatted_case)
                processed_cases.append(processed)

                # Batch insert every 50 cases
                if len(processed_cases) >= 50:
                    print(f"\nStoring batch of {len(processed_cases)} cases...")
                    self.vector_store.add_cases_batch(processed_cases)
                    processed_cases = []

            # Stop if no cursor (no more results)
            if not cursor:
                break

        # Insert remaining cases
        if processed_cases:
            print(f"\nStoring final batch of {len(processed_cases)} cases...")
            self.vector_store.add_cases_batch(processed_cases)

        # Close message store
        message_store.close()

        total = self.vector_store.get_case_count()
        print(f"\n=== Hybrid Ingestion Complete ===")
        print(f"Total cases ingested: {total}")
        print(f"Messages from DB: {xlsx_hits} cases")
        print(f"Messages from API: {api_fallbacks} cases")
        print(f"Skipped/No messages: {no_messages} cases")

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
