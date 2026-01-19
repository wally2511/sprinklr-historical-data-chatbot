"""
Case Taxonomy for Classification.

This module defines the valid case_type and case_topic values
used for classifying customer service cases.

To update this taxonomy:
1. Run: python scripts/analyze_cases_for_taxonomy.py --cases 1000 --use-llm
2. Review the output report
3. Update the lists below with discovered categories
"""

from typing import List


# Case Types - The nature/intent of the interaction
# Refined from LLM analysis of 1000 Brand1 cases (2024)
CASE_TYPES: List[str] = [
    # High frequency (>5% of cases)
    "testimony",            # Sharing a testimony, praise report, or faith story (12.7%)
    "encouragement_seeking", # Seeking encouragement, affirmation, or support (10.7%)
    "question",             # General question about faith, theology, or life (10.2%)
    "prayer_request",       # User requesting prayer for themselves or others (7.5%)
    "appreciation",         # Expressing thanks or appreciation (7.3%)
    "greeting",             # Simple greeting or brief interaction (5.6%)
    "resource_request",     # Asking for books, studies, materials, or content (5.2%)
    "feedback",             # Feedback about the organization, content, or service (4.8%)

    # Medium frequency (1-5% of cases)
    "crisis_support",       # Urgent emotional or spiritual crisis (2.9%)
    "counseling_request",   # Request for deeper guidance or counseling (1.2%)

    # Lower frequency (<1% of cases)
    "salvation_inquiry",    # Questions about becoming a Christian
    "evangelism_guidance",  # Help with sharing faith or witnessing
    "complaint",            # Complaint or concern about experience
    "confession",           # Sharing struggles or seeking accountability
    "general",              # General interaction that doesn't fit other categories
]

# Case Topics - The subject matter being discussed
# Refined from LLM analysis of 1000 Brand1 cases (2024)
CASE_TOPICS: List[str] = [
    # High frequency (>3% of cases)
    "evangelism",           # Sharing faith, witnessing, outreach, gospel (20.4%)
    "spiritual_growth",     # Growing in faith, discipleship, devotional life (6.0%)
    "relationships",        # Friendships, dating, conflict, community (5.3%)
    "media_content",        # Questions about shows, music, content, programs (4.7%)
    "prayer",               # Prayer requests, prayer life, intercession (3.9%)
    "faith",                # General faith topics, belief, trust in God (3.2%)

    # Medium frequency (1-3% of cases)
    "worship",              # Worship, music, praise (1.7%)
    "identity",             # Self-worth, who I am in Christ (1.7%)
    "doubt",                # Questions about faith, struggles to believe (1.4%)
    "community",            # Christian community, fellowship, connection (1.3%)
    "mental_health",        # Anxiety, depression, emotional struggles (1.1%)
    "bible_study",          # Scripture, theology, doctrine questions (1.0%)
    "church",               # Church hurt, finding community, leadership (1.0%)
    "technology",           # AI, apps, digital tools (1.0%)

    # Lower frequency (<1% of cases)
    "family",               # Family relationships, parenting, children
    "forgiveness",          # Forgiving others, receiving forgiveness
    "salvation",            # Coming to faith, understanding gospel
    "health",               # Physical health, illness, healing
    "suffering",            # Making sense of pain, hardship
    "guidance",             # Decision-making, discernment, direction
    "finances",             # Money, debt, provision, employment
    "loneliness",           # Isolation, seeking connection
    "addiction",            # Substance abuse, behavioral addictions
    "marriage",             # Marital issues, divorce, engagement
    "grief",                # Loss, mourning, death of loved one
    "career",               # Work, calling, job transitions
    "purpose",              # Life meaning, calling, destiny
    "politics",             # Political concerns, social issues
    "general",              # Topic doesn't fit other categories
]


def get_case_types() -> List[str]:
    """Get the list of valid case types."""
    return CASE_TYPES.copy()


def get_case_topics() -> List[str]:
    """Get the list of valid case topics."""
    return CASE_TOPICS.copy()


def is_valid_case_type(case_type: str) -> bool:
    """Check if a case type is valid."""
    return case_type.lower() in [ct.lower() for ct in CASE_TYPES]


def is_valid_case_topic(case_topic: str) -> bool:
    """Check if a case topic is valid."""
    return case_topic.lower() in [ct.lower() for ct in CASE_TOPICS]


def normalize_case_type(case_type: str) -> str:
    """Normalize a case type to match the canonical list."""
    case_type_lower = case_type.lower().replace(" ", "_")
    for ct in CASE_TYPES:
        if ct.lower() == case_type_lower:
            return ct
    return "general"


def normalize_case_topic(case_topic: str) -> str:
    """Normalize a case topic to match the canonical list."""
    case_topic_lower = case_topic.lower().replace(" ", "_")
    for topic in CASE_TOPICS:
        if topic.lower() == case_topic_lower:
            return topic
    return "general"
