"""
Analyze cases from SQLite database to discover natural case_type and case_topic patterns.

This script reads directly from the messages SQLite database (converted from XLSX exports)
to analyze case patterns for a specific brand. This allows more targeted taxonomy discovery
than analyzing from ChromaDB which may have mixed brands.

Usage:
    python scripts/analyze_taxonomy_from_sqlite.py --cases 2000 --brand "Brand1" --use-llm
    python scripts/analyze_taxonomy_from_sqlite.py --cases 500 --brand "Brand1" --output data/brand1_taxonomy.json
"""

import sys
import os
import json
import argparse
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import Counter, defaultdict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import config


def get_cases_from_sqlite(
    db_path: str,
    brand: Optional[str] = None,
    max_cases: int = 2000
) -> List[Dict[str, Any]]:
    """
    Load cases from SQLite database, reconstructing conversations from messages.

    Args:
        db_path: Path to SQLite database
        brand: Optional brand name to filter by
        max_cases: Maximum number of cases to load

    Returns:
        List of case dictionaries with reconstructed conversations
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Build query based on brand filter
    if brand:
        query = """
            SELECT case_number, content, role, sender, created_time_epoch, brand
            FROM messages
            WHERE brand = ?
            ORDER BY case_number, created_time_epoch ASC
        """
        cursor = conn.cursor()
        cursor.execute(query, (brand,))
    else:
        query = """
            SELECT case_number, content, role, sender, created_time_epoch, brand
            FROM messages
            ORDER BY case_number, created_time_epoch ASC
        """
        cursor = conn.cursor()
        cursor.execute(query)

    # Group messages by case_number
    cases_dict: Dict[int, List[Dict]] = defaultdict(list)
    for row in cursor.fetchall():
        case_number = row["case_number"]
        if case_number:
            cases_dict[case_number].append({
                "content": row["content"] or "",
                "role": row["role"] or "user",
                "sender": row["sender"] or "Unknown",
                "created_time": row["created_time_epoch"],
                "brand": row["brand"] or ""
            })

    conn.close()

    # Convert to list of cases
    cases = []
    for case_number in list(cases_dict.keys())[:max_cases]:
        messages = cases_dict[case_number]
        if messages:
            # Format conversation
            conversation_lines = []
            for msg in messages:
                role = msg["role"].upper()
                sender = msg["sender"]
                content = msg["content"]
                if sender:
                    conversation_lines.append(f"{role} ({sender}): {content}")
                else:
                    conversation_lines.append(f"{role}: {content}")

            conversation = "\n".join(conversation_lines)

            cases.append({
                "case_number": case_number,
                "conversation": conversation,
                "message_count": len(messages),
                "brand": messages[0]["brand"] if messages else ""
            })

    return cases


def analyze_cases_with_llm(
    cases: List[Dict[str, Any]],
    llm_client,
    provider: str = "openai",
    batch_size: int = 50
) -> Dict[str, Any]:
    """
    Analyze cases using LLM to discover natural taxonomy patterns.

    Args:
        cases: List of case dictionaries with conversations
        llm_client: OpenAI or Anthropic client
        provider: LLM provider ("openai" or "anthropic")
        batch_size: Number of cases to analyze per LLM call

    Returns:
        Dictionary with discovered case_types and case_topics
    """
    all_case_types = Counter()
    all_case_topics = Counter()
    type_topic_mapping = {}  # Maps case_type to list of topics
    individual_classifications = []  # Store individual case classifications

    # Process cases in batches
    total_batches = (len(cases) - 1) // batch_size + 1

    for i in range(0, len(cases), batch_size):
        batch = cases[i:i+batch_size]
        batch_num = i // batch_size + 1
        print(f"Analyzing batch {batch_num}/{total_batches}...")

        # Format cases for analysis
        case_summaries = []
        for j, case in enumerate(batch):
            conversation = case.get("conversation", "")[:2000]  # Truncate
            case_number = case.get("case_number", "unknown")

            case_summaries.append(f"""
