"""
Sprinklr API client for fetching case and message data.

Implements OAuth authentication, rate limiting, and case/message retrieval.
"""

import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Generator
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import config


class RateLimiter:
    """Simple rate limiter for API calls."""

    def __init__(self, calls_per_second: int = 10, calls_per_hour: int = 1000):
        self.calls_per_second = calls_per_second
        self.calls_per_hour = calls_per_hour
        self.second_calls: List[float] = []
        self.hour_calls: List[float] = []

    def wait_if_needed(self) -> None:
        """Wait if rate limits would be exceeded."""
        now = time.time()

        # Clean old entries
        self.second_calls = [t for t in self.second_calls if now - t < 1.0]
        self.hour_calls = [t for t in self.hour_calls if now - t < 3600.0]

        # Check second limit
        if len(self.second_calls) >= self.calls_per_second:
            sleep_time = 1.0 - (now - self.second_calls[0])
            if sleep_time > 0:
                time.sleep(sleep_time)

        # Check hour limit
        if len(self.hour_calls) >= self.calls_per_hour:
            sleep_time = 3600.0 - (now - self.hour_calls[0])
            if sleep_time > 0:
                print(f"Rate limit reached. Waiting {sleep_time:.0f} seconds...")
                time.sleep(sleep_time)

        # Record this call
        now = time.time()
        self.second_calls.append(now)
        self.hour_calls.append(now)


