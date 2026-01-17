#!/usr/bin/env python3
"""
Resume ingestion script - waits for rate limit reset and continues ingestion.

Usage:
    python scripts/resume_ingestion.py --max-cases 100 --days 90
    python scripts/resume_ingestion.py --check-only  # Just check rate limit status
"""

import argparse
import sys
import time
from pathlib import Path
from datetime import datetime

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sprinklr_client import SprinklrClient, SprinklrAPIError
from ingestion import IngestionPipeline
from config import config


def check_rate_limit():
    """Check if the API rate limit has reset."""
    client = SprinklrClient()

    try:
        # Try a simple search to test if we're rate limited
        result = client.search_cases_v1(rows=1)
        total = result.get("totalHits", 0)
        print(f"API accessible! Total cases available: {total}")
        return True
    except SprinklrAPIError as e:
        if "403" in str(e):
            print("Still rate limited (Developer Over Rate)")
        else:
            print(f"API error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


def wait_for_rate_limit_reset(check_interval=60, max_wait=3600):
    """
    Wait for the rate limit to reset.

    Args:
        check_interval: Seconds between checks
        max_wait: Maximum seconds to wait

    Returns:
        True if rate limit reset, False if timed out
    """
    print(f"Waiting for rate limit to reset (checking every {check_interval}s)...")
    print(f"Maximum wait time: {max_wait // 60} minutes")
    print()

    start_time = time.time()
    attempts = 0

    while time.time() - start_time < max_wait:
        attempts += 1
        elapsed = int(time.time() - start_time)
        elapsed_min = elapsed // 60
        elapsed_sec = elapsed % 60

        print(f"[{elapsed_min:02d}:{elapsed_sec:02d}] Attempt {attempts}: Checking rate limit...")

        if check_rate_limit():
            print("\nRate limit has reset!")
            return True

        print(f"  Waiting {check_interval} seconds before next check...")
        time.sleep(check_interval)

    print(f"\nTimed out after {max_wait // 60} minutes")
    return False


def run_ingestion(days_back, max_cases, append=True):
    """Run the data ingestion."""
    print("\n" + "=" * 50)
    print("Starting data ingestion")
    print("=" * 50)
    print(f"Days back: {days_back}")
    print(f"Max cases: {max_cases}")
    print(f"Append mode: {append} (existing data {'kept' if append else 'cleared'})")
    print()

    pipeline = IngestionPipeline()

    # Show current stats
    current_count = pipeline.vector_store.get_case_count()
    print(f"Current cases in store: {current_count}")

    try:
        count = pipeline.ingest_live_data(
            days_back=days_back,
            max_cases=max_cases,
            clear_existing=not append
        )
        print(f"\nSuccess! Total cases now: {count}")
        return count
    except Exception as e:
        print(f"\nError during ingestion: {e}")
        return 0


def main():
    parser = argparse.ArgumentParser(
        description="Resume ingestion after rate limit reset"
    )

    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check rate limit status, don't wait or ingest"
    )

    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Don't wait for rate limit reset, just try once"
    )

    parser.add_argument(
        "--days",
        type=int,
        default=90,
        help="Days of historical data (default: 90)"
    )

    parser.add_argument(
        "--max-cases",
        type=int,
        default=100,
        help="Maximum cases to ingest (default: 100)"
    )

    parser.add_argument(
        "--append",
        action="store_true",
        default=True,
        help="Append to existing data (default: true)"
    )

    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing data before ingesting"
    )

    parser.add_argument(
        "--wait-interval",
        type=int,
        default=60,
        help="Seconds between rate limit checks (default: 60)"
    )

    parser.add_argument(
        "--max-wait",
        type=int,
        default=3600,
        help="Maximum seconds to wait for rate limit reset (default: 3600)"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Sprinklr Ingestion Resume Script")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Check-only mode
    if args.check_only:
        print("Checking rate limit status...")
        accessible = check_rate_limit()
        sys.exit(0 if accessible else 1)

    # Check if rate limit has reset
    if not check_rate_limit():
        if args.no_wait:
            print("API still rate limited. Use without --no-wait to wait for reset.")
            sys.exit(1)

        # Wait for rate limit reset
        if not wait_for_rate_limit_reset(args.wait_interval, args.max_wait):
            print("Could not access API within wait time. Try again later.")
            sys.exit(1)

    # Run ingestion
    count = run_ingestion(
        days_back=args.days,
        max_cases=args.max_cases,
        append=not args.clear
    )

    if count > 0:
        print("\n" + "=" * 50)
        print("Ingestion completed successfully!")
        print("=" * 50)
        print(f"You can now use the chatbot at http://localhost:8502")
        sys.exit(0)
    else:
        print("\nIngestion failed or no cases ingested")
        sys.exit(1)


if __name__ == "__main__":
    main()