Case #{case_number}:
{conversation}
---""")

        cases_text = "\n".join(case_summaries)

        prompt = f"""Analyze these {len(batch)} customer service cases from a faith-based organization.

For EACH case, identify:
1. Case Type - the nature/intent of the interaction. Common types include:
   - prayer_request: User requesting prayer
   - question: Asking about faith, theology, or life
   - testimony: Sharing praise report or answered prayer
   - feedback: Feedback about content or service
   - encouragement_seeking: Needing encouragement or support
   - crisis_support: Urgent emotional/spiritual crisis
   - counseling_request: Seeking deeper guidance
   - resource_request: Asking for materials/resources
   - greeting: Simple hello/acknowledgment
   - appreciation: Expressing thanks
   - salvation_inquiry: Questions about becoming a Christian
   - general: Doesn't fit other categories

2. Case Topic - the subject matter being discussed. Common topics include:
   - spiritual_growth, prayer, bible_study, worship, salvation, doubt, evangelism
   - relationships, marriage, family, loneliness
   - health, mental_health, grief, addiction, finances, career
   - guidance, purpose, forgiveness, identity, suffering
   - media_content, technology, politics, church, general

After analyzing all cases, provide a JSON summary with:
- case_types: Array of unique case types discovered (sorted by frequency)
- case_topics: Array of unique topics discovered (sorted by frequency)
- type_topic_mapping: Object mapping each case_type to its common topics
- individual_cases: Array of objects with case_number, case_type, case_topic for each case

Cases to analyze:
{cases_text}

