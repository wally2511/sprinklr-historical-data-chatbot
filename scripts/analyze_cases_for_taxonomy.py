"""
Analyze existing cases to discover natural case_type and case_topic patterns.

This script analyzes cases from ChromaDB to identify common patterns
that can be used to create a taxonomy for classification.

Usage:
    python scripts/analyze_cases_for_taxonomy.py --cases 1000
    python scripts/analyze_cases_for_taxonomy.py --cases 500 --output taxonomy_report.json
"""

import sys
import os
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any
from collections import Counter

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from vector_store import VectorStore
from config import config


def analyze_cases_with_llm(
    cases: List[Dict[str, Any]],
    llm_client,
    provider: str = "openai",
    batch_size: int = 50
) -> Dict[str, Any]:
    """
    Analyze cases using LLM to discover natural taxonomy patterns.

    Args:
        cases: List of case dictionaries from ChromaDB
        llm_client: OpenAI or Anthropic client
        provider: LLM provider ("openai" or "anthropic")
        batch_size: Number of cases to analyze per LLM call

    Returns:
        Dictionary with discovered case_types and case_topics
    """
    all_case_types = Counter()
    all_case_topics = Counter()
    type_topic_mapping = {}  # Maps case_type to list of topics

    # Process cases in batches
    for i in range(0, len(cases), batch_size):
        batch = cases[i:i+batch_size]
        print(f"Analyzing batch {i//batch_size + 1}/{(len(cases)-1)//batch_size + 1}...")

        # Format cases for analysis
        case_summaries = []
        for j, case in enumerate(batch):
            metadata = case.get("metadata", {})
            summary = case.get("summary", "")
            conversation = metadata.get("full_conversation", "")[:1500]  # Truncate
            theme = metadata.get("theme", "")

            case_summaries.append(f"""
Case {i+j+1}:
Theme: {theme}
Summary: {summary}
Conversation excerpt: {conversation}
---""")

        cases_text = "\n".join(case_summaries)

        prompt = f"""Analyze these {len(batch)} customer service cases from a faith-based organization.

For each case, identify:
1. Case Type - the nature of the interaction (e.g., prayer_request, question, crisis_support, testimony, feedback, complaint, resource_request, etc.)
2. Case Topic - the specific subject matter (e.g., health, family, relationships, finances, career, spiritual_growth, grief, addiction, etc.)

After analyzing all cases, provide a JSON summary with:
- case_types: Array of unique case types discovered, sorted by frequency (most common first)
- case_topics: Array of unique topics discovered, sorted by frequency (most common first)
- type_topic_mapping: Object mapping each case_type to its most common topics

Cases to analyze:
{cases_text}

Output ONLY valid JSON:
{{"case_types": ["type1", "type2", ...], "case_topics": ["topic1", "topic2", ...], "type_topic_mapping": {{"type1": ["topic1", "topic2"], ...}}}}"""

        try:
            if provider == "openai":
                response = llm_client.chat.completions.create(
                    model="gpt-4o",
                    max_tokens=2000,
                    messages=[{"role": "user", "content": prompt}]
                )
                response_text = response.choices[0].message.content
            else:
                response = llm_client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=2000,
                    messages=[{"role": "user", "content": prompt}]
                )
                response_text = response.content[0].text

            # Parse JSON from response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                batch_result = json.loads(json_match.group())

                # Accumulate results
                for ct in batch_result.get("case_types", []):
                    all_case_types[ct.lower().replace(" ", "_")] += 1
                for topic in batch_result.get("case_topics", []):
                    all_case_topics[topic.lower().replace(" ", "_")] += 1

                # Merge type-topic mapping
                for ct, topics in batch_result.get("type_topic_mapping", {}).items():
                    ct_normalized = ct.lower().replace(" ", "_")
                    if ct_normalized not in type_topic_mapping:
                        type_topic_mapping[ct_normalized] = Counter()
                    for t in topics:
                        type_topic_mapping[ct_normalized][t.lower().replace(" ", "_")] += 1

        except Exception as e:
            print(f"Warning: Batch analysis failed: {e}")
            continue

    # Convert Counters to sorted lists
    return {
        "case_types": [ct for ct, _ in all_case_types.most_common()],
        "case_topics": [t for t, _ in all_case_topics.most_common()],
        "case_type_counts": dict(all_case_types),
        "case_topic_counts": dict(all_case_topics),
        "type_topic_mapping": {
            ct: [t for t, _ in topics.most_common(10)]
            for ct, topics in type_topic_mapping.items()
        }
    }


