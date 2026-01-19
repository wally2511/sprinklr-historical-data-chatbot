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
# Discovered from analysis of 1000 cases + domain knowledge
CASE_TYPES: List[str] = [
    "prayer_request",       # User requesting prayer for themselves or others
    "question",             # General question about faith, theology, or life
    "testimony",            # Sharing a testimony or praise report
    "feedback",             # Feedback about the organization, content, or service
    "encouragement_seeking", # Seeking encouragement, affirmation, or support
    "crisis_support",       # Urgent emotional or spiritual crisis
    "counseling_request",   # Request for deeper guidance or counseling
    "resource_request",     # Asking for books, studies, or materials
    "complaint",            # Complaint or concern about experience
    "greeting",             # Simple greeting or brief interaction
    "appreciation",         # Expressing thanks or appreciation
    "confession",           # Sharing struggles or seeking accountability
    "salvation_inquiry",    # Questions about becoming a Christian
    "general",              # General interaction that doesn't fit other categories
]

# Case Topics - The subject matter being discussed
# Consolidated from LLM analysis of 1000 cases
CASE_TOPICS: List[str] = [
    # Faith & Spiritual Life
    "spiritual_growth",     # Growing in faith, discipleship, devotional life
    "prayer",               # Prayer requests, prayer life, intercession
    "bible_study",          # Scripture, theology, doctrine questions
    "worship",              # Worship, music, praise
    "salvation",            # Coming to faith, understanding gospel
    "doubt",                # Questions about faith, struggles to believe
    "evangelism",           # Sharing faith, witnessing, outreach

    # Relationships & Family
    "relationships",        # Friendships, dating, conflict, community
    "marriage",             # Marital issues, divorce, engagement
    "family",               # Family relationships, parenting, children
    "loneliness",           # Isolation, seeking connection

    # Life Challenges
    "health",               # Physical health, illness, healing
    "mental_health",        # Anxiety, depression, emotional struggles
    "grief",                # Loss, mourning, death of loved one
    "addiction",            # Substance abuse, behavioral addictions
    "finances",             # Money, debt, provision, employment
    "career",               # Work, calling, job transitions

    # Personal Growth
    "guidance",             # Decision-making, discernment, direction
    "purpose",              # Life meaning, calling, destiny
    "forgiveness",          # Forgiving others, receiving forgiveness
    "identity",             # Self-worth, who I am in Christ
    "suffering",            # Making sense of pain, hardship

    # Media & Content
    "media_content",        # Questions about shows, music, content
    "technology",           # AI, apps, digital tools

    # Other
    "politics",             # Political concerns, social issues
    "church",               # Church hurt, finding community, leadership
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