Output ONLY valid JSON (no markdown, no explanation):
{{"case_types": [...], "case_topics": [...], "type_topic_mapping": {{}}, "individual_cases": [...]}}"""

        try:
            if provider == "openai":
                response = llm_client.chat.completions.create(
                    model="gpt-4o",
                    max_tokens=4000,
                    messages=[{"role": "user", "content": prompt}]
                )
                response_text = response.choices[0].message.content
            else:
                response = llm_client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4000,
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

                # Store individual classifications
                for case_class in batch_result.get("individual_cases", []):
                    individual_classifications.append({
                        "case_number": case_class.get("case_number"),
                        "case_type": case_class.get("case_type", "").lower().replace(" ", "_"),
                        "case_topic": case_class.get("case_topic", "").lower().replace(" ", "_")
                    })

        except Exception as e:
            print(f"Warning: Batch analysis failed: {e}")
            continue

    # Count individual classifications for more accurate frequency
    individual_type_counts = Counter()
    individual_topic_counts = Counter()
    for ic in individual_classifications:
        if ic.get("case_type"):
            individual_type_counts[ic["case_type"]] += 1
        if ic.get("case_topic"):
            individual_topic_counts[ic["case_topic"]] += 1

    # Convert Counters to sorted lists
    return {
        "case_types": [ct for ct, _ in individual_type_counts.most_common()],
        "case_topics": [t for t, _ in individual_topic_counts.most_common()],
        "case_type_counts": dict(individual_type_counts),
        "case_topic_counts": dict(individual_topic_counts),
        "type_topic_mapping": {
            ct: [t for t, _ in topics.most_common(10)]
            for ct, topics in type_topic_mapping.items()
        },
        "individual_classifications": individual_classifications
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
        "prayer_request": ["pray for", "prayer request", "please pray", "praying for", "need prayer", "lift up"],
        "question": ["question", "wondering", "curious", "what is", "how do", "why do", "can you explain", "?"],
        "crisis_support": ["crisis", "emergency", "urgent", "suicidal", "end my life", "want to die", "desperate"],
        "testimony": ["testimony", "praise report", "thankful", "god answered", "miracle", "he healed", "praise god"],
        "feedback": ["feedback", "suggestion", "love this", "great content", "amazing show"],
        "resource_request": ["resource", "recommend", "book", "study material", "where can i find"],
        "counseling_request": ["need to talk", "can i speak", "counselor", "guidance", "advice"],
        "greeting": ["hello", "hi there", "good morning", "good evening", "hey"],
        "appreciation": ["thank you", "thanks", "appreciate", "grateful", "bless you", "god bless"],
        "salvation_inquiry": ["how to be saved", "become a christian", "accept jesus", "born again"],
    }

    # Define keyword patterns for topics
    topic_patterns = {
        "health": ["health", "sick", "illness", "disease", "medical", "cancer", "surgery", "doctor", "healing"],
        "family": ["family", "parents", "children", "kids", "spouse", "husband", "wife", "marriage", "divorce"],
        "relationships": ["relationship", "friend", "dating", "lonely", "conflict"],
        "finances": ["money", "financial", "job", "debt", "bills", "unemploy"],
        "career": ["career", "work", "boss", "coworker", "job", "promotion"],
        "spiritual_growth": ["faith", "bible", "scripture", "pray", "church", "grow", "spiritual"],
        "grief": ["grief", "loss", "died", "death", "mourning", "passed away", "funeral"],
        "mental_health": ["anxiety", "anxious", "worry", "fear", "depress", "hopeless", "panic", "stress"],
        "addiction": ["addict", "alcohol", "drug", "porn", "gambling", "substance"],
        "salvation": ["salvation", "saved", "accept", "believe", "convert", "born again"],
        "doubt": ["doubt", "question", "struggle", "faith crisis"],
        "guidance": ["guidance", "direction", "decision", "discern", "will of god", "next step"],
        "purpose": ["purpose", "meaning", "calling", "why am i", "destiny"],
        "forgiveness": ["forgive", "forgiveness", "hurt", "resentment", "bitterness"],
    }

    case_type_counts = Counter()
    topic_counts = Counter()

    for case in cases:
        conversation = case.get("conversation", "").lower()

        # Detect case type
        detected_type = "general"
        for ct, keywords in case_type_patterns.items():
            if any(kw in conversation for kw in keywords):
                detected_type = ct
                break
        case_type_counts[detected_type] += 1

        # Detect topics (can have multiple)
        topics_found = False
        for topic, keywords in topic_patterns.items():
            if any(kw in conversation for kw in keywords):
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


def generate_taxonomy_report(analysis: Dict[str, Any], output_path: str, brand: str = "") -> None:
    """
    Generate a human-readable report from the analysis.

    Args:
        analysis: Analysis results dictionary
        output_path: Path to write the report
        brand: Brand name for report title
    """
    brand_title = f" ({brand})" if brand else ""
    total_cases = analysis.get("total_cases_analyzed", 0)

    report_lines = [
        "=" * 70,
        f"CASE TAXONOMY ANALYSIS REPORT{brand_title}",
        f"Total Cases Analyzed: {total_cases}",
        "=" * 70,
        "",
        "CASE TYPES (by frequency)",
        "-" * 50,
    ]

    type_counts = analysis.get("case_type_counts", {})
    for ct, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        pct = count / total_cases * 100 if total_cases > 0 else 0
        report_lines.append(f"  {ct:30} {count:6} ({pct:5.1f}%)")

    report_lines.extend([
        "",
        "CASE TOPICS (by frequency)",
        "-" * 50,
    ])

    topic_counts = analysis.get("case_topic_counts", {})
    for topic, count in sorted(topic_counts.items(), key=lambda x: -x[1]):
        pct = count / total_cases * 100 if total_cases > 0 else 0
        report_lines.append(f"  {topic:30} {count:6} ({pct:5.1f}%)")

    if "type_topic_mapping" in analysis:
        report_lines.extend([
            "",
            "TYPE-TOPIC MAPPING (most common topics per type)",
            "-" * 50,
        ])
        for ct, topics in analysis.get("type_topic_mapping", {}).items():
            if topics:
                report_lines.append(f"  {ct}:")
                for t in topics[:5]:
                    report_lines.append(f"    - {t}")

    report_lines.extend([
        "",
        "=" * 70,
        "RECOMMENDED TAXONOMY FOR src/taxonomy.py",
        "=" * 70,
        "",
        "# Copy these into src/taxonomy.py",
        "",
        "CASE_TYPES = [",
    ])

    # Top case types (include all with > 1% of cases or top 15)
    threshold = total_cases * 0.01 if total_cases > 0 else 0
    included_types = [ct for ct, count in type_counts.items()
                      if count >= threshold or ct in list(type_counts.keys())[:15]]
    for ct in included_types[:15]:
        report_lines.append(f'    "{ct}",')
    report_lines.append("]")

    report_lines.extend([
        "",
        "CASE_TOPICS = [",
    ])

    # Top case topics
    included_topics = [t for t, count in topic_counts.items()
                       if count >= threshold or t in list(topic_counts.keys())[:25]]
    for topic in included_topics[:25]:
        report_lines.append(f'    "{topic}",')
    report_lines.append("]")

    report_text = "\n".join(report_lines)

    # Save report
    report_path = output_path.replace(".json", "_report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_text)

    print(f"\nReport saved to: {report_path}")
    print("\n" + report_text)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze cases from SQLite database to discover taxonomy patterns"
    )
    parser.add_argument(
        "--cases", type=int, default=2000,
        help="Number of cases to analyze (default: 2000)"
    )
    parser.add_argument(
        "--brand", type=str, default="Brand1",
        help="Brand name to filter by (default: Brand1)"
    )
    parser.add_argument(
        "--output", type=str, default="data/sqlite_taxonomy_analysis.json",
        help="Output file path for JSON results"
    )
    parser.add_argument(
        "--db", type=str, default="data/messages.db",
        help="Path to SQLite database (default: data/messages.db)"
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
    parser.add_argument(
        "--batch-size", type=int, default=50,
        help="Number of cases per LLM batch (default: 50)"
    )

    args = parser.parse_args()

    # Check database exists
    if not Path(args.db).exists():
        print(f"Error: Database not found: {args.db}")
        print("Run 'python scripts/xlsx_to_sqlite.py' to create it from XLSX files.")
        sys.exit(1)

    print(f"Loading cases from SQLite database...")
    print(f"  Database: {args.db}")
    print(f"  Brand filter: {args.brand or 'None (all brands)'}")
    print(f"  Max cases: {args.cases}")
    print()

    # Load cases
    cases = get_cases_from_sqlite(
        db_path=args.db,
        brand=args.brand if args.brand else None,
        max_cases=args.cases
    )
    print(f"Loaded {len(cases)} cases for analysis")

    if len(cases) == 0:
        print("Error: No cases found with the specified filters.")
        sys.exit(1)

    # Analyze
    if args.use_llm:
        print(f"\nAnalyzing with {args.provider} LLM...")
        print(f"Batch size: {args.batch_size} cases per API call")

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

        analysis = analyze_cases_with_llm(
            cases, llm_client, args.provider, args.batch_size
        )
    else:
        print("\nAnalyzing with keyword patterns (use --use-llm for better results)...")
        analysis = analyze_with_keyword_patterns(cases)

    # Add metadata
    analysis["total_cases_analyzed"] = len(cases)
    analysis["brand"] = args.brand or "all"
    analysis["database"] = args.db

    # Ensure output directory exists
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save JSON results
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2)
    print(f"\nJSON results saved to: {output_path}")

    # Generate report
    generate_taxonomy_report(analysis, str(output_path), args.brand or "")

    print("\n" + "=" * 70)
    print("NEXT STEPS:")
    print("1. Review the taxonomy report above")
    print("2. Update src/taxonomy.py with the recommended values")
    print("3. Re-run ingestion with classification:")
    print("   python scripts/ingest_data.py --live --xlsx-messages --max-cases 1000")
    print("=" * 70)


if __name__ == "__main__":
    main()
