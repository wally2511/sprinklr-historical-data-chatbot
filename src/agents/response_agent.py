"""
Response Agent for generating context-appropriate responses.

This agent processes retrieved cases and generates responses tailored
to the query type (specific case analysis, broad synthesis, aggregation).
"""

from typing import List, Dict, Any, Optional, TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from .query_agent import CompoundQueryPlan


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
Synthesize information across all provided cases to give a comprehensive, detailed answer.

Your response MUST include:
1. **Specific examples with case numbers** - Reference at least 3-5 specific cases (e.g., "In Case #12345...")
2. **Direct quotes from conversations** - Include actual quotes from the case data when relevant
3. **Detailed patterns with evidence** - Don't just name patterns; describe them with supporting case examples
4. **Concrete recommendations** - Provide actionable insights based on the data

Guidelines:
- Be thorough and detailed in your analysis
- Cite case numbers frequently when referencing examples
- Use quotes and specific details from conversations to support your points
- Identify both common themes AND notable exceptions or unique cases
- Be empathetic when discussing sensitive topics like grief, doubt, or mental health
- If you have many cases, organize your response with clear sections or categories"""

    AGGREGATION_PROMPT = """You are presenting statistical data about customer service cases from faith-based organizations.
Present the data clearly and highlight the most significant findings.
Provide context and insights about what the numbers mean.
If sample cases are provided, reference them to illustrate the statistics."""

    FILTERED_SEARCH_PROMPT = """You are analyzing customer service cases that match specific filter criteria from faith-based organizations.
You have access to full conversation transcripts for detailed analysis.

Your role is to:
1. Analyze the conversations in detail, noting specific exchanges
2. Identify patterns and common themes within the filtered results
3. Provide specific examples with direct quotes when relevant
4. Offer actionable insights based on the conversations

Be empathetic when discussing sensitive topics and cite case numbers when referencing examples."""

    DATABASE_QUERY_PROMPT = """You are presenting database query results from customer service cases from faith-based organizations.

Your role is to:
1. Present counts and percentages clearly in a numbered list or table format
2. Highlight the most significant findings (top categories, notable patterns)
3. Reference example cases to illustrate each category when provided
4. Provide actionable insights based on the data distribution
5. Use clear formatting with bold for category names and percentages

Format example for "top 4 prayer request types":
**Top 4 Prayer Request Types:**

1. **Health** - 234 cases (34%)
   - Example: Case #12345 - User requested prayer for cancer diagnosis...

2. **Family** - 189 cases (27%)
   - Example: Case #23456 - Parent seeking prayer for wayward child...

Be empathetic when discussing sensitive topics like health crises, grief, or mental health."""

    # Compound search prompts for multi-step strategies
    COMPOUND_PROMPT_HIERARCHICAL = """You are synthesizing results from a multi-step search strategy for customer service cases from faith-based organizations.

Structure your response as:
1. **Overview**: High-level findings from statistics (if available)
2. **Key Patterns**: Synthesized insights from case summaries
3. **Detailed Examples**: Specific cases with quotes and analysis
4. **Insights & Recommendations**: Actionable takeaways

Guidelines:
- Cite case numbers when referencing specific examples (e.g., "In Case #12345...")
- Be empathetic when discussing sensitive topics like grief, doubt, or mental health
- Connect statistics to real examples for concrete understanding
- Prioritize actionable insights over raw data summaries"""

    COMPOUND_PROMPT_COMPARATIVE = """You are comparing different segments of customer service data from faith-based organizations.

Structure your response as:
1. **Comparison Overview**: Key differences and similarities at a glance
2. **Segment A Analysis**: Findings for the first group with examples
3. **Segment B Analysis**: Findings for the second group with examples
4. **Key Differences**: What stands out between segments
5. **Recommendations**: Actionable insights from the comparison

Guidelines:
- Cite case numbers and be specific about which segment each example comes from
- Use concrete examples to illustrate differences
- Be balanced in analysis, highlighting both strengths and areas for improvement
- Be empathetic when discussing sensitive topics"""

    COMPOUND_PROMPT_TIMELINE = """You are analyzing changes over time in customer service data from faith-based organizations.

Structure your response as:
1. **Timeline Overview**: High-level trends observed
2. **Earlier Period**: Patterns and examples from the first period
3. **Later Period**: Patterns and examples from the later period
4. **Notable Changes**: What shifted and potential reasons
5. **Implications**: What this means going forward

