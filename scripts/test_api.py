#!/usr/bin/env python3
"""Quick API test to check if rate limit has reset."""

import sys
from pathlib import Path
import requests

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sprinklr_client import SprinklrClient, SprinklrAPIError, RateLimitError
from config import config

def test_v1_api(client):
    """Test v1 search API."""
    print("\n--- Testing v1 Case Search API ---")
    try:
        result = client.search_cases_v1(rows=1)
        total = result.get("totalHits", 0)
        print(f"SUCCESS! v1 API accessible. Total cases: {total}")
        return True
    except Exception as e:
        print(f"v1 API ERROR: {e}")
        return False

def test_v2_api(client):
    """Test v2 search API."""
    print("\n--- Testing v2 Search by Entity API ---")
    try:
        result = client.search_cases_v2(start=0, size=1)
        total = result.get("totalCount", 0)
        cases = result.get("data", [])
        print(f"SUCCESS! v2 API accessible. Total cases: {total}, returned: {len(cases)}")
        return True
    except Exception as e:
        print(f"v2 API ERROR: {e}")
        return False

def test_raw_request():
    """Make a raw request to see exact error response."""
    print("\n--- Raw API Test ---")
    base_url = config.get_sprinklr_base_url().replace("api2.sprinklr.com", "api3.sprinklr.com")
    url = f"{base_url}/api/v1/case/search"

    headers = {
        "Authorization": f"Bearer {config.SPRINKLR_ACCESS_TOKEN}",
        "Key": config.SPRINKLR_API_KEY,
        "Content-Type": "application/json",
    }

    body = {
        "query": "",
        "paginationInfo": {"start": 0, "rows": 1}
    }

    try:
        response = requests.post(url, headers=headers, json=body, timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        return response.status_code == 200
    except Exception as e:
        print(f"Request error: {e}")
        return False

def main():
    client = SprinklrClient()
    print("Testing Sprinklr API connection...")
    print(f"Base URL: {client.base_url}")
    print(f"API Key configured: {bool(config.SPRINKLR_API_KEY)}")
    print(f"Access Token configured: {bool(config.SPRINKLR_ACCESS_TOKEN)}")

    # Test raw request first to see exact error
    test_raw_request()

    # Test both APIs
    v1_ok = test_v1_api(client)
    v2_ok = test_v2_api(client)

    if v1_ok or v2_ok:
        print("\n==> At least one API is accessible!")
        return True
    else:
        print("\n==> Both APIs failed. May still be rate limited.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
