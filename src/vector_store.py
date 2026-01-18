"""
Vector store module for ChromaDB operations.

Handles storage and retrieval of case embeddings for semantic search.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from config import config


class VectorStore:
    """Manages ChromaDB collection for case embeddings and semantic search."""

    def __init__(self):
        """Initialize the vector store with ChromaDB and embedding model."""
        # Ensure data directory exists
        config.ensure_data_directory()

        # Initialize ChromaDB with persistent storage
        self.client = chromadb.PersistentClient(
            path=config.CHROMA_DB_PATH,
            settings=Settings(anonymized_telemetry=False)
        )

        # Initialize embedding model
        self.embedding_model = SentenceTransformer(config.EMBEDDING_MODEL)

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=config.COLLECTION_NAME,
            metadata={"description": "Sprinklr case conversations and summaries"}
        )

    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for text."""
        embedding = self.embedding_model.encode(text)
        return embedding.tolist()

    def add_case(
        self,
        case_id: str,
        summary: str,
        full_conversation: str,
        metadata: Dict[str, Any]
    ) -> None:
        """
        Add a case to the vector store.

        Args:
            case_id: Unique identifier for the case
            summary: AI-generated summary of the case (used for embedding)
            full_conversation: Full conversation text for context
            metadata: Additional metadata (date, themes, outcome, etc.)
        """
        # Generate embedding from summary (cleaner semantic signal)
        embedding = self._generate_embedding(summary)

        # Prepare metadata - ChromaDB only supports string, int, float, bool
        clean_metadata = {
            "summary": summary,
            "full_conversation": full_conversation[:5000],  # Truncate if too long
            "created_at": metadata.get("created_at", ""),
            "channel": metadata.get("channel", ""),
            "theme": metadata.get("theme", ""),
            "outcome": metadata.get("outcome", ""),
            "topics": ",".join(metadata.get("topics", [])),  # Convert list to string
            "message_count": metadata.get("message_count", 0),
        }

        # Add to collection
        self.collection.upsert(
            ids=[case_id],
            embeddings=[embedding],
            metadatas=[clean_metadata],
            documents=[summary]
        )

    def add_cases_batch(self, cases: List[Dict[str, Any]]) -> int:
        """
        Add multiple cases to the vector store in batch.

        Args:
            cases: List of case dictionaries with summary and metadata

        Returns:
            Number of cases added
        """
        if not cases:
            return 0

        ids = []
        embeddings = []
        metadatas = []
        documents = []

        for case in cases:
            case_id = case["id"]
            summary = case["summary"]

            # Generate embedding
            embedding = self._generate_embedding(summary)

            # Prepare metadata - ChromaDB only supports string, int, float, bool
            clean_metadata = {
                "summary": summary,
                "full_conversation": case.get("full_conversation", "")[:5000],
                "description": case.get("description", "")[:1000],
                "subject": case.get("subject", "")[:500],
                "created_at": case.get("created_at", ""),
                "channel": case.get("channel", ""),
                "brand": case.get("brand", ""),
                "theme": case.get("theme", ""),
                "outcome": case.get("outcome", ""),
                "topics": ",".join(case.get("topics", [])),
                "message_count": case.get("message_count", 0),
                "sentiment": case.get("sentiment", 0),
                "language": case.get("language", ""),
                "country": case.get("country", ""),
                "case_number": case.get("case_number") or 0,
            }

            ids.append(case_id)
            embeddings.append(embedding)
            metadatas.append(clean_metadata)
            documents.append(summary)

        # Batch upsert
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents
        )

        return len(cases)

    def search(
        self,
        query: str,
        n_results: int = 10,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        theme: Optional[str] = None,
        brands: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant cases using semantic similarity.

        Args:
            query: Natural language query
            n_results: Maximum number of results to return
            start_date: Optional start date filter (ISO format)
            end_date: Optional end date filter (ISO format)
            theme: Optional theme filter
            brands: Optional list of brands to filter by

        Returns:
            List of matching cases with scores
        """
        # Generate query embedding
        query_embedding = self._generate_embedding(query)

        # Build where clause for filtering
        # Note: ChromaDB comparison operators ($gte, $lte) only work with numeric types,
        # so date filtering must be done post-query on ISO date strings
        where_clause = None
        where_conditions = []

        if theme:
            where_conditions.append({"theme": {"$eq": theme}})

        if brands and len(brands) > 0:
            # Use $in operator for multiple brands
            where_conditions.append({"brand": {"$in": brands}})

        if where_conditions:
            if len(where_conditions) == 1:
                where_clause = where_conditions[0]
            else:
                where_clause = {"$and": where_conditions}

        # Perform search
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_clause,
            include=["documents", "metadatas", "distances"]
        )

        # Process results
        cases = []
        if results and results["ids"] and results["ids"][0]:
            for i, case_id in enumerate(results["ids"][0]):
                case = {
                    "id": case_id,
                    "summary": results["documents"][0][i] if results["documents"] else "",
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else 0,
                }

                # Apply date filtering post-query (ChromaDB doesn't support string comparisons)
                if start_date or end_date:
                    case_date = case["metadata"].get("created_at", "")
                    if case_date:
                        # Extract date portion only (YYYY-MM-DD) for comparison
                        case_date_only = case_date[:10] if len(case_date) >= 10 else case_date
                        if start_date and case_date_only < start_date[:10]:
                            continue
                        if end_date and case_date_only > end_date[:10]:
                            continue

                cases.append(case)

        return cases

    def get_case_count(self) -> int:
        """Get the total number of cases in the store."""
        return self.collection.count()

    def clear(self) -> None:
        """Clear all cases from the store."""
        # Delete and recreate collection
        self.client.delete_collection(config.COLLECTION_NAME)
        self.collection = self.client.get_or_create_collection(
            name=config.COLLECTION_NAME,
            metadata={"description": "Sprinklr case conversations and summaries"}
        )

    def get_all_themes(self) -> List[str]:
        """Get all unique themes in the store."""
        # This is a simple implementation - for large stores,
        # you might want to maintain a separate index
        results = self.collection.get(include=["metadatas"])
        themes = set()
        if results and results["metadatas"]:
            for metadata in results["metadatas"]:
                if metadata.get("theme"):
                    themes.add(metadata["theme"])
        return sorted(list(themes))

    def get_all_brands(self) -> List[str]:
        """Get all unique brands in the store."""
        results = self.collection.get(include=["metadatas"])
        brands = set()
        if results and results["metadatas"]:
            for metadata in results["metadatas"]:
                if metadata.get("brand"):
                    brands.add(metadata["brand"])
        return sorted(list(brands))

    def get_date_range(self) -> tuple[Optional[str], Optional[str]]:
        """Get the date range of cases in the store."""
        results = self.collection.get(include=["metadatas"])
        if not results or not results["metadatas"]:
            return None, None

        dates = []
        for metadata in results["metadatas"]:
            if metadata.get("created_at"):
                dates.append(metadata["created_at"])

        if not dates:
            return None, None

        return min(dates), max(dates)

    def get_by_case_number(self, case_number: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve a case by its case number using metadata filtering.

        Args:
            case_number: The case number to look up

        Returns:
            Case dictionary or None if not found
        """
        results = self.collection.get(
            where={"case_number": {"$eq": case_number}},
            include=["documents", "metadatas"]
        )

        if results and results["ids"]:
            return {
                "id": results["ids"][0],
                "summary": results["documents"][0] if results["documents"] else "",
                "metadata": results["metadatas"][0] if results["metadatas"] else {}
            }
        return None

    def get_by_case_numbers(self, case_numbers: List[int]) -> List[Dict[str, Any]]:
        """
        Batch retrieve multiple cases by case numbers.

        Args:
            case_numbers: List of case numbers to look up

        Returns:
            List of case dictionaries
        """
        if not case_numbers:
            return []

        results = self.collection.get(
            where={"case_number": {"$in": case_numbers}},
            include=["documents", "metadatas"]
        )

        cases = []
        if results and results["ids"]:
            for i, case_id in enumerate(results["ids"]):
                cases.append({
                    "id": case_id,
                    "summary": results["documents"][i] if results["documents"] else "",
                    "metadata": results["metadatas"][i] if results["metadatas"] else {}
                })
        return cases

    def count_by_theme(self) -> Dict[str, int]:
        """
        Count cases grouped by theme.

        Returns:
            Dictionary mapping theme names to case counts
        """
        results = self.collection.get(include=["metadatas"])
        counts: Dict[str, int] = {}

        if results and results["metadatas"]:
            for metadata in results["metadatas"]:
                theme = metadata.get("theme") or "Unknown"
                counts[theme] = counts.get(theme, 0) + 1

        return dict(sorted(counts.items(), key=lambda x: -x[1]))

    def count_by_brand(self) -> Dict[str, int]:
        """
        Count cases grouped by brand.

        Returns:
            Dictionary mapping brand names to case counts
        """
        results = self.collection.get(include=["metadatas"])
        counts: Dict[str, int] = {}

        if results and results["metadatas"]:
            for metadata in results["metadatas"]:
                brand = metadata.get("brand") or "Unknown"
                counts[brand] = counts.get(brand, 0) + 1

        return dict(sorted(counts.items(), key=lambda x: -x[1]))

    def count_by_field(self, field: str) -> Dict[str, int]:
        """
        Count cases grouped by any metadata field.

        Args:
            field: The metadata field to group by

        Returns:
            Dictionary mapping field values to case counts
        """
        results = self.collection.get(include=["metadatas"])
        counts: Dict[str, int] = {}

        if results and results["metadatas"]:
            for metadata in results["metadatas"]:
                value = metadata.get(field) or "Unknown"
                # Handle numeric fields
                if isinstance(value, (int, float)):
                    value = str(value)
                counts[value] = counts.get(value, 0) + 1

        return dict(sorted(counts.items(), key=lambda x: -x[1]))

    def get_all_cases(
        self,
        limit: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all cases with optional filtering.

        Args:
            limit: Maximum number of cases to return
            start_date: Optional start date filter (ISO format)
            end_date: Optional end date filter (ISO format)

        Returns:
            List of case dictionaries
        """
        results = self.collection.get(include=["documents", "metadatas"])

        cases = []
        if results and results["ids"]:
            for i, case_id in enumerate(results["ids"]):
                case = {
                    "id": case_id,
                    "summary": results["documents"][i] if results["documents"] else "",
                    "metadata": results["metadatas"][i] if results["metadatas"] else {}
                }

                # Apply date filtering
                if start_date or end_date:
                    case_date = case["metadata"].get("created_at", "")
                    if case_date:
                        case_date_only = case_date[:10] if len(case_date) >= 10 else case_date
                        if start_date and case_date_only < start_date[:10]:
                            continue
                        if end_date and case_date_only > end_date[:10]:
                            continue

                cases.append(case)

                if limit and len(cases) >= limit:
                    break

        return cases