def analyze_with_keyword_patterns(cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Fallback: Analyze cases using keyword patterns (no LLM required).

    Args:
        cases: List of case dictionaries

    Returns:
        Dictionary with discovered patterns based on keywords
    """
    # Define keyword patterns for case types
    case_type_patterns = {
        "prayer_request": ["pray", "prayer", "praying", "intercede"],
        "question": ["question", "wondering", "curious", "what is", "how do", "why do", "can you explain"],
        "crisis_support": ["crisis", "emergency", "urgent", "help me", "struggling", "desperate", "suicidal"],
        "testimony": ["testimony", "praise", "thankful", "god did", "miracle", "answered prayer", "blessed"],
        "feedback": ["feedback", "suggestion", "comment", "thought you should know"],
        "resource_request": ["resource", "recommend", "book", "study", "material", "where can i find"],
        "counseling_request": ["counsel", "advice", "guidance", "talk to someone", "need help with"],
        "complaint": ["complaint", "unhappy", "disappointed", "upset", "frustrated"],
    }

    # Define keyword patterns for topics
    topic_patterns = {
        "health": ["health", "sick", "illness", "disease", "medical", "cancer", "surgery", "doctor", "healing"],
        "family": ["family", "parents", "children", "kids", "spouse", "husband", "wife", "marriage", "divorce"],
        "relationships": ["relationship", "friend", "dating", "lonely", "conflict", "forgiveness"],
        "finances": ["money", "financial", "job", "debt", "bills", "unemploy"],
        "career": ["career", "work", "boss", "coworker", "job", "promotion", "calling"],
        "spiritual_growth": ["faith", "bible", "scripture", "pray", "church", "grow", "spiritual"],
        "grief": ["grief", "loss", "died", "death", "mourning", "passed away", "funeral"],
        "anxiety": ["anxiety", "anxious", "worry", "fear", "scared", "panic", "stress"],
        "depression": ["depress", "hopeless", "sad", "empty", "numb", "dark"],
        "addiction": ["addict", "alcohol", "drug", "porn", "gambling", "substance"],
        "salvation": ["salvation", "saved", "accept", "believe", "convert", "born again"],
        "doubt": ["doubt", "question", "struggle", "faith crisis", "believe"],
        "guidance": ["guidance", "direction", "decision", "discern", "will of god", "next step"],
        "peace": ["peace", "calm", "rest", "comfort", "serenity"],
        "purpose": ["purpose", "meaning", "calling", "why am i", "destiny"],
    }

    case_type_counts = Counter()
    topic_counts = Counter()

    for case in cases:
        summary = case.get("summary", "").lower()
        conversation = case.get("metadata", {}).get("full_conversation", "").lower()
        text = f"{summary} {conversation}"

        # Detect case type
        for ct, keywords in case_type_patterns.items():
            if any(kw in text for kw in keywords):
                case_type_counts[ct] += 1
                break
        else:
            case_type_counts["general"] += 1

        # Detect topics (can have multiple)
        topics_found = False
        for topic, keywords in topic_patterns.items():
            if any(kw in text for kw in keywords):
                topic_counts[topic] += 1
                topics_found = True

        if not topics_found:
            topic_counts["general"] += 1

    return {
        "case_types": [ct for ct, _ in case_type_counts.most_common()],
        "case_topics": [t for t, _ in topic_counts.most_common()],
        "case_type_counts": dict(case_type_counts),
        "case_topic_counts": dict(topic_counts),
        "method": "keyword_patterns"
    }


def generate_taxonomy_report(analysis: Dict[str, Any], output_path: str) -> None:
    """
    Generate a human-readable report from the analysis.

    Args:
        analysis: Analysis results dictionary
        output_path: Path to write the report
    """
    report_lines = [
        "=" * 60,
        "CASE TAXONOMY ANALYSIS REPORT",
        "=" * 60,
        "",
        "CASE TYPES (by frequency)",
        "-" * 40,
    ]

    for ct, count in sorted(
        analysis.get("case_type_counts", {}).items(),
        key=lambda x: -x[1]
    ):
        report_lines.append(f"  {ct}: {count}")

    report_lines.extend([
        "",
        "CASE TOPICS (by frequency)",
        "-" * 40,
    ])

    for topic, count in sorted(
        analysis.get("case_topic_counts", {}).items(),
        key=lambda x: -x[1]
    ):
        report_lines.append(f"  {topic}: {count}")

    if "type_topic_mapping" in analysis:
        report_lines.extend([
            "",
            "TYPE-TOPIC MAPPING",
            "-" * 40,
        ])
        for ct, topics in analysis.get("type_topic_mapping", {}).items():
            report_lines.append(f"  {ct}:")
            for t in topics[:5]:
                report_lines.append(f"    - {t}")

    report_lines.extend([
        "",
        "=" * 60,
        "RECOMMENDED TAXONOMY FOR taxonomy.py",
        "=" * 60,
        "",
        "CASE_TYPES = [",
    ])

    for ct in analysis.get("case_types", [])[:15]:  # Top 15
        report_lines.append(f'    "{ct}",')
    report_lines.append("]")

    report_lines.extend([
        "",
        "CASE_TOPICS = [",
    ])

    for topic in analysis.get("case_topics", [])[:25]:  # Top 25
        report_lines.append(f'    "{topic}",')
    report_lines.append("]")

    report_text = "\n".join(report_lines)

    # Save report
    report_path = output_path.replace(".json", "_report.txt")
    with open(report_path, "w") as f:
        f.write(report_text)

    print(f"\nReport saved to: {report_path}")
    print("\n" + report_text)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze cases to discover taxonomy patterns"
    )
    parser.add_argument(
        "--cases", type=int, default=1000,
        help="Number of cases to analyze (default: 1000)"
    )
    parser.add_argument(
        "--output", type=str, default="data/taxonomy_analysis.json",
        help="Output file path for JSON results"
    )
    parser.add_argument(
        "--use-llm", action="store_true",
        help="Use LLM for analysis (requires API key)"
    )
    parser.add_argument(
        "--provider", type=str, default="openai",
        choices=["openai", "anthropic"],
        help="LLM provider to use (default: openai)"
    )

    args = parser.parse_args()

    print(f"Loading cases from ChromaDB...")
    vector_store = VectorStore()

    total_cases = vector_store.get_case_count()
    print(f"Total cases in store: {total_cases}")

    if total_cases == 0:
        print("Error: No cases found in vector store. Run ingestion first.")
        sys.exit(1)

    # Load cases
    cases = vector_store.get_all_cases(limit=args.cases)
    print(f"Loaded {len(cases)} cases for analysis")

    # Analyze
    if args.use_llm:
        print(f"\nAnalyzing with {args.provider} LLM...")

        # Initialize LLM client
        if args.provider == "openai":
            if not config.validate_openai_config():
                print("Error: OpenAI API key not configured")
                sys.exit(1)
            import openai
            llm_client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
        else:
            if not config.validate_anthropic_config():
                print("Error: Anthropic API key not configured")
                sys.exit(1)
            import anthropic
            llm_client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

        analysis = analyze_cases_with_llm(cases, llm_client, args.provider)
    else:
        print("\nAnalyzing with keyword patterns (use --use-llm for better results)...")
        analysis = analyze_with_keyword_patterns(cases)

    # Add metadata
    analysis["total_cases_analyzed"] = len(cases)
    analysis["total_cases_in_store"] = total_cases

    # Ensure output directory exists
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save JSON results
    with open(output_path, "w") as f:
        json.dump(analysis, f, indent=2)
    print(f"\nJSON results saved to: {output_path}")

    # Generate report
    generate_taxonomy_report(analysis, str(output_path))

    print("\n" + "=" * 60)
    print("NEXT STEPS:")
    print("1. Review the taxonomy report above")
    print("2. Update src/taxonomy.py with the recommended values")
    print("3. Re-run ingestion with classification enabled")
    print("=" * 60)


if __name__ == "__main__":
    main()
