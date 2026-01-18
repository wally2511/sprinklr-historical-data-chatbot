"""
Orchestrator for coordinating multi-agent query processing.

This module coordinates the Query Agent and Response Agent to process
user queries through the optimal pipeline.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from .query_agent import QueryAgent, QueryPlan
from .response_agent import ResponseAgent, ResponseResult


class Orchestrator:
    """
    Orchestrates the multi-agent workflow for query processing.

    Flow:
    1. Query Agent analyzes the user's query and creates a QueryPlan
    2. Orchestrator executes the search strategy based on the plan
    3. Response Agent generates an appropriate response

    Supports:
    - Specific case lookups
    - Broad semantic searches
    - Filtered searches
    - Aggregation queries
    """

    def __init__(
        self,
        llm_client,
        vector_store,
        provider: str = "anthropic"
    ):
        """
        Initialize the Orchestrator.

        Args:
            llm_client: LLM client for agents
            vector_store: VectorStore instance for data retrieval
            provider: LLM provider ("anthropic" or "openai")
        """
        self.vector_store = vector_store
        self.llm_client = llm_client
        self.provider = provider

        # Initialize agents
        self.query_agent = QueryAgent(llm_client, provider)
        self.response_agent = ResponseAgent(llm_client, provider)

    def process_query(
        self,
        query: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        theme: Optional[str] = None,
        brands: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Process a user query through the multi-agent pipeline.

        Args:
            query: The user's natural language query
            start_date: Optional date filter from UI
            end_date: Optional date filter from UI
            theme: Optional theme filter from UI
            brands: Optional brand filter from UI

        Returns:
            Dictionary containing response, sources, and metadata
        """
        current_date = datetime.now().strftime("%Y-%m-%d")

        # Get available filter values
        available_themes = self.vector_store.get_all_themes()
        available_brands = self.vector_store.get_all_brands()

        # Step 1: Query Agent analyzes the query
        query_plan = self.query_agent.process(
            query=query,
            available_themes=available_themes,
            available_brands=available_brands,
            current_date=current_date
        )

        # Apply UI-provided filters (override agent's detection)
        if theme:
            query_plan.themes = [theme]
        if brands:
            query_plan.brands = brands
        if start_date:
            query_plan.date_start = start_date
        if end_date:
            query_plan.date_end = end_date

        # Step 2: Execute search strategy based on plan
        cases = []
        aggregation_data = None

        if query_plan.query_type == "specific_case" and query_plan.case_number:
            # Direct case lookup
            case = self.vector_store.get_by_case_number(query_plan.case_number)
            if case:
                cases = [case]

        elif query_plan.query_type == "aggregation":
            # Get aggregation data
            aggregation_data = self._execute_aggregation(query_plan)

            # Also get sample cases for context
            if query_plan.semantic_query:
                cases = self.vector_store.search(
                    query=query_plan.semantic_query,
                    n_results=5,
                    start_date=query_plan.date_start,
                    end_date=query_plan.date_end,
                    theme=query_plan.themes[0] if query_plan.themes else None,
                    brands=query_plan.brands
                )

        else:
            # Semantic search with filters
            cases = self.vector_store.search(
                query=query_plan.semantic_query or query,
                n_results=query_plan.result_count,
                start_date=query_plan.date_start,
                end_date=query_plan.date_end,
                theme=query_plan.themes[0] if query_plan.themes else None,
                brands=query_plan.brands
            )

        # Step 3: Response Agent generates the answer
        response_result = self.response_agent.process(
            query_plan=query_plan,
            cases=cases,
            original_query=query,
            aggregation_data=aggregation_data
        )

        # Build final response
        return {
            "response": response_result.response,
            "cases_found": response_result.cases_found,
            "query_type": response_result.query_type,
            "sources": response_result.sources,
            "query_plan": query_plan.to_dict()
        }

    def _execute_aggregation(self, query_plan: QueryPlan) -> Dict[str, Any]:
        """
        Execute aggregation based on the query plan.

        Args:
            query_plan: The query plan with aggregation type

        Returns:
            Dictionary with aggregation results
        """
        result = {
            "total_cases": self.vector_store.get_case_count()
        }

        agg_type = query_plan.aggregation_type

        if agg_type == "count_by_brand":
            result["brand_distribution"] = self.vector_store.count_by_brand()

        elif agg_type == "sentiment_distribution":
            result["sentiment_distribution"] = self.vector_store.count_by_field("sentiment")

        else:  # Default to count_by_theme
            result["theme_distribution"] = self.vector_store.count_by_theme()

        # If date filter specified, we'd need to filter the aggregation
        # For now, aggregations are on all data (could enhance later)

        return result

    def get_available_filters(self) -> Dict[str, List[str]]:
        """Get available filter values for the UI."""
        return {
            "themes": self.vector_store.get_all_themes(),
            "brands": self.vector_store.get_all_brands()
        }
