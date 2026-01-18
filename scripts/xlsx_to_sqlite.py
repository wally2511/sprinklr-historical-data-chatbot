#!/usr/bin/env python3
"""
Convert Sprinklr XLSX message exports to SQLite database.

One-time conversion script that creates a SQLite database for fast message lookups
during hybrid ingestion.

Usage:
    python scripts/xlsx_to_sqlite.py
    python scripts/xlsx_to_sqlite.py --xlsx-dir data_import/ --output data/messages.db
"""

import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import openpyxl

# Column mapping (1-based indices)
COLUMN_MAP = {
    "message": 6,
    "social_network": 1,
    "created_time": 7,
    "sender_screen_name": 3,
    "receiver_screen_name": 10,
    "message_type": 117,
    "conversation_id": 107,
    "profile_sprinklr_id": 81,
    "brand": 40,
    "sentiment": 16,
    "language": 23,
    "associated_cases": 109,
    "country": 111,
}


def parse_datetime(dt_value):
    """Parse datetime to epoch milliseconds."""
    if dt_value is None:
        return None

    if isinstance(dt_value, datetime):
        return int(dt_value.timestamp() * 1000)

    if isinstance(dt_value, (int, float)):
        if dt_value > 1_000_000_000_000:
            return int(dt_value)
        elif dt_value > 1_000_000_000:
            return int(dt_value * 1000)
        return None

    if isinstance(dt_value, str):
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
        ]
        for fmt in formats:
            try:
                dt = datetime.strptime(dt_value.strip(), fmt)
                return int(dt.timestamp() * 1000)
            except ValueError:
                continue
    return None


def safe_get(row, col_name):
    """Safely get a column value."""
    idx = COLUMN_MAP.get(col_name, 0)
    if idx > 0 and len(row) >= idx:
        val = row[idx - 1]
        return str(val).strip() if val else ""
    return ""


def create_database(db_path: str):
    """Create SQLite database with messages table."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create messages table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_number INTEGER NOT NULL,
            content TEXT,
            role TEXT,
            sender TEXT,
            created_time_epoch INTEGER,
            social_network TEXT,
            brand TEXT,
            sentiment TEXT,
            language TEXT,
            message_type TEXT,
            conversation_id TEXT,
            country TEXT
        )
    """)

    # Create index on case_number for fast lookups
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_case_number ON messages(case_number)
    """)

    # Create metadata table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    conn.commit()
    return conn


def process_xlsx_file(xlsx_path: Path, conn: sqlite3.Connection) -> int:
    """Process a single XLSX file and insert into database."""
    cursor = conn.cursor()

    wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
    ws = wb.active

    rows_inserted = 0
    batch = []
    batch_size = 1000

    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row or len(row) < COLUMN_MAP["associated_cases"]:
            continue

        # Get case number
        case_number_raw = row[COLUMN_MAP["associated_cases"] - 1]
        if not case_number_raw:
            continue

        try:
            case_number = int(str(case_number_raw).strip())
        except (ValueError, TypeError):
            continue

        # Get message content
        content = safe_get(row, "message")

        # Get message type and determine role
        message_type = safe_get(row, "message_type")
        is_sent = "sent" in message_type.lower() or "outbound" in message_type.lower()
        role = "agent" if is_sent else "user"

        # Get other fields
        sender = safe_get(row, "sender_screen_name") or "Unknown"
        created_time = parse_datetime(row[COLUMN_MAP["created_time"] - 1] if len(row) >= COLUMN_MAP["created_time"] else None)

        batch.append((
            case_number,
            content,
            role,
            sender,
            created_time,
            safe_get(row, "social_network"),
            safe_get(row, "brand"),
            safe_get(row, "sentiment"),
            safe_get(row, "language"),
            message_type,
            safe_get(row, "conversation_id"),
            safe_get(row, "country"),
        ))

        if len(batch) >= batch_size:
            cursor.executemany("""
                INSERT INTO messages (case_number, content, role, sender, created_time_epoch,
                    social_network, brand, sentiment, language, message_type, conversation_id, country)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, batch)
            rows_inserted += len(batch)
            batch = []

    # Insert remaining
    if batch:
        cursor.executemany("""
            INSERT INTO messages (case_number, content, role, sender, created_time_epoch,
                social_network, brand, sentiment, language, message_type, conversation_id, country)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, batch)
        rows_inserted += len(batch)

    conn.commit()
    wb.close()

    return rows_inserted


def main():
    parser = argparse.ArgumentParser(description="Convert XLSX files to SQLite database")

    parser.add_argument(
        "--xlsx-dir",
        type=str,
        default="data_import",
        help="Directory containing XLSX files (default: data_import)"
    )

    parser.add_argument(
        "--output",
        type=str,
        default="data/messages.db",
        help="Output SQLite database path (default: data/messages.db)"
    )

    args = parser.parse_args()

    # Find XLSX directory
    xlsx_dir = Path(args.xlsx_dir)
    if not xlsx_dir.exists():
        # Try relative to script
        xlsx_dir = Path(__file__).parent.parent / args.xlsx_dir

    if not xlsx_dir.exists():
        print(f"Error: XLSX directory not found: {args.xlsx_dir}")
        sys.exit(1)

    # Find all XLSX files
    xlsx_files = list(xlsx_dir.rglob("*.xlsx"))
    if not xlsx_files:
        print(f"Error: No XLSX files found in {xlsx_dir}")
        sys.exit(1)

    print(f"Found {len(xlsx_files)} XLSX files in {xlsx_dir}")

    # Create output directory
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Remove existing database
    if output_path.exists():
        output_path.unlink()
        print(f"Removed existing database: {output_path}")

    # Create database
    print(f"Creating database: {output_path}")
    conn = create_database(str(output_path))

    # Process each file
    total_messages = 0
    for i, xlsx_file in enumerate(xlsx_files, 1):
        print(f"[{i}/{len(xlsx_files)}] Processing {xlsx_file.name}...", end=" ", flush=True)
        count = process_xlsx_file(xlsx_file, conn)
        total_messages += count
        print(f"{count:,} messages")

    # Store metadata
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
                   ("total_messages", str(total_messages)))
    cursor.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
                   ("created_at", datetime.now().isoformat()))
    cursor.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
                   ("files_processed", str(len(xlsx_files))))

    # Get unique case count
    cursor.execute("SELECT COUNT(DISTINCT case_number) FROM messages")
    unique_cases = cursor.fetchone()[0]
    cursor.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
                   ("unique_cases", str(unique_cases)))

    conn.commit()

    # Print summary
    print(f"\n=== Conversion Complete ===")
    print(f"Total messages: {total_messages:,}")
    print(f"Unique cases: {unique_cases:,}")
    print(f"Database size: {output_path.stat().st_size / 1024 / 1024:.1f} MB")
    print(f"Output: {output_path}")

    conn.close()


if __name__ == "__main__":
    main()
