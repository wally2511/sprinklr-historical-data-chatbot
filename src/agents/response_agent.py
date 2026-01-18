"""
Response Agent for generating context-appropriate responses.

This agent processes retrieved cases and generates responses tailored
to the query type (specific case analysis, broad synthesis, aggregation).
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ResponseResult:
    """Result from the response agent."""
    response: str
    cases_found: int
    query_type: str
    sources: List[Dict[str, Any]]


class ResponseAgent:
    """
    Agent that generates responses based on query type and retrieved context.

    Adapts response style based on whether the query is:
    - Specific case: Detailed analysis of a single case
    - Broad search: Synthesis across multiple cases
    - Aggregation: Statistical summary with insights
    """

    SPECIFIC_CASE_PROMPT = """You are analyzing a specific customer service case from a faith-based organization.
Provide a detailed analysis including:
1. What the customer asked about or discussed
2. How the agent responded
3. The outcome of the interaction
4. Any notable insights or lessons learned

Be specific and cite directly from the conversation. Be empathetic when discussing sensitive topics."""

    BROAD_SEARCH_PROMPT = """You are analyzing multiple customer service cases from faith-based organizations to answer a question.
Synthesize information across all provided cases to give a comprehensive answer.
Identify patterns, common themes, and provide specific examples where relevant.
Cite case numbers when referencing specific examples.
Be helpful and provide actionable insights when possible."""

    AGGREGATION_PROMPT = """You are presenting statistical data about customer service cases from faith-based organizations.
Present the data clearly and highlight the most significant findings.
Provide context and insights about what the numbers mean.
If sample cases are provided, reference them to illustrate the statistics."""

    FILTERED_SEARCH_PROMPT = """You are analyzing customer service cases that match specific criteria.
Summarize the cases that match the filter and identify common patterns.
Provide specific examples and insights relevant to the filter criteria.
Be helpful and provide actionable recommendations when possible."""

    def __init__(self, llm_client=None, provider: str = "anthropic"):
        """
        Initialize the Response Agent.

        Args:
            llm_client: LLM client for response generation
            provider: LLM provider ("anthropic" or "openai")
        """
        self.llm_client = llm_client
        self.provider = provider

    def process(
        self,
        query_plan: Any,  # QueryPlan
        cases: List[Dict[str, Any]],
        original_query: str,
        aggregation_data: Optional[Dict[str, Any]] = None
    ) -> ResponseResult:
        """
        Generate a response based on the query plan and retrieved data.

        Args:
            query_plan: The QueryPlan from the query agent
            cases: List of retrieved cases
            original_query: The user's original query
            aggregation_data: Optional aggregation statistics

        Returns:
            ResponseResult with the generated response
        """
        # Select appropriate prompt based on query type
        query_type = query_plan.query_type

        if query_type == "specific_case":
            system_prompt = self.SPECIFIC_CASE_PROMPT
            context = self._build_detailed_context(cases)
        elif query_type == "aggregation":
            system_prompt = self.AGGREGATION_PROMPT
            context = self._build_aggregation_context(aggregation_data, cases)
        elif query_type == "filtered_search":
            system_prompt = self.FILTERED_SEARCH_PROMPT
            context = self._build_filtered_context(cases, query_plan)
        else:  # broad_search
            system_prompt = self.BROAD_SEARCH_PROMPT
            context = self._build_summary_context(cases)

        # Build user message
        user_message = f"""Question: {original_query}

{context}

