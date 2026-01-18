"""
Message store service for hybrid ingestion.

Provides a lookup service that loads messages from a SQLite database
(converted from XLSX exports) for fast lookups during API-based case ingestion.
"""

import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any


class MessageStore:
    """
    Service for looking up pre-loaded messages from SQLite database.

    This service provides fast message lookups by case number, avoiding
    the need to load XLSX files or hit the Sprinklr bulk message API.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the message store.

        Args:
            db_path: Path to SQLite database file.
                    If None, will try to auto-discover.
        """
        self._conn: Optional[sqlite3.Connection] = None
        self._db_path: Optional[str] = None
        self._is_loaded = False

        if db_path:
            self.load(db_path)
        else:
            # Try auto-discover
            default_path = find_message_database()
            if default_path:
                self.load(default_path)

    def load(self, db_path: str) -> bool:
        """
        Load the SQLite database.

        Args:
            db_path: Path to SQLite database file

        Returns:
            True if loaded successfully
        """
        path = Path(db_path)
        if not path.exists():
            print(f"Warning: Message database not found: {db_path}")
            return False

        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._db_path = db_path
        self._is_loaded = True

        # Print stats
        stats = self.get_stats()
        print(f"Message store loaded: {stats['total_messages']:,} messages, {stats['unique_cases']:,} cases")

        return True

    def close(self):
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
            self._is_loaded = False

    @property
    def is_loaded(self) -> bool:
        """Check if the message store has been loaded."""
        return self._is_loaded

    def get_messages_for_case(self, case_number: int) -> List[Dict[str, Any]]:
        """
        Get all messages for a case, formatted for the ingestion pipeline.

        Args:
            case_number: The case number to look up

        Returns:
            List of message dictionaries sorted by created_time
        """
        if not self._is_loaded or not self._conn:
            return []

        cursor = self._conn.cursor()
        cursor.execute("""
            SELECT content, role, sender, created_time_epoch,
                   social_network, sentiment, language, message_type
            FROM messages
            WHERE case_number = ?
            ORDER BY created_time_epoch ASC
        """, (case_number,))

        messages = []
        for row in cursor.fetchall():
            messages.append({
                "role": row["role"] or "user",
                "content": row["content"] or "",
                "sender": row["sender"] or "Unknown",
                "created_time_epoch": row["created_time_epoch"],
                "social_network": row["social_network"] or "",
                "sentiment": row["sentiment"] or "",
                "language": row["language"] or "",
                "message_type": row["message_type"] or "",
            })

        return messages

    def has_messages_for_case(self, case_number: int) -> bool:
        """
        Check if messages exist for a case number.

        Args:
            case_number: The case number to check

        Returns:
            True if messages are available in the store
        """
        if not self._is_loaded or not self._conn:
            return False

        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT 1 FROM messages WHERE case_number = ? LIMIT 1",
            (case_number,)
        )
        return cursor.fetchone() is not None

    def get_message_count_for_case(self, case_number: int) -> int:
        """Get the number of messages for a case."""
        if not self._is_loaded or not self._conn:
            return 0

        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM messages WHERE case_number = ?",
            (case_number,)
        )
        return cursor.fetchone()[0]

    def get_case_metadata_from_messages(self, case_number: int) -> Dict[str, Any]:
        """
        Extract case-level metadata from the messages.

        Args:
            case_number: The case number

        Returns:
            Dictionary with aggregated metadata
        """
        if not self._is_loaded or not self._conn:
            return {}

        cursor = self._conn.cursor()

        # Get aggregated info
        cursor.execute("""
            SELECT
                COUNT(*) as msg_count,
                MAX(brand) as brand,
                MAX(social_network) as channel,
                MAX(language) as language
            FROM messages
            WHERE case_number = ?
        """, (case_number,))

        row = cursor.fetchone()
        if not row or row["msg_count"] == 0:
            return {}

        # Get most common sentiment
        cursor.execute("""
            SELECT sentiment, COUNT(*) as cnt
            FROM messages
            WHERE case_number = ? AND sentiment != ''
            GROUP BY sentiment
            ORDER BY cnt DESC
            LIMIT 1
        """, (case_number,))
        sentiment_row = cursor.fetchone()

        return {
            "brand": row["brand"] or "",
            "sentiment": sentiment_row["sentiment"] if sentiment_row else "",
            "language": row["language"] or "",
            "channel": row["channel"] or "",
            "message_count": row["msg_count"],
        }

    def get_available_case_numbers(self) -> List[int]:
        """
        Get all case numbers that have messages in the store.

        Returns:
            List of case numbers
        """
        if not self._is_loaded or not self._conn:
            return []

        cursor = self._conn.cursor()
        cursor.execute("SELECT DISTINCT case_number FROM messages ORDER BY case_number")
        return [row[0] for row in cursor.fetchall()]

    @property
    def message_count(self) -> int:
        """Total number of messages in the store."""
        if not self._is_loaded or not self._conn:
            return 0

        cursor = self._conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM messages")
        return cursor.fetchone()[0]

    @property
    def case_count(self) -> int:
        """Number of unique cases in the store."""
        if not self._is_loaded or not self._conn:
            return 0

        cursor = self._conn.cursor()
        cursor.execute("SELECT COUNT(DISTINCT case_number) FROM messages")
        return cursor.fetchone()[0]

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the message store.

        Returns:
            Dictionary with statistics
        """
        if not self._is_loaded or not self._conn:
            return {
                "loaded": False,
                "total_messages": 0,
                "unique_cases": 0,
            }

        cursor = self._conn.cursor()

        # Get from metadata table if available
        try:
            cursor.execute("SELECT key, value FROM metadata")
            metadata = {row[0]: row[1] for row in cursor.fetchall()}
            return {
                "loaded": True,
                "total_messages": int(metadata.get("total_messages", 0)),
                "unique_cases": int(metadata.get("unique_cases", 0)),
                "created_at": metadata.get("created_at", ""),
                "files_processed": int(metadata.get("files_processed", 0)),
                "db_path": self._db_path,
            }
        except sqlite3.OperationalError:
            # Metadata table doesn't exist, compute directly
            return {
                "loaded": True,
                "total_messages": self.message_count,
                "unique_cases": self.case_count,
                "db_path": self._db_path,
            }


# Default database path
DEFAULT_DB_PATH = "data/messages.db"


def find_message_database() -> Optional[str]:
    """
    Find the message database by checking common locations.

    Returns:
        Path to database or None if not found
    """
    # Check relative to current working directory
    cwd_path = Path.cwd() / DEFAULT_DB_PATH
    if cwd_path.exists():
        return str(cwd_path)

    # Check relative to this file's location
    src_path = Path(__file__).parent.parent.parent / DEFAULT_DB_PATH
    if src_path.exists():
        return str(src_path)

    return None


def find_xlsx_directory() -> Optional[str]:
    """
    Find the XLSX directory by checking common locations.
    Kept for backwards compatibility.

    Returns:
        Path to XLSX directory or None if not found
    """
    default_dir = "data_import"

    cwd_path = Path.cwd() / default_dir
    if cwd_path.exists():
        return str(cwd_path)

    src_path = Path(__file__).parent.parent.parent / default_dir
    if src_path.exists():
        return str(src_path)

    return None
