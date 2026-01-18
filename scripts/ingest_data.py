#!/usr/bin/env python3
"""
CLI script for ingesting data into the Sprinklr chatbot.

Usage:
    # Ingest mock data (default)
    python scripts/ingest_data.py

    # Ingest with custom number of cases
    python scripts/ingest_data.py --cases 100 --days 60

    # Ingest live data from Sprinklr
    python scripts/ingest_data.py --live --days 30

    # Hybrid ingestion: API cases + XLSX messages (no message rate limits)
    python scripts/ingest_data.py --live --xlsx-messages --max-cases 1000

    # Hybrid with specific XLSX directory
    python scripts/ingest_data.py --live --xlsx-dir data_import/ --max-cases 1000

    # Append to existing data (don't clear)
    python scripts/ingest_data.py --no-clear
"""

import argparse
import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ingestion import IngestionPipeline
from config import config


def main():
    """Main entry point for the ingestion script."""
    parser = argparse.ArgumentParser(
        description="Ingest data into the Sprinklr chatbot vector store"
    )

    parser.add_argument(
        "--live",
        action="store_true",
        help="Use live Sprinklr API data instead of mock data"
    )

    parser.add_argument(
        "--cases",
        type=int,
        default=50,
        help="Number of mock cases to generate (default: 50, ignored with --live)"
    )

    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days of historical data (default: 30)"
    )

    parser.add_argument(
        "--max-cases",
        type=int,
        default=None,
        help="Maximum number of live cases to fetch (default: unlimited)"
    )

    parser.add_argument(
        "--no-clear",
        action="store_true",
        help="Don't clear existing data before ingesting"
    )

    parser.add_argument(
        "--stats",
        action="store_true",
        help="Just show stats about existing data"
    )

    parser.add_argument(
        "--xlsx-messages",
        action="store_true",
        help="Use SQLite message database for message content (hybrid mode)"
    )

    parser.add_argument(
        "--db-path",
        type=str,
        default=None,
        help="Path to SQLite message database (default: auto-discover data/messages.db)"
    )

    parser.add_argument(
        "--skip-api-fallback",
        action="store_true",
        help="Skip cases not found in message DB instead of fetching from API"
    )

    args = parser.parse_args()

    # Initialize pipeline
    print("Initializing ingestion pipeline...")
    pipeline = IngestionPipeline()

    # Show stats only
    if args.stats:
        stats = pipeline.get_stats()
        print("\n=== Data Statistics ===")
        print(f"Total cases: {stats['total_cases']}")
        print(f"Themes: {', '.join(stats['themes']) if stats['themes'] else 'None'}")
        if stats['date_range']['start']:
            print(f"Date range: {stats['date_range']['start'][:10]} to {stats['date_range']['end'][:10]}")
        else:
            print("Date range: No data")
        return

    # Check configuration
    if args.live:
        if not config.validate_sprinklr_config():
            print("Error: Sprinklr API credentials not configured.")
            print("Please set SPRINKLR_API_KEY and SPRINKLR_ACCESS_TOKEN in .env")
            sys.exit(1)

        # Use hybrid mode if xlsx flags are provided
        use_hybrid = args.xlsx_messages or args.db_path is not None

        if use_hybrid:
            print(f"\nIngesting with HYBRID mode (API cases + SQLite messages)...")
            print(f"  - Message DB: {args.db_path or 'auto-discover'}")
            print(f"  - Days back: {args.days}")
            print(f"  - Max cases: {args.max_cases or 'unlimited'}")
            print(f"  - Skip API fallback: {args.skip_api_fallback}")
            print(f"  - Clear existing: {not args.no_clear}")
            print()

            try:
                count = pipeline.ingest_hybrid(
                    db_path=args.db_path,
                    days_back=args.days,
                    max_cases=args.max_cases,
                    clear_existing=not args.no_clear,
                    skip_api_fallback=args.skip_api_fallback
                )
                print(f"\nSuccess! Ingested {count} cases using hybrid mode.")

            except FileNotFoundError as e:
                print(f"\nError: {e}")
                print("Hint: Run 'python scripts/xlsx_to_sqlite.py' first to create the message database.")
                sys.exit(1)
            except Exception as e:
                print(f"\nError during ingestion: {e}")
                sys.exit(1)
        else:
            print(f"\nIngesting live data from Sprinklr...")
            print(f"  - Days back: {args.days}")
            print(f"  - Max cases: {args.max_cases or 'unlimited'}")
            print(f"  - Clear existing: {not args.no_clear}")
            print()

            try:
                count = pipeline.ingest_live_data(
                    days_back=args.days,
                    max_cases=args.max_cases,
                    clear_existing=not args.no_clear
                )
                print(f"\nSuccess! Ingested {count} cases from Sprinklr.")

            except Exception as e:
                print(f"\nError during ingestion: {e}")
                sys.exit(1)

    else:
        print(f"\nIngesting mock data...")
        print(f"  - Number of cases: {args.cases}")
        print(f"  - Days back: {args.days}")
        print(f"  - Clear existing: {not args.no_clear}")
        print()

        try:
            count = pipeline.ingest_mock_data(
                num_cases=args.cases,
                days_back=args.days,
                clear_existing=not args.no_clear
            )
            print(f"\nSuccess! Ingested {count} mock cases.")

        except Exception as e:
            print(f"\nError during ingestion: {e}")
            sys.exit(1)

    # Show final stats
    print("\n=== Final Statistics ===")
    stats = pipeline.get_stats()
    print(f"Total cases in store: {stats['total_cases']}")
    print(f"Themes: {', '.join(stats['themes']) if stats['themes'] else 'None'}")
    if stats['date_range']['start']:
        print(f"Date range: {stats['date_range']['start'][:10]} to {stats['date_range']['end'][:10]}")


if __name__ == "__main__":
    main()
