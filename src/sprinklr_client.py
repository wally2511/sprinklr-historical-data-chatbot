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

    def search_cases(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[str] = None,
        page: int = 0,
        page_size: int = 50
    ) -> Dict[str, Any]:
        """
        Search for cases with filters.

        Args:
            start_date: Filter cases created after this date
            end_date: Filter cases created before this date
            status: Filter by case status
            page: Page number for pagination
            page_size: Number of results per page

        Returns:
            Search results with cases and pagination info
        """
        params = {
            "page": page,
            "size": page_size,
            "sort": "createdTime,desc"
        }

        if start_date:
            params["createdTimeFrom"] = int(start_date.timestamp() * 1000)
        if end_date:
            params["createdTimeTo"] = int(end_date.timestamp() * 1000)
        if status:
            params["status"] = status

        return self._make_request("GET", "/api/v2/case/search", params=params)

    def get_case_messages(self, case_id: str) -> List[Dict[str, Any]]:
        """
        Fetch all messages for a case.

        Args:
            case_id: The case ID

        Returns:
            List of message dictionaries
        """
        response = self._make_request("GET", f"/api/v1/case/{case_id}/messages")
        return response.get("data", [])

    def fetch_cases_with_messages(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        max_cases: Optional[int] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Fetch cases with their messages, handling pagination.

        Args:
            start_date: Filter cases created after this date
            end_date: Filter cases created before this date
            max_cases: Maximum number of cases to fetch

        Yields:
            Case dictionaries with messages included
        """
        page = 0
        page_size = 50
        cases_fetched = 0

        while True:
            # Check if we've hit the max
            if max_cases and cases_fetched >= max_cases:
                break

            # Search for cases
            search_result = self.search_cases(
                start_date=start_date,
                end_date=end_date,
                page=page,
                page_size=page_size
            )

            cases = search_result.get("data", [])
            if not cases:
                break

            for case in cases:
                if max_cases and cases_fetched >= max_cases:
                    break

                case_id = case.get("id")
                if case_id:
                    # Fetch messages for this case
                    try:
                        messages = self.get_case_messages(case_id)
                        case["messages"] = messages
                    except SprinklrAPIError as e:
                        print(f"Warning: Could not fetch messages for case {case_id}: {e}")
                        case["messages"] = []

                    yield case
                    cases_fetched += 1

            # Check if there are more pages
            total_pages = search_result.get("totalPages", 1)
            if page >= total_pages - 1:
                break

            page += 1

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
