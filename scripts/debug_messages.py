#!/usr/bin/env python3
"""Debug message format from Sprinklr API."""

import sys
import json
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sprinklr_client import SprinklrClient, SprinklrAPIError

def main():
    client = SprinklrClient()

    print("Debugging Sprinklr Message Format")
    print("=" * 60)

    # Search for cases with messages
    print("\n1. Finding a case with BRAND messages...")
    try:
        # Search more cases to find one with brand messages
        result = client.search_cases_v1(rows=100)
        cases = result.get("data", [])

        # First, show stats on brand vs fan messages
        total_fan = sum(c.get("associatedFanMessageCount", 0) for c in cases)
        total_brand = sum(c.get("associatedBrandMessageCount", 0) for c in cases)
        print(f"   Searched {len(cases)} cases")
        print(f"   Total fan messages across all: {total_fan}")
        print(f"   Total brand messages across all: {total_brand}")

        # Find case with BRAND messages (to see agent message format)
        best_case = None
        best_brand_count = 0
        for case in cases:
            fan_count = case.get("associatedFanMessageCount", 0)
            brand_count = case.get("associatedBrandMessageCount", 0)
            # Prefer cases with brand messages
            if brand_count > best_brand_count:
                best_case = case
                best_brand_count = brand_count
            elif brand_count == best_brand_count and (fan_count + brand_count) > 0:
                if not best_case:
                    best_case = case

        if not best_case:
            print("No cases with messages found!")
            return

        case_id = best_case.get("id")
        case_num = best_case.get("caseNumber")
        fan_count = best_case.get("associatedFanMessageCount", 0)
        brand_count = best_case.get("associatedBrandMessageCount", 0)

        print(f"   Found case #{case_num}")
        print(f"   Fan messages: {fan_count}")
        print(f"   Brand messages: {brand_count}")
        print(f"   Total: {fan_count + brand_count}")

    except SprinklrAPIError as e:
        print(f"Error: {e}")
        return

    # Get message IDs
    print(f"\n2. Getting message IDs for case {case_id}...")
    try:
        message_ids = client.get_case_associated_message_ids(case_id)
        print(f"   Found {len(message_ids)} message IDs")
    except SprinklrAPIError as e:
        print(f"Error: {e}")
        return

    # Get messages - try bulk first, then individual if needed
    print(f"\n3. Fetching messages...")
    messages = []

    # Try bulk first (may fail for large batches)
    if len(message_ids) <= 50:
        messages = client.get_messages_bulk(message_ids)
        print(f"   Bulk fetch: {len(messages)} messages")
    else:
        print(f"   Too many messages ({len(message_ids)}) for bulk, fetching first 10 individually...")
        for msg_id in message_ids[:10]:
            msg = client.get_message_by_id(msg_id)
            if msg:
                messages.append(msg)
        print(f"   Retrieved {len(messages)} messages individually")

    # Analyze message structure
    print("\n" + "=" * 60)
    print("RAW MESSAGE ANALYSIS")
    print("=" * 60)

    for i, msg in enumerate(messages[:5]):  # Show first 5
        print(f"\n--- Message {i+1} ---")

        # Key fields for role detection
        sender_type = msg.get("senderType")
        brand_post = msg.get("brandPost")
        sender_profile = msg.get("senderProfile", {})
        sender_name = sender_profile.get("name", "Unknown")

        # Content
        content = msg.get("content", {})
        text = content.get("text", "")[:100] if content.get("text") else "(no text)"

        print(f"senderType: {sender_type}")
        print(f"brandPost: {brand_post}")
        print(f"senderProfile.name: {sender_name}")

        # Check all top-level keys
        print(f"\nAll top-level keys: {list(msg.keys())}")

        # Print content safely
        text_safe = text.encode('ascii', 'replace').decode('ascii')
        print(f"Content: {text_safe}...")

    # Summary of role indicators
    print("\n" + "=" * 60)
    print("ROLE INDICATOR SUMMARY")
    print("=" * 60)

    sender_types = {}
    brand_posts = {"True": 0, "False": 0, "None": 0}

    for msg in messages:
        st = msg.get("senderType", "None")
        sender_types[st] = sender_types.get(st, 0) + 1

        bp = msg.get("brandPost")
        if bp is True:
            brand_posts["True"] += 1
        elif bp is False:
            brand_posts["False"] += 1
        else:
            brand_posts["None"] += 1

    print(f"\nsenderType values:")
    for k, v in sender_types.items():
        print(f"  {k}: {v}")

    print(f"\nbrandPost values:")
    for k, v in brand_posts.items():
        print(f"  {k}: {v}")

    # Recommendation
    print("\n" + "=" * 60)
    print("RECOMMENDATION")
    print("=" * 60)
    print("\nBased on the API response, update role detection to use:")
    print("  - brandPost=True -> AGENT/BRAND role")
    print("  - brandPost=False -> USER role")

if __name__ == "__main__":
    main()
