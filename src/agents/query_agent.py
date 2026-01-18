"""
Query Agent for analyzing user queries and generating search plans.

This agent determines the type of query (specific case, broad search,
aggregation, etc.) and creates an optimal search strategy.
"""

import json
import re
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta


@dataclass
class QueryPlan:
    """
    Structured plan for executing a user query.

    Attributes:
        query_type: Type of query (specific_case, broad_search, filtered_search, aggregation)
        case_number: Case number for specific case lookups
        semantic_query: Query text for semantic search
        result_count: Number of results to retrieve
        detail_level: Level of detail needed (summary, full_conversation)
        date_start: Start date filter (ISO format)
        date_end: End date filter (ISO format)
        themes: List of themes to filter by
        brands: List of brands to filter by
        aggregation_type: Type of aggregation (count_by_theme, count_by_brand, etc.)
    """
    query_type: str = "broad_search"  # specific_case, broad_search, filtered_search, aggregation
    case_number: Optional[int] = None
    semantic_query: Optional[str] = None
    result_count: int = 10
    detail_level: str = "summary"  # summary, full_conversation, metadata_only
    date_start: Optional[str] = None
    date_end: Optional[str] = None
    themes: Optional[List[str]] = None
    brands: Optional[List[str]] = None
    aggregation_type: Optional[str] = None  # count_by_theme, count_by_brand, sentiment_distribution

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class QueryAgent:
    """
    Agent that analyzes user queries and generates optimal search plans.

    Uses a combination of regex patterns for fast detection and LLM for
    complex query understanding.
    """

    SYSTEM_PROMPT = """You are a query analysis agent for a customer service case database containing faith-based conversations.
Your job is to analyze user queries and generate a structured search plan.

Output a JSON object with these fields:
- query_type: "specific_case" | "broad_search" | "filtered_search" | "aggregation"
- case_number: integer if query mentions a specific case number, null otherwise
- semantic_query: the core search query for semantic search, null for pure aggregations
- result_count: 1 for specific case, 10 for filtered searches with full transcripts, 100 for broad analysis with summaries
- detail_level: "full_conversation" for specific cases, "summary" for broad searches, "metadata_only" for aggregations
- date_start: ISO date (YYYY-MM-DD) if date range mentioned, null otherwise
- date_end: ISO date (YYYY-MM-DD) if date range mentioned, null otherwise
- themes: list of themes if mentioned (faith, prayer, grief, anxiety, doubt, relationships, forgiveness, bible_study, evangelism, new_believer, church_hurt, addiction, purpose, suffering, teen_faith, skeptic), null otherwise
- brands: list of brands if mentioned, null otherwise
- aggregation_type: "count_by_theme" | "count_by_brand" | "sentiment_distribution" | null

Examples:
Query: "What was the outcome of case #54123?"
Output: {"query_type": "specific_case", "case_number": 54123, "result_count": 1, "detail_level": "full_conversation"}

Query: "What are the most common questions in the last 30 days?"
Output: {"query_type": "aggregation", "aggregation_type": "count_by_theme", "result_count": 50, "detail_level": "metadata_only", "date_start": "<30 days ago>", "date_end": "<today>"}

Query: "Show me anxiety cases from Brand1"
Output: {"query_type": "filtered_search", "semantic_query": "anxiety concerns", "themes": ["anxiety"], "brands": ["Brand1"], "result_count": 10, "detail_level": "full_conversation"}

Query: "What questions do users ask about prayer?"
Output: {"query_type": "broad_search", "semantic_query": "prayer questions requests", "result_count": 100, "detail_level": "summary"}

Query: "How many cases per brand?"
Output: {"query_type": "aggregation", "aggregation_type": "count_by_brand", "result_count": 5, "detail_level": "metadata_only"}
"""

    # Patterns for fast detection
    CASE_NUMBER_PATTERNS = [
        r'case\s*#?\s*(\d+)',
        r'#(\d+)',
        r'case\s+number\s+(\d+)',
        r'case\s+(\d{4,})',  # 4+ digit numbers after "case"
    ]

    AGGREGATION_KEYWORDS = [
        "how many", "count", "total", "distribution", "breakdown",
        "most common", "popular", "frequent", "statistics", "stats",
        "trend", "trends", "percentage", "percent"
    ]

    DATE_KEYWORDS = [
        "today", "yesterday", "last week", "last month", "last 30 days",
        "past week", "past month", "recent", "this week", "this month"
    ]

    def __init__(self, llm_client=None, provider: str = "anthropic"):
        """
        Initialize the Query Agent.

        Args:
            llm_client: Optional LLM client for complex query understanding
            provider: LLM provider ("anthropic" or "openai")
        """
        self.llm_client = llm_client
        self.provider = provider

    def process(
        self,
        query: str,
        available_themes: Optional[List[str]] = None,
        available_brands: Optional[List[str]] = None,
        current_date: Optional[str] = None
    ) -> QueryPlan:
        """
        Analyze a user query and generate a search plan.

        Args:
            query: The user's natural language query
            available_themes: List of available themes for filtering
            available_brands: List of available brands for filtering
            current_date: Current date for relative date calculations

        Returns:
            QueryPlan with optimal search strategy
        """
        if not current_date:
            current_date = datetime.now().strftime("%Y-%m-%d")

        # Fast path: Check for case number
        case_number = self._extract_case_number(query)
        if case_number:
            return QueryPlan(
                query_type="specific_case",
                case_number=case_number,
                semantic_query=None,
                result_count=1,
                detail_level="full_conversation"
            )

        # Fast path: Check for aggregation keywords
        if self._is_aggregation_query(query):
            return self._create_aggregation_plan(query, current_date)

        # Check for date range mentions
        date_start, date_end = self._extract_date_range(query, current_date)

        # Check for theme/brand mentions
        detected_themes = self._detect_themes(query, available_themes or [])
        detected_brands = self._detect_brands(query, available_brands or [])

        # Use LLM for complex query understanding if available
        if self.llm_client:
            try:
                return self._process_with_llm(
                    query, available_themes, available_brands, current_date
                )
            except Exception as e:
                print(f"Warning: LLM query analysis failed: {e}")
                # Fall through to rule-based approach

        # Rule-based fallback
        if detected_themes or detected_brands or date_start:
            return QueryPlan(
                query_type="filtered_search",
                semantic_query=query,
                result_count=10,
                detail_level="full_conversation",
                date_start=date_start,
                date_end=date_end,
                themes=detected_themes if detected_themes else None,
                brands=detected_brands if detected_brands else None
            )

        # Default: broad search
        return QueryPlan(
            query_type="broad_search",
            semantic_query=query,
            result_count=100,
            detail_level="summary",
            date_start=date_start,
            date_end=date_end
        )

    def _extract_case_number(self, query: str) -> Optional[int]:
        """Extract case number from query using regex patterns."""
        for pattern in self.CASE_NUMBER_PATTERNS:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue
        return None

    def _is_aggregation_query(self, query: str) -> bool:
        """Check if query is asking for aggregation/statistics."""
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in self.AGGREGATION_KEYWORDS)

    def _create_aggregation_plan(self, query: str, current_date: str) -> QueryPlan:
        """Create a plan for aggregation queries."""
        query_lower = query.lower()

        # Determine aggregation type
        if "brand" in query_lower:
            agg_type = "count_by_brand"
        elif "sentiment" in query_lower:
            agg_type = "sentiment_distribution"
        else:
            agg_type = "count_by_theme"

        # Check for date range
        date_start, date_end = self._extract_date_range(query, current_date)

        return QueryPlan(
            query_type="aggregation",
            semantic_query=query,
            result_count=50,
            detail_level="metadata_only",
            date_start=date_start,
            date_end=date_end,
            aggregation_type=agg_type
        )

    def _extract_date_range(
        self,
        query: str,
        current_date: str
    ) -> tuple[Optional[str], Optional[str]]:
        """Extract date range from query."""
        query_lower = query.lower()
        today = datetime.strptime(current_date, "%Y-%m-%d")

        # Check for relative date patterns
        if "last 30 days" in query_lower or "past 30 days" in query_lower or "past month" in query_lower:
            start = (today - timedelta(days=30)).strftime("%Y-%m-%d")
            return start, current_date

        if "last week" in query_lower or "past week" in query_lower:
            start = (today - timedelta(days=7)).strftime("%Y-%m-%d")
            return start, current_date

        if "last 7 days" in query_lower or "past 7 days" in query_lower:
            start = (today - timedelta(days=7)).strftime("%Y-%m-%d")
            return start, current_date

        if "this week" in query_lower:
            # Start of current week (Monday)
            start = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
            return start, current_date

        if "this month" in query_lower:
            start = today.replace(day=1).strftime("%Y-%m-%d")
            return start, current_date

        if "today" in query_lower:
            return current_date, current_date

        if "yesterday" in query_lower:
            yesterday = (today - timedelta(days=1)).strftime("%Y-%m-%d")
            return yesterday, yesterday

        if "recent" in query_lower:
            start = (today - timedelta(days=14)).strftime("%Y-%m-%d")
            return start, current_date

        return None, None

    def _detect_themes(self, query: str, available_themes: List[str]) -> List[str]:
        """Detect theme mentions in query."""
        query_lower = query.lower()
        detected = []
        for theme in available_themes:
            if theme.lower() in query_lower or theme.replace("_", " ") in query_lower:
                detected.append(theme)
        return detected

    def _detect_brands(self, query: str, available_brands: List[str]) -> List[str]:
        """Detect brand mentions in query."""
        detected = []
        for brand in available_brands:
            if brand.lower() in query.lower():
                detected.append(brand)
        return detected

    def _process_with_llm(
        self,
        query: str,
        available_themes: Optional[List[str]],
        available_brands: Optional[List[str]],
        current_date: str
    ) -> QueryPlan:
        """Use LLM for complex query understanding."""
        context = f"""Available themes: {', '.join(available_themes) if available_themes else 'Not specified'}
Available brands: {', '.join(available_brands) if available_brands else 'Not specified'}
Current date: {current_date}

User query: {query}

Analyze this query and output a JSON search plan."""

        if self.provider == "openai":
            response = self.llm_client.chat.completions.create(
                model="gpt-4o",
                max_tokens=500,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": context}
                ]
            )
            response_text = response.choices[0].message.content
        else:
            response = self.llm_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                system=self.SYSTEM_PROMPT,
                messages=[{"role": "user", "content": context}]
            )
            response_text = response.content[0].text

        # Parse JSON from response
        try:
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                plan_dict = json.loads(json_match.group())

                # Handle relative dates in response
                if plan_dict.get("date_start") and "<" in str(plan_dict.get("date_start")):
                    date_start, date_end = self._extract_date_range(query, current_date)
                    plan_dict["date_start"] = date_start
                    plan_dict["date_end"] = date_end or current_date

                return QueryPlan(
                    query_type=plan_dict.get("query_type", "broad_search"),
                    case_number=plan_dict.get("case_number"),
                    semantic_query=plan_dict.get("semantic_query", query),
                    result_count=plan_dict.get("result_count", 10),
                    detail_level=plan_dict.get("detail_level", "summary"),
                    date_start=plan_dict.get("date_start"),
                    date_end=plan_dict.get("date_end"),
                    themes=plan_dict.get("themes"),
                    brands=plan_dict.get("brands"),
                    aggregation_type=plan_dict.get("aggregation_type")
                )
        except (json.JSONDecodeError, TypeError) as e:
            print(f"Warning: Failed to parse LLM response: {e}")

        # Fallback
        return QueryPlan(
            query_type="broad_search",
            semantic_query=query,
            result_count=15,
            detail_level="summary"
        )
