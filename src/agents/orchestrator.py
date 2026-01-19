"""
Orchestrator for coordinating multi-agent query processing.

This module coordinates the Query Agent and Response Agent to process
user queries through the optimal pipeline.
"""

from typing import Dict, Any, Optional, List, Union
from datetime import datetime

from .query_agent import QueryAgent, QueryPlan, SearchStep, CompoundQueryPlan
from .response_agent import ResponseAgent, ResponseResult

# Import Config - handle both package and direct execution contexts
try:
    from ..config import Config
except ImportError:
    from config import Config


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
        brands: Optional[List[str]] = None,
        enable_compound: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Process a user query through the multi-agent pipeline.

        Args:
            query: The user's natural language query
            start_date: Optional date filter from UI
            end_date: Optional date filter from UI
            theme: Optional theme filter from UI
            brands: Optional brand filter from UI
            enable_compound: Whether to allow compound (multi-step) searches

        Returns:
            Dictionary containing response, sources, and metadata
        """
        current_date = datetime.now().strftime("%Y-%m-%d")

        # Use config default if not explicitly specified
        if enable_compound is None:
            enable_compound = Config.ENABLE_COMPOUND_SEARCH

        # Get available filter values
        available_themes = self.vector_store.get_all_themes()
        available_brands = self.vector_store.get_all_brands()

        # Step 1: Query Agent analyzes the query
        plan = self.query_agent.process(
            query=query,
            available_themes=available_themes,
            available_brands=available_brands,
            current_date=current_date,
            enable_compound=enable_compound
        )

        # Check if compound plan was generated
        if isinstance(plan, CompoundQueryPlan) and plan.is_compound:
            return self._execute_compound_plan(
                plan, query, start_date, end_date, theme, brands
            )

        # Simple query plan execution (backward compatible)
        query_plan = plan  # Type: QueryPlan

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
                    n_results=min(query_plan.result_count, Config.MAX_CONTEXT_CASES_BROAD),
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

    def _execute_compound_plan(
        self,
        plan: CompoundQueryPlan,
        query: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        theme: Optional[str] = None,
        brands: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Execute a compound (multi-step) search strategy.

        Args:
            plan: The CompoundQueryPlan with ordered search steps
            query: Original user query
            start_date: Optional UI date filter
            end_date: Optional UI date filter
            theme: Optional UI theme filter
            brands: Optional UI brand filter

        Returns:
            Dictionary containing synthesized response and metadata
        """
        step_results = []
        all_cases = []
        all_aggregations = {}

        for i, step in enumerate(plan.steps):
            # Apply UI filters to step if specified
            if theme:
                step.themes = [theme]
            if brands:
                step.brands = brands
            if start_date:
                step.date_start = start_date
            if end_date:
                step.date_end = end_date

            # Execute the step
            result = self._execute_step(step, prior_results=step_results)
            step_results.append({
                "step": step,
                "result": result
            })

            # Collect cases and aggregations
            if result.get("cases"):
                # Tag cases with metadata for response agent
                for case in result["cases"]:
                    case["_detail_level"] = step.detail_level
                    case["_step_purpose"] = step.purpose
                all_cases.extend(result["cases"])
            if result.get("aggregation"):
                all_aggregations[step.purpose] = result["aggregation"]

        # Deduplicate cases by case_number while preserving order
        seen = set()
        unique_cases = []
        for case in all_cases:
            case_num = case.get("metadata", {}).get("case_number")
            if case_num and case_num not in seen:
                seen.add(case_num)
                unique_cases.append(case)
            elif not case_num:
                unique_cases.append(case)

        # Response Agent synthesizes all results
        response_result = self.response_agent.process_compound(
            plan=plan,
            step_results=step_results,
            cases=unique_cases,
            aggregations=all_aggregations,
            original_query=query
        )

        # Build final response
        return {
            "response": response_result.response,
            "cases_found": response_result.cases_found,
            "query_type": response_result.query_type,
            "sources": response_result.sources,
            "query_plan": plan.to_dict(),
            "compound_steps": len(plan.steps)
        }

    def _execute_step(
        self,
        step: SearchStep,
        prior_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Execute a single search step.

        Args:
            step: The SearchStep to execute
            prior_results: Results from prior steps (for use_prior_results)

        Returns:
            Dictionary with cases and/or aggregation data
        """
        if step.step_type == "database_query":
            # Execute database query (filter and count)
            return self._execute_database_query(step)

        elif step.step_type == "aggregation":
            # Execute aggregation
            agg_result = self._execute_aggregation_step(step)
            return {"aggregation": agg_result}

        elif step.step_type == "broad_search":
            # Broad search returns many summaries
            cases = self.vector_store.search(
                query=step.semantic_query or "",
                n_results=min(step.result_count, 50),  # Cap at 50
                start_date=step.date_start,
                end_date=step.date_end,
                theme=step.themes[0] if step.themes else None,
                brands=step.brands
            )
            return {"cases": cases}

        elif step.step_type == "filtered_search":
            # Filtered search returns fewer cases with full detail
            cases = self.vector_store.search(
                query=step.semantic_query or "",
                n_results=min(step.result_count, 10),  # Cap at 10
                start_date=step.date_start,
                end_date=step.date_end,
                theme=step.themes[0] if step.themes else None,
                brands=step.brands
            )
            return {"cases": cases}

        elif step.step_type == "specific_case":
            # Look up specific case numbers
            cases = []
            case_numbers = step.case_numbers or []

            # If use_prior_results, extract case numbers from prior results
            if step.use_prior_results and prior_results:
                for prior in prior_results:
                    prior_cases = prior.get("result", {}).get("cases", [])
                    for case in prior_cases[:3]:  # Limit to top 3
                        case_num = case.get("metadata", {}).get("case_number")
                        if case_num and case_num not in case_numbers:
                            case_numbers.append(case_num)

            # Fetch each case
            for case_num in case_numbers[:3]:  # Max 3 specific cases
                case = self.vector_store.get_by_case_number(case_num)
                if case:
                    cases.append(case)
            return {"cases": cases}

        return {}

    def _execute_database_query(self, step: SearchStep) -> Dict[str, Any]:
        """
        Execute a database query step (filter and count/aggregate).

        Args:
            step: SearchStep with group_by, filters, and top_n specified

        Returns:
            Dictionary with aggregation data and optionally sample cases
        """
        result = {}

        if step.group_by:
            # Use the filter_and_count method from vector_store
            counts = self.vector_store.filter_and_count(
                group_by=step.group_by,
                filters=step.filters,
                top_n=step.top_n
            )

            # Calculate total for percentage
            total = sum(counts.values())

            result["aggregation"] = {
                f"{step.group_by}_distribution": counts,
                "total": total,
                "group_by": step.group_by,
                "filters_applied": step.filters
            }

            # Also get sample cases for each top category (for examples)
            if step.top_n and step.top_n <= 5:
                sample_cases = []
                for category in list(counts.keys())[:step.top_n]:
                    # Get 1-2 sample cases for each category
                    category_filters = {step.group_by: category}
                    if step.filters:
                        category_filters.update(step.filters)

                    category_cases = self.vector_store.get_filtered_cases(
                        filters=category_filters,
                        limit=2
                    )
                    for case in category_cases:
                        case["_category"] = category
                    sample_cases.extend(category_cases)

                if sample_cases:
                    result["cases"] = sample_cases

        return result

    def _execute_aggregation_step(self, step: SearchStep) -> Dict[str, Any]:
        """
        Execute an aggregation step.

        Args:
            step: SearchStep with aggregation_type specified

        Returns:
            Dictionary with aggregation results
        """
        result = {
            "total_cases": self.vector_store.get_case_count()
        }

        agg_type = step.aggregation_type

        if agg_type == "count_by_brand":
            result["brand_distribution"] = self.vector_store.count_by_brand()
        elif agg_type == "sentiment_distribution":
            result["sentiment_distribution"] = self.vector_store.count_by_field("sentiment")
        elif agg_type == "count_by_case_type":
            result["case_type_distribution"] = self.vector_store.count_by_case_type()
        elif agg_type == "count_by_case_topic":
            result["case_topic_distribution"] = self.vector_store.count_by_case_topic()
        else:  # Default to count_by_theme
            result["theme_distribution"] = self.vector_store.count_by_theme()

        return result

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

        elif agg_type == "count_by_case_type":
            result["case_type_distribution"] = self.vector_store.count_by_case_type()

        elif agg_type == "count_by_case_topic":
            result["case_topic_distribution"] = self.vector_store.count_by_case_topic()

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