class SprinklrClient:
    """Client for interacting with the Sprinklr API."""

    def __init__(self):
        """Initialize the Sprinklr API client."""
        self.base_url = config.get_sprinklr_base_url()
        self.api_key = config.SPRINKLR_API_KEY
        self.access_token = config.SPRINKLR_ACCESS_TOKEN
        self.rate_limiter = RateLimiter(
            calls_per_second=config.RATE_LIMIT_CALLS_PER_SECOND,
            calls_per_hour=config.RATE_LIMIT_CALLS_PER_HOUR
        )

        # Setup session with retries
        self.session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retries))

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make an API request with rate limiting and error handling.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            json_data: JSON body data

        Returns:
            Response data as dictionary
        """
        self.rate_limiter.wait_if_needed()

        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()

        try:
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_data,
                timeout=30
            )

            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise AuthenticationError("Invalid or expired access token")
            elif e.response.status_code == 403:
                raise AuthorizationError("Insufficient permissions")
            elif e.response.status_code == 429:
                raise RateLimitError("Rate limit exceeded")
            else:
                raise SprinklrAPIError(f"API error: {e}")

        except requests.exceptions.RequestException as e:
            raise SprinklrAPIError(f"Request failed: {e}")

    def get_case(self, case_id: str) -> Dict[str, Any]:
        """
        Fetch a single case by ID.

        Args:
            case_id: The case ID to fetch

        Returns:
            Case data dictionary
        """
        return self._make_request("GET", f"/api/v2/case/{case_id}")

    def search_cases_v2(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        start: int = 0,
        size: int = 100
    ) -> Dict[str, Any]:
        """
        Search for cases using Sprinklr v2 search API with proper pagination.

        Uses POST /api/v2/search/CASE endpoint on api3.sprinklr.com.
        Supports date filtering, pagination with start/size, and total count.

        Args:
            start_date: Filter cases created after this date
            end_date: Filter cases created before this date
            start: Pagination offset (default 0)
            size: Number of results per page (default 100)

        Returns:
            Search results with cases, cursor, and total count
        """
        # v2 search uses api3.sprinklr.com
        v2_base_url = self.base_url.replace("api2.sprinklr.com", "api3.sprinklr.com")

        # Build request body according to documentation
        # Note: page is lowercase and start is 1-indexed
        body = {
            "filter": {
                "type": "EQUALS",
                "key": "deleted",
                "values": [False]
            },
            "page": {
                "start": start + 1,  # 1-indexed
                "size": size
            },
            "includeCount": True
        }

        # Add time filter if dates specified (yyyy-MM format)
        if start_date or end_date:
            body["timeFilter"] = {
                "key": "createdTime"
            }
            if start_date:
                body["timeFilter"]["since"] = start_date.strftime("%Y-%m")
            if end_date:
                body["timeFilter"]["until"] = end_date.strftime("%Y-%m")

        # Make request
        url = f"{v2_base_url}/api/v2/search/CASE"
        headers = self._get_headers()

        try:
            self.rate_limiter.wait_if_needed()
            response = self.session.request(
                method="POST",
                url=url,
                headers=headers,
                json=body,
                timeout=30
            )
            response.raise_for_status()
            resp_data = response.json()

            # Extract data from response
            data = resp_data.get("data", {})
            results = data.get("results", [])
            cursor = data.get("cursor")
            total_count = data.get("totalCount", 0)

            return {
                "data": results,
                "cursor": cursor,
                "totalCount": total_count,
                "errors": resp_data.get("errors", [])
            }

        except requests.exceptions.HTTPError as e:
            raise SprinklrAPIError(f"API error: {e}")
        except requests.exceptions.RequestException as e:
            raise SprinklrAPIError(f"Request failed: {e}")

    def search_cases_v1(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        start: int = 0,
        rows: int = 100,
        query: str = ""
    ) -> Dict[str, Any]:
        """
        Search for cases using Sprinklr v1 search API.

        This endpoint supports proper pagination and date filtering.
        Uses api3.sprinklr.com instead of api2.

        Args:
            start_date: Filter cases created after this date
            end_date: Filter cases created before this date
            start: Pagination offset (default 0)
            rows: Number of results per page (default 100)
            query: Search keywords (default empty for all)

        Returns:
            Search results with cases and pagination info
        """
        # v1 search uses api3.sprinklr.com
        v1_base_url = self.base_url.replace("api2.sprinklr.com", "api3.sprinklr.com")

        # Build request body
        body = {
            "query": query,
            "filters": [
                {
                    "filterType": "IN",
                    "field": "channelType",
                    "values": ["SPRINKLR"]
                }
            ],
            "paginationInfo": {
                "start": start,
                "rows": rows,
                "sortKey": "caseModificationTime"
            }
        }

        # Add date filters if specified
        if start_date:
            body["paginationInfo"]["sinceDate"] = int(start_date.timestamp() * 1000)
        if end_date:
            body["paginationInfo"]["untilDate"] = int(end_date.timestamp() * 1000)

        # Make direct request to v1 endpoint
        url = f"{v1_base_url}/api/v1/case/search"
        headers = self._get_headers()

        try:
            response = self.session.request(
                method="POST",
                url=url,
                headers=headers,
                json=body,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            # Extract cases from v1 response format
            search_results = data.get("searchResults", [])
            cases = []
            for result in search_results:
                case_dto = result.get("universalCaseApiDTO", {})
                if case_dto:
                    # Convert v1 format to match v2 format
                    cases.append({
                        "id": case_dto.get("id"),
                        "caseNumber": case_dto.get("caseNumber"),
                        "subject": case_dto.get("subject", ""),
                        "description": case_dto.get("description", ""),
                        "status": case_dto.get("status", ""),
                        "createdTime": case_dto.get("caseCreationTime"),
                        "modifiedTime": case_dto.get("caseModificationTime"),
                        "associatedFanMessageCount": case_dto.get("associatedFanMessageCount", 0),
                        "associatedBrandMessageCount": case_dto.get("associatedBrandMessageCount", 0),
                        "sentiment": case_dto.get("sentiment", {}).get("value", 0),
                        "workflow": {
                            "customProperties": case_dto.get("universalCaseWorkflow", {}).get("cProp", {})
                        },
                        "contact": {
                            "channelType": case_dto.get("fromUserSocialNetwork", ""),
                            "name": result.get("profile", {}).get("name", ""),
                        }
                    })

            return {
                "data": cases,
                "totalHits": data.get("totalHits", 0),
                "hasMore": data.get("hasMore", False),
                "timeBasedCursor": data.get("timeBasedCursor"),
                "errors": []
            }

        except requests.exceptions.HTTPError as e:
            raise SprinklrAPIError(f"API error: {e}")
        except requests.exceptions.RequestException as e:
            raise SprinklrAPIError(f"Request failed: {e}")

    def search_cases(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[str] = None,
        brand: Optional[str] = None,
        page_size: int = 50,
        cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search for cases with filters using Sprinklr v2 search API.

        Note: This endpoint has pagination issues. For better results,
        use search_cases_v1() instead.

        Args:
            start_date: Filter cases created after this date (post-query filter)
            end_date: Filter cases created before this date (post-query filter)
            status: Filter by case status
            brand: Filter by brand name (custom property)
            page_size: Number of results per page
            cursor: Cursor for pagination (from previous response)

        Returns:
            Search results with cases and pagination info
        """
        # Build endpoint - cursor is passed as URL query param with POST + empty body
        # Cursor format from Sprinklr is already "id=xyz", so extract just the value
        if cursor:
            # Remove "id=" prefix if present to normalize, then add it back
            cursor_value = cursor.replace("id=", "") if cursor.startswith("id=") else cursor
            endpoint = f"/api/v2/search/CASE?id={cursor_value}"
        else:
            endpoint = "/api/v2/search/CASE"

        # Always use POST with empty body - works for both initial and paginated requests
        response = self._make_request("POST", endpoint, json_data={})

        # Transform response to normalized format
        # Response is: {"data": {"results": [...], "cursor": "..."}, "errors": []}
        data = response.get("data", {})
        results = data.get("results", [])

        # Apply post-query date filtering if specified
        if start_date or end_date:
            start_ts = int(start_date.timestamp() * 1000) if start_date else 0
            end_ts = int(end_date.timestamp() * 1000) if end_date else float('inf')

            filtered_results = []
            for case in results:
                created_time = case.get("createdTime", 0)
                if start_ts <= created_time <= end_ts:
                    filtered_results.append(case)
            results = filtered_results

        return {
            "data": results,
            "cursor": data.get("cursor"),
            "errors": response.get("errors", [])
        }

    def get_case_associated_message_ids(self, case_id: str) -> List[str]:
        """
        Fetch all message IDs associated with a case.

        Uses the correct Sprinklr API endpoint:
        GET /api/v2/case/associated-messages?id={case_id}

        Args:
            case_id: The case ID

        Returns:
            List of message ID strings
        """
        response = self._make_request(
            "GET",
            f"/api/v2/case/associated-messages?id={case_id}"
        )
        return response.get("data", [])

    def get_message_by_id(self, message_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a single message by its ID.

        Uses the correct Sprinklr API endpoint:
        GET /api/v2/message/byMessageId?messageId={message_id}

        Note: For fetching multiple messages, use get_messages_bulk() instead
        for better efficiency.

        Args:
            message_id: The message ID

        Returns:
            Message dictionary or None if not found
        """
        try:
            response = self._make_request(
                "GET",
                f"/api/v2/message/byMessageId?messageId={message_id}"
            )
            return response.get("data")
        except SprinklrAPIError:
            return None

    def get_messages_bulk(self, message_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Fetch multiple messages in bulk using a single API call.

        Uses the Sprinklr bulk message fetch API:
        POST /api/v2/message/bulk-fetch

        This is more efficient than fetching messages individually,
        reducing API calls from N to 1 for N messages.

        Args:
            message_ids: List of message ID strings

        Returns:
            List of message dictionaries
        """
        if not message_ids:
            return []

        try:
            response = self._make_request(
                "POST",
                "/api/v2/message/bulk-fetch",
                json_data=message_ids
            )
            return response.get("data", [])
        except SprinklrAPIError as e:
            print(f"Warning: Bulk message fetch failed: {e}")
            return []

    def get_case_messages(self, case_id: str) -> List[Dict[str, Any]]:
        """
        Fetch all messages for a case using bulk message API.

        First gets message IDs associated with the case, then fetches
        all messages in a single bulk API call for efficiency.

        Args:
            case_id: The case ID

        Returns:
            List of message dictionaries with full content
        """
        # Get all message IDs for this case
        message_ids = self.get_case_associated_message_ids(case_id)

        if not message_ids:
            return []

        # Fetch all messages in bulk (single API call instead of N calls)
        messages = self.get_messages_bulk(message_ids)

        # Sort by timestamp
        messages.sort(key=lambda m: m.get("channelCreatedTime", 0))

        return messages

    def get_case_by_number(self, case_number: int) -> Optional[Dict[str, Any]]:
        """
        Fetch a case by its case number.

        Args:
            case_number: The case number (e.g., 478117)

        Returns:
            Case dictionary or None if not found
        """
        try:
            response = self._make_request(
                "GET",
                f"/api/v2/case/case-numbers?case-number={case_number}"
            )
            cases = response.get("data", [])
            return cases[0] if cases else None
        except SprinklrAPIError:
            return None

    def fetch_cases_by_number_range(
        self,
        start_number: int,
        end_number: int,
        max_cases: Optional[int] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Fetch cases by iterating through a case number range.

        This is a workaround for the broken search API pagination.
        Cases are fetched by number and their messages are retrieved.

        Args:
            start_number: Starting case number
            end_number: Ending case number (inclusive)
            max_cases: Maximum number of cases to return

        Yields:
            Case dictionaries with messages included
        """
        cases_found = 0

        for case_num in range(start_number, end_number + 1):
            if max_cases and cases_found >= max_cases:
                break

            case = self.get_case_by_number(case_num)
            if case:
                case_id = case.get("id")
                if case_id:
                    # Fetch messages for this case
                    try:
                        messages = self.get_case_messages(case_id)
                        case["messages"] = messages
                    except SprinklrAPIError as e:
                        print(f"Warning: Could not fetch messages for case {case_num}: {e}")
                        case["messages"] = []

                    yield case
                    cases_found += 1

    def fetch_cases_with_messages(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        max_cases: Optional[int] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Fetch cases with their messages using the v1 search API.

        Uses the v1 search API which supports proper pagination and date filtering.

        Args:
            start_date: Filter cases created after this date
            end_date: Filter cases created before this date
            max_cases: Maximum number of cases to fetch

        Yields:
            Case dictionaries with messages included
        """
        rows_per_page = 100
        cases_fetched = 0
        start_offset = 0
        seen_ids = set()

        while True:
            # Check if we've hit the max
            if max_cases and cases_fetched >= max_cases:
                break

            # Search for cases using v1 API
            search_result = self.search_cases_v1(
                start_date=start_date,
                end_date=end_date,
                start=start_offset,
                rows=rows_per_page
            )

            cases = search_result.get("data", [])
            total_hits = search_result.get("totalHits", 0)
            has_more = search_result.get("hasMore", False)

            if not cases:
                break

            for case in cases:
                if max_cases and cases_fetched >= max_cases:
                    break

                case_id = case.get("id")
                if case_id:
                    # Skip duplicates
                    if case_id in seen_ids:
                        continue
                    seen_ids.add(case_id)

                    # Fetch messages for this case
                    try:
                        messages = self.get_case_messages(case_id)
                        case["messages"] = messages
                    except SprinklrAPIError as e:
                        print(f"Warning: Could not fetch messages for case {case_id}: {e}")
                        case["messages"] = []

                    yield case
                    cases_fetched += 1

            # Move to next page
            start_offset += rows_per_page

            # Stop if no more results
            if not has_more or start_offset >= total_hits:
                break

    def test_connection(self) -> bool:
        """
        Test the API connection.

        Returns:
            True if connection is successful
        """
        try:
            # Try to search for one case to verify credentials
            self.search_cases(page_size=1)
            return True
        except Exception:
            return False

    @staticmethod
    def extract_brand(case: Dict[str, Any]) -> Optional[str]:
        """
        Extract brand name from case custom properties.

        The brand is stored in workflow.customProperties with key '5cc9a7cfe4b01904c8dfc908'.

        Args:
            case: Case dictionary from Sprinklr API

        Returns:
            Brand name or None if not found
        """
        try:
            custom_props = case.get("workflow", {}).get("customProperties", {})
            # Brand field key in Sprinklr
            brand_values = custom_props.get("5cc9a7cfe4b01904c8dfc908", [])
            return brand_values[0] if brand_values else None
        except (KeyError, IndexError):
            return None

    @staticmethod
    def extract_case_metadata(case: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract useful metadata from a case for storage.

        Args:
            case: Case dictionary from Sprinklr API

        Returns:
            Dictionary with extracted metadata
        """
        custom_props = case.get("workflow", {}).get("customProperties", {})

        return {
            "case_id": case.get("id"),
            "case_number": case.get("caseNumber"),
            "subject": case.get("subject", ""),
            "description": case.get("description", ""),
            "status": case.get("status"),
            "priority": case.get("priority"),
            "case_type": case.get("caseType"),
            "sentiment": case.get("sentiment", 0),
            "channel": case.get("externalCase", {}).get("channelType")
                       or case.get("contact", {}).get("channelType"),
            "brand": SprinklrClient.extract_brand(case),
            "language": custom_props.get("5cc9a7d0e4b01904c8dfc965", [None])[0],
            "country": custom_props.get("_c_66fcd9757813fc0020abeda3", [None])[0],
            "contact_name": case.get("contact", {}).get("name"),
            "created_time": case.get("createdTime"),
            "modified_time": case.get("modifiedTime"),
        }


class SprinklrAPIError(Exception):
    """Base exception for Sprinklr API errors."""
    pass


class AuthenticationError(SprinklrAPIError):
    """Raised when authentication fails."""
    pass


class AuthorizationError(SprinklrAPIError):
    """Raised when authorization fails."""
    pass


class RateLimitError(SprinklrAPIError):
    """Raised when rate limit is exceeded."""
    pass
