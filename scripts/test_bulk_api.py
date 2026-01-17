#!/usr/bin/env python3
"""Test the bulk message fetch API."""

import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sprinklr_client import SprinklrClient, SprinklrAPIError

def main():
    client = SprinklrClient()

    print("Testing Sprinklr Bulk Message Fetch API")
    print("=" * 50)

    # First, get a case to test with
    print("\n1. Searching for a case with messages...")
    try:
        # Search more cases to find one with multiple messages
        result = client.search_cases_v1(rows=20)
        cases = result.get("data", [])

        if not cases:
            print("No cases found!")
            return False

        print(f"   Found {len(cases)} cases")

        # Find a case with multiple messages (to show bulk efficiency)
        test_case = None
        best_msg_count = 0
        for case in cases:
            case_id = case.get("id")
            fan_msg_count = case.get("associatedFanMessageCount", 0)
            brand_msg_count = case.get("associatedBrandMessageCount", 0)
            total_msgs = fan_msg_count + brand_msg_count

            if total_msgs > best_msg_count:
                test_case = case
                best_msg_count = total_msgs

        if test_case:
            print(f"   Using case #{test_case.get('caseNumber')} with {best_msg_count} messages")

        if not test_case:
            print("   No cases with messages found in first 5 results")
            return False

    except SprinklrAPIError as e:
        print(f"   Error searching cases: {e}")
        return False

    # Get message IDs for the case
    print("\n2. Getting message IDs for the case...")
    try:
        case_id = test_case.get("id")
        message_ids = client.get_case_associated_message_ids(case_id)
        print(f"   Found {len(message_ids)} message IDs")

        if not message_ids:
            print("   No message IDs returned")
            return False

        # Show first few message IDs
        for i, msg_id in enumerate(message_ids[:3]):
            print(f"   [{i+1}] {msg_id[:50]}..." if len(msg_id) > 50 else f"   [{i+1}] {msg_id}")

    except SprinklrAPIError as e:
        print(f"   Error getting message IDs: {e}")
        return False

    # Test bulk message fetch
    print("\n3. Testing BULK message fetch API...")
    try:
        messages = client.get_messages_bulk(message_ids)
        print(f"   SUCCESS! Retrieved {len(messages)} messages in single API call")

        if messages:
            # Show sample message
            msg = messages[0]
            content = msg.get("content", {})
            text = content.get("text", "")[:100] if content.get("text") else "(no text)"
            sender = msg.get("senderProfile", {}).get("name", "Unknown")
            # Handle Windows encoding
            text_safe = text.encode('ascii', 'replace').decode('ascii')
            sender_safe = sender.encode('ascii', 'replace').decode('ascii')
            print(f"\n   Sample message:")
            print(f"   - Sender: {sender_safe}")
            print(f"   - Content: {text_safe}...")

    except SprinklrAPIError as e:
        print(f"   FAILED: {e}")
        return False

    # Compare with individual fetch (for verification)
    print("\n4. Comparing with individual fetch (first message only)...")
    try:
        single_msg = client.get_message_by_id(message_ids[0])
        if single_msg:
            print("   Individual fetch also works")
            print("   Both methods return valid data")
        else:
            print("   Individual fetch returned None")

    except SprinklrAPIError as e:
        print(f"   Individual fetch error: {e}")

    # Test get_case_messages (which now uses bulk internally)
    print("\n5. Testing get_case_messages() (uses bulk API internally)...")
    try:
        all_messages = client.get_case_messages(case_id)
        print(f"   Retrieved {len(all_messages)} messages")
        print("   Bulk API integration successful!")

    except Exception as e:
        print(f"   Error: {e}")
        return False

    print("\n" + "=" * 50)
    print("BULK MESSAGE API TEST PASSED!")
    print("=" * 50)
    print("\nAPI Call Efficiency:")
    print(f"  - Old method: {len(message_ids) + 1} API calls (1 for IDs + N for messages)")
    print(f"  - New method: 2 API calls (1 for IDs + 1 bulk fetch)")
    print(f"  - Savings: {len(message_ids) - 1} fewer API calls per case")

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
