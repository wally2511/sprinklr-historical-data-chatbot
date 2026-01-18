# Pending Improvements: Chatbot Response Quality

## Status: Ready for Implementation

## Problem Statement

User reports:
1. **Only 5 sources returned** for broad analytical queries (expected ~100)
2. **Responses are vague** and lacking in detail/context

---

## Root Cause Analysis

### Issue 1: Limited Sources (5 instead of 100)

**File:** `src/agents/orchestrator.py` line 138

```python
# Aggregation queries hardcode n_results=5
cases = self.vector_store.search(
    query=query_plan.semantic_query,
    n_results=5,  # <-- HARDCODED - should use query_plan.result_count
    ...
)
```

When a query like "What are the obstacles to sharing faith?" is classified as **aggregation**, it only fetches 5 sample cases to accompany statistics.

### Issue 2: Vague Responses

**File:** `src/agents/response_agent.py`

1. **Truncated context** (line 216): Summaries truncated to 300 chars for broad searches
2. **Missing rich data**: `full_conversation`, `description`, `subject` not passed for broad queries
3. **Low token limit**: `max_tokens=1500` constrains response detail
4. **Generic prompts**: Broad search prompt lacks explicit detail instructions

---

## Implementation Plan

### Step 1: Increase Aggregation Sample Cases

**File:** `src/agents/orchestrator.py`

Change line 138 from hardcoded `5` to use config or query plan:

```python
# Before
n_results=5

# After
n_results=min(query_plan.result_count, config.MAX_CONTEXT_CASES_BROAD)
```

### Step 2: Enhance Context for Broad Queries

**File:** `src/agents/response_agent.py`

Modify `_build_summary_context()` (lines 205-224) to include more fields:

```python
# Add to context:
- full_conversation (or first 2000 chars)
- description
- subject
- outcome
- sentiment
```

Or: Create new `_build_enriched_context()` method for broad queries that includes more detail.

### Step 3: Increase Token Limits

**File:** `src/agents/response_agent.py`

Change `max_tokens=1500` to `max_tokens=2500` on lines 305, 315, and other generate calls.

### Step 4: Enhance Broad Search Prompt

**File:** `src/agents/response_agent.py`

Update `BROAD_SEARCH_PROMPT` (lines 43-47) to explicitly request:
- Specific examples with case numbers
- Direct quotes from conversations
- Detailed patterns with evidence
- Concrete recommendations

### Step 5: Increase Default Result Counts

**File:** `src/config.py`

Increase to 100 sources:
```python
MAX_CONTEXT_CASES_BROAD = 100  # Was 50
```

**File:** `src/agents/query_agent.py`

Ensure broad search requests 100 results (already set, verify line 327).

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/agents/orchestrator.py` | Line 138: Use config/plan result_count instead of hardcoded 5 |
| `src/agents/response_agent.py` | Enhance `_build_summary_context()`, increase max_tokens, improve prompts |
| `src/config.py` | Increase MAX_CONTEXT_CASES_BROAD to 100 |

---

## Verification

1. Restart chatbot after changes
2. Test query: "What are the obstacles to sharing faith?"
3. Expected: 50+ sources returned (vs 5 before)
4. Expected: Response includes specific case citations and quotes
5. Test query: "What are the most common themes?" - verify aggregation still works

---

## User Preferences

- **Source count:** 100 sources for broad queries
- **Detail level:** Include conversation excerpts for richer responses

## Trade-offs Accepted

| Change | Benefit | Cost |
|--------|---------|------|
| 100 sources (was 5) | Comprehensive analysis | More ChromaDB queries |
| Conversation excerpts | Quotes & specific details | Larger prompts, more tokens |
| Higher max_tokens | Longer, detailed responses | ~$0.01 more per query |
