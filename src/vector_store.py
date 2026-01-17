"""
Vector store module for ChromaDB operations.

Handles storage and retrieval of case embeddings for semantic search.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from .config import config


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

            # Prepare metadata
            clean_metadata = {
                "summary": summary,
                "full_conversation": case.get("full_conversation", "")[:5000],
                "created_at": case.get("created_at", ""),
                "channel": case.get("channel", ""),
                "theme": case.get("theme", ""),
                "outcome": case.get("outcome", ""),
                "topics": ",".join(case.get("topics", [])),
                "message_count": case.get("message_count", 0),
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
        theme: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant cases using semantic similarity.

        Args:
            query: Natural language query
            n_results: Maximum number of results to return
            start_date: Optional start date filter (ISO format)
            end_date: Optional end date filter (ISO format)
            theme: Optional theme filter

        Returns:
            List of matching cases with scores
        """
        # Generate query embedding
        query_embedding = self._generate_embedding(query)

        # Build where clause for filtering
        where_clause = None
        where_conditions = []

        if theme:
            where_conditions.append({"theme": {"$eq": theme}})

        # Note: ChromaDB date filtering is string-based
        # For more complex date filtering, we'd filter post-query
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

                # Apply date filtering if specified (post-query filtering)
                if start_date or end_date:
                    case_date = case["metadata"].get("created_at", "")
                    if case_date:
                        if start_date and case_date < start_date:
                            continue
                        if end_date and case_date > end_date:
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
