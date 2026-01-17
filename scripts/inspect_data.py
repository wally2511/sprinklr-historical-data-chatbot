#!/usr/bin/env python3
"""Inspect ingested data to verify summaries and full transcripts."""

import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from vector_store import VectorStore

def main():
    print("Inspecting Ingested Data")
    print("=" * 60)

    vs = VectorStore()
    count = vs.get_case_count()
    print(f"\nTotal cases in database: {count}")

    if count == 0:
        print("No data to inspect!")
        return

    # Get a sample of cases
    print("\n" + "=" * 60)
    print("SAMPLE CASES (showing first 3 with conversations)")
    print("=" * 60)

    # Search for cases with conversation content
    results = vs.search("conversation message", n_results=10)

    cases_shown = 0
    for case in results:
        metadata = case.get("metadata", {})
        full_conv = metadata.get("full_conversation", "")

        # Skip cases without conversation
        if not full_conv or len(full_conv) < 50:
            continue

        cases_shown += 1
        if cases_shown > 3:
            break

        print(f"\n{'-' * 60}")
        print(f"CASE #{cases_shown}")
        print(f"{'-' * 60}")
        print(f"ID: {case.get('id', 'N/A')}")
        print(f"Case Number: {metadata.get('case_number', 'N/A')}")
        print(f"Brand: {metadata.get('brand', 'N/A')}")
        print(f"Channel: {metadata.get('channel', 'N/A')}")
        print(f"Created: {metadata.get('created_at', 'N/A')}")
        print(f"Message Count: {metadata.get('message_count', 0)}")

        print(f"\n--- SUMMARY ---")
        summary = case.get("summary", "No summary")
        # Handle encoding for Windows
        summary_safe = summary.encode('ascii', 'replace').decode('ascii') if summary else "No summary"
        print(summary_safe[:500] + "..." if len(summary_safe) > 500 else summary_safe)

        print(f"\n--- FULL CONVERSATION ---")
        conv_safe = full_conv.encode('ascii', 'replace').decode('ascii') if full_conv else "No conversation"
        print(conv_safe[:1000] + "..." if len(conv_safe) > 1000 else conv_safe)

        # Check for both USER and AGENT messages
        has_user = "USER" in full_conv.upper()
        has_agent = "AGENT" in full_conv.upper()
        print(f"\n--- MESSAGE TYPES ---")
        print(f"Contains USER messages: {has_user}")
        print(f"Contains AGENT messages: {has_agent}")

    # Statistics on message types
    print("\n" + "=" * 60)
    print("MESSAGE TYPE STATISTICS")
    print("=" * 60)

    all_results = vs.search("", n_results=min(100, count))

    cases_with_conversation = 0
    cases_with_user_msgs = 0
    cases_with_agent_msgs = 0
    cases_with_both = 0
    total_message_count = 0

    for case in all_results:
        metadata = case.get("metadata", {})
        full_conv = metadata.get("full_conversation", "")
        msg_count = metadata.get("message_count", 0)
        total_message_count += msg_count

        if full_conv and len(full_conv) > 10:
            cases_with_conversation += 1
            has_user = "USER" in full_conv.upper()
            has_agent = "AGENT" in full_conv.upper()

            if has_user:
                cases_with_user_msgs += 1
            if has_agent:
                cases_with_agent_msgs += 1
            if has_user and has_agent:
                cases_with_both += 1

    print(f"\nOut of {len(all_results)} cases sampled:")
    print(f"  - Cases with conversation text: {cases_with_conversation}")
    print(f"  - Cases with USER messages: {cases_with_user_msgs}")
    print(f"  - Cases with AGENT messages: {cases_with_agent_msgs}")
    print(f"  - Cases with BOTH user & agent: {cases_with_both}")
    print(f"  - Total message count: {total_message_count}")

    # Check summary quality
    print("\n" + "=" * 60)
    print("SUMMARY QUALITY CHECK")
    print("=" * 60)

    cases_with_ai_summary = 0
    cases_with_fallback_summary = 0

    for case in all_results:
        summary = case.get("summary", "")
        if summary:
            # AI summaries typically don't start with "This is a" or "User asked:"
            if summary.startswith("User asked:") or summary.startswith("This is a"):
                cases_with_fallback_summary += 1
            else:
                cases_with_ai_summary += 1

    print(f"  - Cases with AI-generated summary: {cases_with_ai_summary}")
    print(f"  - Cases with fallback summary: {cases_with_fallback_summary}")

    print("\n" + "=" * 60)
    print("INSPECTION COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()
