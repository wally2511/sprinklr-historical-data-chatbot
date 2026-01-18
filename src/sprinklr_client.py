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

        # Setup session with retries (includes 403 for rate limit errors)
        self.session = requests.Session()
        retries = Retry(
            total=5,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retries))

        # Rate limit retry settings
        self.rate_limit_max_retries = 3
        self.rate_limit_wait_seconds = 300  # 5 minutes between retries

        # API3 base URL (for search/bulk endpoints)
        self.api3_base_url = self.base_url.replace("api2.sprinklr.com", "api3.sprinklr.com")

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
        json_data: Optional[Dict] = None,
        _retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        Make an API request with rate limiting and error handling.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            json_data: JSON body data
            _retry_count: Internal retry counter for rate limit errors

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
                # Check if this is a rate limit error (Developer Over Rate)
                try:
                    error_body = e.response.json()
                    error_msg = error_body.get("message", "")
                except:
                    error_msg = e.response.text

                if "rate" in error_msg.lower() or "over" in error_msg.lower():
                    if _retry_count < self.rate_limit_max_retries:
                        wait_time = self.rate_limit_wait_seconds
                        print(f"Rate limit hit (403). Waiting {wait_time // 60} minutes before retry {_retry_count + 1}/{self.rate_limit_max_retries}...")
                        time.sleep(wait_time)
                        return self._make_request(method, endpoint, params, json_data, _retry_count + 1)
                    else:
                        raise RateLimitError(f"Rate limit exceeded after {self.rate_limit_max_retries} retries")
                else:
                    raise AuthorizationError("Insufficient permissions")
            elif e.response.status_code == 429:
                raise RateLimitError("Rate limit exceeded")
            else:
                raise SprinklrAPIError(f"API error: {e}")

        except requests.exceptions.RequestException as e:
            raise SprinklrAPIError(f"Request failed: {e}")

    def _make_api3_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json_data: Optional[Any] = None,
        _retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        Make an API request to api3.sprinklr.com with rate limiting and error handling.

        Used for search and bulk endpoints.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            json_data: JSON body data (can be dict or list)
            _retry_count: Internal retry counter for rate limit errors

        Returns:
            Response data as dictionary
        """
        self.rate_limiter.wait_if_needed()

        url = f"{self.api3_base_url}{endpoint}"
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
                # Check if this is a rate limit error (Developer Over Rate)
                try:
                    error_body = e.response.json()
                    error_msg = error_body.get("message", "")
                except:
                    error_msg = e.response.text

                if "rate" in error_msg.lower() or "over" in error_msg.lower():
                    if _retry_count < self.rate_limit_max_retries:
                        wait_time = self.rate_limit_wait_seconds
                        print(f"Rate limit hit (403). Waiting {wait_time // 60} minutes before retry {_retry_count + 1}/{self.rate_limit_max_retries}...")
                        time.sleep(wait_time)
                        return self._make_api3_request(method, endpoint, params, json_data, _retry_count + 1)
                    else:
                        raise RateLimitError(f"Rate limit exceeded after {self.rate_limit_max_retries} retries")
                else:
                    raise AuthorizationError(f"Insufficient permissions: {error_msg}")
            elif e.response.status_code == 429:
                if _retry_count < self.rate_limit_max_retries:
                    wait_time = self.rate_limit_wait_seconds
                    print(f"Rate limit hit (429). Waiting {wait_time // 60} minutes before retry {_retry_count + 1}/{self.rate_limit_max_retries}...")
                    time.sleep(wait_time)
                    return self._make_api3_request(method, endpoint, params, json_data, _retry_count + 1)
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
        size: int = 100,
        cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search for cases using Sprinklr v2 search API.

        Uses POST /api/v2/search/CASE endpoint for initial request,
        then GET /api/v2/search/CASE?id={cursor} for pagination.

        Per API docs, v2 uses:
        - filter: AND/OR conditions with epoch timestamps
        - sorts: [{key: "createdTime", order: "DESC"}]
        - page: {size: 100} for initial request
        - cursor-based pagination for subsequent requests

        Args:
            start_date: Filter cases created after this date
            end_date: Filter cases created before this date
            size: Number of results per page (default 100)
            cursor: Cursor from previous response for pagination

        Returns:
            Search results with cases, cursor, and total count
        """
        # If we have a cursor, use GET for pagination (cursor expires after 5 min)
        if cursor:
            cursor_id = cursor.replace("id=", "") if cursor.startswith("id=") else cursor
            response = self._make_api3_request("GET", f"/api/v2/search/CASE?id={cursor_id}")
        else:
            # Build filter conditions
            filters = [{"type": "EQUALS", "key": "deleted", "values": [False]}]

            # Add date range filters using epoch timestamps
            if start_date:
                filters.append({
                    "type": "GTE",
                    "key": "createdTime",
                    "values": [int(start_date.timestamp() * 1000)]
                })
            if end_date:
                filters.append({
                    "type": "LTE",
                    "key": "createdTime",
                    "values": [int(end_date.timestamp() * 1000)]
                })

            # Build request body per API reference
            body = {
                "filter": {
                    "type": "AND",
                    "filters": filters
                },
                "sorts": [{"key": "createdTime", "order": "DESC"}],
                "page": {"size": size},
                "includeCount": True
            }

            response = self._make_api3_request("POST", "/api/v2/search/CASE", json_data=body)

        # Extract data from response
        data = response.get("data", {})
        results = data.get("results", [])
        next_cursor = data.get("cursor")
        total_count = data.get("totalCount", 0)

        return {
            "data": results,
            "cursor": next_cursor,
            "totalCount": total_count,
            "errors": response.get("errors", [])
        }

    def search_cases_v1(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        start: int = 0,
        rows: int = 100,
        query: str = "",
        _retry_count: int = 0
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
                "sortKey": "caseCreationTime",
                "sortDirection": "DESC"
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
            # Handle 403 rate limit errors with retry
            if e.response.status_code == 403:
                try:
                    error_body = e.response.json()
                    error_msg = error_body.get("message", "")
                except:
                    error_msg = e.response.text

                if "rate" in error_msg.lower() or "over" in error_msg.lower():
                    if _retry_count < self.rate_limit_max_retries:
                        wait_time = self.rate_limit_wait_seconds
                        print(f"Rate limit hit (403). Waiting {wait_time // 60} minutes before retry {_retry_count + 1}/{self.rate_limit_max_retries}...")
                        time.sleep(wait_time)
                        return self.search_cases_v1(start_date, end_date, start, rows, query, _retry_count + 1)
                    else:
                        raise RateLimitError(f"Rate limit exceeded after {self.rate_limit_max_retries} retries")
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

        Uses GET /api/v2/case/associated-messages?id={case_id} on api3.

        Args:
            case_id: The case ID

        Returns:
            List of message ID strings
        """
        response = self._make_api3_request(
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

    def get_messages_bulk(self, message_ids: List[str], chunk_size: int = 50) -> List[Dict[str, Any]]:
        """
        Fetch multiple messages in bulk using the bulk fetch API.

        Uses POST /api/v2/message/bulk-fetch on api3.
        Includes rate limit retry handling.

        Args:
            message_ids: List of message ID strings
            chunk_size: Max messages per request (default 50)

        Returns:
            List of message dictionaries
        """
        if not message_ids:
            return []

        all_messages = []

        # Process in chunks to avoid API limits
        for i in range(0, len(message_ids), chunk_size):
            chunk = message_ids[i:i + chunk_size]

            try:
                response = self._make_api3_request(
                    "POST",
                    "/api/v2/message/bulk-fetch",
                    json_data=chunk
                )
                messages = response.get("data", [])
                all_messages.extend(messages)
            except SprinklrAPIError as e:
                print(f"Warning: Bulk message fetch failed for chunk: {e}")
                # Continue with other chunks

        return all_messages

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

        Uses GET /api/v2/case/case-numbers on api3.

        Args:
            case_number: The case number (e.g., 478117)

        Returns:
            Case dictionary or None if not found
        """
        try:
            response = self._make_api3_request(
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
        Fetch cases with their messages using the v2 search API.

        Uses cursor-based pagination for efficient traversal.
        Sorts by createdTime DESC to get newest cases first.

        Args:
            start_date: Filter cases created after this date
            end_date: Filter cases created before this date
            max_cases: Maximum number of cases to fetch

        Yields:
            Case dictionaries with messages included
        """
        cases_fetched = 0
        cursor = None
        seen_ids = set()

        while True:
            # Check if we've hit the max
            if max_cases and cases_fetched >= max_cases:
                break

            # Search for cases using v2 API with cursor pagination
            search_result = self.search_cases_v2(
                start_date=start_date,
                end_date=end_date,
                size=100,
                cursor=cursor
            )

            cases = search_result.get("data", [])
            cursor = search_result.get("cursor")
            total_count = search_result.get("totalCount", 0)

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

            # Stop if no cursor (no more results)
            if not cursor:
                break

    def fetch_cases_with_messages_batched(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        max_cases: Optional[int] = None,
        case_batch_size: int = 50,
        message_bulk_limit: int = 500
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Fetch cases with messages using batched message fetching for efficiency.

        Instead of fetching messages per-case (2 API calls per case), this method:
        1. Collects message IDs for a batch of cases
        2. Fetches ALL messages in one bulk request
        3. Associates messages back to their cases

        This reduces API calls from 2N to N+1 for N cases.

        Args:
            start_date: Filter cases created after this date
            end_date: Filter cases created before this date
            max_cases: Maximum number of cases to fetch
            case_batch_size: Number of cases to batch before bulk message fetch
            message_bulk_limit: Max messages per bulk fetch request

        Yields:
            Case dictionaries with messages included
        """
        cases_fetched = 0
        cursor = None
        seen_ids = set()
        case_batch = []

        while True:
            # Check if we've hit the max
            if max_cases and cases_fetched >= max_cases:
                break

            # Search for cases using v2 API with cursor pagination
            search_result = self.search_cases_v2(
                start_date=start_date,
                end_date=end_date,
                size=100,
                cursor=cursor
            )

            cases = search_result.get("data", [])
            cursor = search_result.get("cursor")

            if not cases:
                # Process any remaining cases in batch
                if case_batch:
                    yield from self._process_case_batch(case_batch, message_bulk_limit)
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

                    case_batch.append(case)
                    cases_fetched += 1

                    # Process batch when full
                    if len(case_batch) >= case_batch_size:
                        yield from self._process_case_batch(case_batch, message_bulk_limit)
                        case_batch = []

            # Stop if no cursor (no more results)
            if not cursor:
                # Process any remaining cases
                if case_batch:
                    yield from self._process_case_batch(case_batch, message_bulk_limit)
                break

    def _process_case_batch(
        self,
        cases: List[Dict[str, Any]],
        message_bulk_limit: int = 500
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Process a batch of cases by fetching all messages in bulk.

        Args:
            cases: List of case dictionaries
            message_bulk_limit: Max messages per bulk fetch

        Yields:
            Cases with messages attached
        """
        if not cases:
            return

        # Step 1: Collect message IDs for all cases in batch
        case_message_ids = {}  # case_id -> [message_ids]
        all_message_ids = []

        for case in cases:
            case_id = case.get("id")
            case_num = case.get("caseNumber", "unknown")
            try:
                message_ids = self.get_case_associated_message_ids(case_id)
                case_message_ids[case_id] = message_ids
                all_message_ids.extend(message_ids)
            except SprinklrAPIError as e:
                print(f"Warning: Could not fetch message IDs for case #{case_num}: {e}")
                case_message_ids[case_id] = []

        # Step 2: Bulk fetch ALL messages at once
        all_messages = []
        if all_message_ids:
            try:
                all_messages = self.get_messages_bulk(all_message_ids, chunk_size=message_bulk_limit)
            except SprinklrAPIError as e:
                print(f"Warning: Bulk message fetch failed: {e}")

        # Step 3: Create message lookup by ID
        message_lookup = {msg.get("messageId"): msg for msg in all_messages}

        # Step 4: Associate messages with cases and yield
        for case in cases:
            case_id = case.get("id")
            message_ids = case_message_ids.get(case_id, [])
            case["messages"] = [message_lookup.get(mid) for mid in message_ids if message_lookup.get(mid)]
            yield case

    def test_connection(self) -> bool:
        """
        Test the API connection using v2 search API.

        Returns:
            True if connection is successful
        """
        try:
            # Try to search for one case to verify credentials
            result = self.search_cases_v2(size=1)
            return len(result.get("data", [])) > 0 or result.get("totalCount", 0) >= 0
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
