#!/usr/bin/env python3
"""Test the chatbot with the current data."""

import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from chatbot import create_chatbot

def main():
    print("Testing chatbot with existing data...")
    print("=" * 50)

    chatbot = create_chatbot()
    if not chatbot:
        print("ERROR: Could not create chatbot. Check ANTHROPIC_API_KEY.")
        return False

    # Check data stats
    case_count = chatbot.get_case_count()
    print(f"Cases in database: {case_count}")

    date_range = chatbot.get_date_range()
    print(f"Date range: {date_range[0]} to {date_range[1]}")

    brands = chatbot.get_available_brands()
    print(f"Brands: {brands}")

    if case_count == 0:
        print("No cases in database. Run ingestion first.")
        return False

    # Test a query
    print("\n" + "=" * 50)
    print("Testing query: 'What types of interactions do we have?'")
    print("=" * 50)

    response = chatbot.chat(
        message="What types of interactions do we have?",
        include_sources=True
    )

    print(f"\nResponse ({response['cases_found']} cases found):")
    print("-" * 50)
    response_text = response['response'][:500] + "..." if len(response['response']) > 500 else response['response']
    # Handle encoding for Windows console
    print(response_text.encode('ascii', 'replace').decode('ascii'))

    print("\n" + "=" * 50)
    print("Chatbot test completed successfully!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
