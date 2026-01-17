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

    # Append to existing data (don't clear)
    python scripts/ingest_data.py --no-clear
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion import IngestionPipeline
from src.config import config


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