Please provide a helpful, specific answer based on the data above. If the data doesn't contain enough information to fully answer the question, acknowledge this limitation."""

        # Generate response
        if self.llm_client:
            response_text = self._call_llm(system_prompt, user_message)
        else:
            response_text = self._generate_fallback_response(cases, query_type, aggregation_data)

        # Format sources
        sources = self._format_sources(cases)

        return ResponseResult(
            response=response_text,
            cases_found=len(cases),
            query_type=query_type,
            sources=sources
        )

    def _build_detailed_context(self, cases: List[Dict[str, Any]]) -> str:
        """Build context with full conversation details for specific case queries."""
        if not cases:
            return "No matching case found."

        context_parts = []
        for case in cases:
            metadata = case.get("metadata", {})
            context_parts.append(f"""
=== Case #{metadata.get('case_number', 'Unknown')} ===
Date: {metadata.get('created_at', 'Unknown')[:10] if metadata.get('created_at') else 'Unknown'}
Brand: {metadata.get('brand', 'Unknown')}
Channel: {metadata.get('channel', 'Unknown')}
Theme: {metadata.get('theme', 'Unknown')}
Outcome: {metadata.get('outcome', 'Unknown')}
Subject: {metadata.get('subject', 'N/A')}

Summary: {case.get('summary', 'No summary available')}

Full Conversation:
{metadata.get('full_conversation', 'No conversation available')}

Description: {metadata.get('description', 'N/A')}
""")
        return "\n".join(context_parts)

    def _build_summary_context(self, cases: List[Dict[str, Any]]) -> str:
        """Build context with summaries only for broad queries."""
        if not cases:
            return "No matching cases found."

        context_parts = [f"Found {len(cases)} relevant cases:\n"]
        for i, case in enumerate(cases, 1):
            metadata = case.get("metadata", {})
            date_str = metadata.get('created_at', '')[:10] if metadata.get('created_at') else 'N/A'
            summary = case.get('summary', 'No summary')
            # Truncate long summaries
            if len(summary) > 300:
                summary = summary[:297] + "..."

            context_parts.append(f"""
{i}. Case #{metadata.get('case_number', 'Unknown')} ({date_str})
   Brand: {metadata.get('brand', 'Unknown')} | Theme: {metadata.get('theme', 'Unknown')} | Channel: {metadata.get('channel', 'Unknown')}
   Summary: {summary}
""")
        return "\n".join(context_parts)

    def _build_filtered_context(
        self,
        cases: List[Dict[str, Any]],
        query_plan: Any
    ) -> str:
        """Build context for filtered search results."""
        if not cases:
            return "No cases found matching the filter criteria."

        # Build filter description
        filters = []
        if query_plan.themes:
            filters.append(f"Theme: {', '.join(query_plan.themes)}")
        if query_plan.brands:
            filters.append(f"Brand: {', '.join(query_plan.brands)}")
        if query_plan.date_start:
            filters.append(f"Date range: {query_plan.date_start} to {query_plan.date_end or 'now'}")

        filter_desc = f"Filters applied: {' | '.join(filters)}" if filters else ""

        context_parts = [f"Found {len(cases)} cases matching criteria.\n{filter_desc}\n"]

        for i, case in enumerate(cases, 1):
            metadata = case.get("metadata", {})
            date_str = metadata.get('created_at', '')[:10] if metadata.get('created_at') else 'N/A'
            summary = case.get('summary', 'No summary')
            if len(summary) > 250:
                summary = summary[:247] + "..."

            context_parts.append(f"""
{i}. Case #{metadata.get('case_number', 'Unknown')} ({date_str})
   Brand: {metadata.get('brand', 'Unknown')} | Theme: {metadata.get('theme', 'Unknown')}
   Outcome: {metadata.get('outcome', 'Unknown')}
   Summary: {summary}
""")
        return "\n".join(context_parts)

    def _build_aggregation_context(
        self,
        aggregation_data: Optional[Dict[str, Any]],
        sample_cases: List[Dict[str, Any]]
    ) -> str:
        """Build context for aggregation queries."""
        context_parts = ["=== Statistical Summary ===\n"]

        if aggregation_data:
            total = aggregation_data.get("total_cases", 0)
            context_parts.append(f"Total cases analyzed: {total}\n")

            for key, value in aggregation_data.items():
                if key == "total_cases":
                    continue
                if isinstance(value, dict):
                    context_parts.append(f"\n{key.replace('_', ' ').title()}:")
                    # Sort by count descending and show top 10
                    sorted_items = sorted(value.items(), key=lambda x: -x[1])[:10]
                    for k, v in sorted_items:
                        percentage = (v / total * 100) if total > 0 else 0
                        context_parts.append(f"  - {k}: {v} ({percentage:.1f}%)")
                else:
                    context_parts.append(f"{key}: {value}")

        if sample_cases:
            context_parts.append(f"\n\n=== Sample Cases ({len(sample_cases)} shown) ===")
            for i, case in enumerate(sample_cases[:5], 1):
                metadata = case.get("metadata", {})
                summary = case.get('summary', '')[:150]
                context_parts.append(
                    f"\n{i}. #{metadata.get('case_number', 'Unknown')}: {summary}..."
                )

        return "\n".join(context_parts)

    def _call_llm(self, system_prompt: str, user_message: str) -> str:
        """Call the LLM to generate a response."""
        try:
            if self.provider == "openai":
                response = self.llm_client.chat.completions.create(
                    model="gpt-4o",
                    max_tokens=1500,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ]
                )
                return response.choices[0].message.content
            else:
                response = self.llm_client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=1500,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_message}]
                )
                return response.content[0].text
        except Exception as e:
            print(f"Warning: LLM response generation failed: {e}")
            return f"I encountered an error generating a response. Based on the {len(user_message)} cases found, please review the source data for details."

    def _generate_fallback_response(
        self,
        cases: List[Dict[str, Any]],
        query_type: str,
        aggregation_data: Optional[Dict[str, Any]]
    ) -> str:
        """Generate a basic response without LLM."""
        if not cases and not aggregation_data:
            return "No matching data found for your query."

        if query_type == "specific_case" and cases:
            case = cases[0]
            metadata = case.get("metadata", {})
            return f"""Case #{metadata.get('case_number', 'Unknown')}:
- Theme: {metadata.get('theme', 'Unknown')}
- Brand: {metadata.get('brand', 'Unknown')}
- Outcome: {metadata.get('outcome', 'Unknown')}
- Summary: {case.get('summary', 'No summary available')}"""

        if query_type == "aggregation" and aggregation_data:
            parts = [f"Found {aggregation_data.get('total_cases', 0)} total cases."]
            for key, value in aggregation_data.items():
                if isinstance(value, dict):
                    top_items = sorted(value.items(), key=lambda x: -x[1])[:5]
                    parts.append(f"\nTop {key.replace('_', ' ')}:")
                    for k, v in top_items:
                        parts.append(f"  - {k}: {v}")
            return "\n".join(parts)

        return f"Found {len(cases)} cases matching your query. Please review the sources for details."

    def _format_sources(self, cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format cases as source citations."""
        sources = []
        for case in cases:
            metadata = case.get("metadata", {})
            sources.append({
                "id": f"#{metadata.get('case_number', 'Unknown')}",
                "case_number": metadata.get("case_number"),
                "summary": case.get("summary", "")[:200],
                "brand": metadata.get("brand", ""),
                "theme": metadata.get("theme", ""),
                "channel": metadata.get("channel", ""),
                "date": metadata.get("created_at", "")[:10] if metadata.get("created_at") else "",
                "outcome": metadata.get("outcome", "")
            })
        return sources