Guidelines:
- Cite case numbers and dates when referencing examples
- Highlight both quantitative changes (if statistics available) and qualitative shifts
- Speculate thoughtfully on reasons for changes
- Be empathetic when discussing sensitive topics"""

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
            context = self._build_detailed_context(cases)  # Full transcripts for filtered search
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
        """Build enriched context for broad queries with summaries and conversation excerpts."""
        if not cases:
            return "No matching cases found."

        context_parts = [f"Found {len(cases)} relevant cases:\n"]
        for i, case in enumerate(cases, 1):
            metadata = case.get("metadata", {})
            date_str = metadata.get('created_at', '')[:10] if metadata.get('created_at') else 'N/A'
            summary = case.get('summary', 'No summary')

            # Get additional fields for richer context
            subject = metadata.get('subject', '')
            description = metadata.get('description', '')
            outcome = metadata.get('outcome', 'Unknown')
            sentiment = metadata.get('sentiment', 'Unknown')
            full_conversation = metadata.get('full_conversation', '')

            # Truncate conversation to first 2000 chars for context
            if full_conversation and len(full_conversation) > 2000:
                full_conversation = full_conversation[:1997] + "..."

            # Build case entry
            case_entry = f"""
{i}. Case #{metadata.get('case_number', 'Unknown')} ({date_str})
   Brand: {metadata.get('brand', 'Unknown')} | Theme: {metadata.get('theme', 'Unknown')} | Channel: {metadata.get('channel', 'Unknown')}
   Outcome: {outcome} | Sentiment: {sentiment}"""

            if subject:
                case_entry += f"\n   Subject: {subject}"

            case_entry += f"\n   Summary: {summary}"

            if description and description != summary:
                desc_truncated = description[:500] + "..." if len(description) > 500 else description
                case_entry += f"\n   Description: {desc_truncated}"

            if full_conversation:
                case_entry += f"\n   Conversation Excerpt:\n   {full_conversation}"

            context_parts.append(case_entry)

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
                    max_tokens=2500,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ]
                )
                return response.choices[0].message.content
            else:
                response = self.llm_client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=2500,
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

    def process_compound(
        self,
        plan: "CompoundQueryPlan",
        step_results: List[Dict[str, Any]],
        cases: List[Dict[str, Any]],
        aggregations: Dict[str, Dict[str, Any]],
        original_query: str
    ) -> ResponseResult:
        """
        Generate a response from compound (multi-step) search results.

        Args:
            plan: The CompoundQueryPlan that was executed
            step_results: Results from each step (with step metadata)
            cases: All collected cases (deduplicated)
            aggregations: All aggregation data keyed by step purpose
            original_query: The user's original query

        Returns:
            ResponseResult with synthesized response
        """
        # Select prompt based on synthesis strategy
        if plan.synthesis_strategy == "comparative":
            system_prompt = self.COMPOUND_PROMPT_COMPARATIVE
        elif plan.synthesis_strategy == "timeline":
            system_prompt = self.COMPOUND_PROMPT_TIMELINE
        else:
            system_prompt = self.COMPOUND_PROMPT_HIERARCHICAL

        # Build structured context
        context_parts = []

        # Add aggregation data
        if aggregations:
            context_parts.append("=== STATISTICAL DATA ===")
            for purpose, data in aggregations.items():
                context_parts.append(f"\n**{purpose}:**")
                context_parts.append(self._format_aggregation_data(data))

        # Separate cases by detail level
        summary_cases = [c for c in cases if c.get("_detail_level") == "summary"]
        detailed_cases = [c for c in cases if c.get("_detail_level") == "full_conversation"]

        # Add case summaries
        if summary_cases:
            context_parts.append(f"\n=== CASE SUMMARIES ({len(summary_cases)} cases) ===")
            context_parts.append(self._build_compound_summary_context(summary_cases))

        # Add detailed transcripts
        if detailed_cases:
            context_parts.append(f"\n=== DETAILED TRANSCRIPTS ({len(detailed_cases)} cases) ===")
            context_parts.append(self._build_compound_detailed_context(detailed_cases))

        context = "\n".join(context_parts)

        # Generate response
        user_message = f"""Question: {original_query}

{context}

Please provide a comprehensive answer that synthesizes the statistical data (if available) with the specific case examples. Structure your response according to the format guidelines."""

        if self.llm_client:
            response_text = self._call_llm(system_prompt, user_message)
        else:
            response_text = self._generate_compound_fallback(cases, aggregations)

        return ResponseResult(
            response=response_text,
            cases_found=len(cases),
            query_type="compound",
            sources=self._format_sources(cases)
        )

    def _format_aggregation_data(self, data: Dict[str, Any]) -> str:
        """Format aggregation data for compound context."""
        parts = []

        # Handle database query format (has "total" instead of "total_cases")
        total = data.get("total") or data.get("total_cases", 0)
        parts.append(f"Total cases: {total}")

        # Show what field was grouped by if available
        if data.get("group_by"):
            parts.append(f"Grouped by: {data['group_by']}")

        # Show filters if applied
        if data.get("filters_applied"):
            filters_str = ", ".join(f"{k}={v}" for k, v in data["filters_applied"].items())
            parts.append(f"Filters: {filters_str}")

        for key, value in data.items():
            if key in ("total_cases", "total", "group_by", "filters_applied"):
                continue
            if isinstance(value, dict):
                parts.append(f"\n{key.replace('_', ' ').title()}:")
                # Sort by count if values are integers, otherwise just iterate
                try:
                    sorted_items = sorted(value.items(), key=lambda x: -x[1])[:10]
                except TypeError:
                    sorted_items = list(value.items())[:10]
                for k, v in sorted_items:
                    if isinstance(v, (int, float)) and total > 0:
                        pct = (v / total * 100)
                        parts.append(f"  - {k}: {v} ({pct:.1f}%)")
                    else:
                        parts.append(f"  - {k}: {v}")
            elif key not in ("total_cases", "total", "group_by", "filters_applied"):
                parts.append(f"{key}: {value}")

        return "\n".join(parts)

    def _build_compound_summary_context(self, cases: List[Dict[str, Any]]) -> str:
        """Build context with summaries for compound queries."""
        context_parts = []
        for i, case in enumerate(cases, 1):
            metadata = case.get("metadata", {})
            date_str = metadata.get('created_at', '')[:10] if metadata.get('created_at') else 'N/A'
            summary = case.get('summary', 'No summary')
            step_purpose = case.get('_step_purpose', 'General')

            # Truncate long summaries
            if len(summary) > 300:
                summary = summary[:297] + "..."

            context_parts.append(f"""
{i}. Case #{metadata.get('case_number', 'Unknown')} ({date_str}) [From: {step_purpose}]
   Brand: {metadata.get('brand', 'Unknown')} | Theme: {metadata.get('theme', 'Unknown')} | Channel: {metadata.get('channel', 'Unknown')}
   Summary: {summary}
""")
        return "\n".join(context_parts)

    def _build_compound_detailed_context(self, cases: List[Dict[str, Any]]) -> str:
        """Build context with full details for compound queries."""
        context_parts = []
        for case in cases:
            metadata = case.get("metadata", {})
            step_purpose = case.get('_step_purpose', 'Detailed Analysis')

            context_parts.append(f"""
=== Case #{metadata.get('case_number', 'Unknown')} ===
[Purpose: {step_purpose}]
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

    def _generate_compound_fallback(
        self,
        cases: List[Dict[str, Any]],
        aggregations: Dict[str, Dict[str, Any]]
    ) -> str:
        """Generate a basic compound response without LLM."""
        parts = []

        if aggregations:
            parts.append("**Statistical Overview:**")
            for purpose, data in aggregations.items():
                total = data.get("total_cases", 0)
                parts.append(f"\n{purpose}:")
                parts.append(f"- Total cases: {total}")
                for key, value in data.items():
                    if isinstance(value, dict) and key != "total_cases":
                        top_items = sorted(value.items(), key=lambda x: -x[1])[:5]
                        for k, v in top_items:
                            parts.append(f"  - {k}: {v}")

        if cases:
            parts.append(f"\n**Cases Found ({len(cases)} total):**")
            for i, case in enumerate(cases[:10], 1):
                metadata = case.get("metadata", {})
                parts.append(f"\n{i}. Case #{metadata.get('case_number', 'Unknown')}")
                parts.append(f"   Theme: {metadata.get('theme', 'Unknown')}")
                summary = case.get('summary', '')[:150]
                if summary:
                    parts.append(f"   {summary}...")

        if not parts:
            return "No data found for your compound query."

        return "\n".join(parts)
