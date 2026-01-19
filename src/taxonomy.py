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
# Examples: prayer_request, question, crisis_support, testimony, etc.
CASE_TYPES: List[str] = [
    "prayer_request",       # User requesting prayer for themselves or others
    "question",             # General question about faith, theology, or life
    "crisis_support",       # Urgent emotional or spiritual crisis
    "testimony",            # Sharing a testimony or praise report
    "counseling_request",   # Request for deeper guidance or counseling
    "resource_request",     # Asking for books, studies, or materials
    "feedback",             # Feedback about the organization or service
    "complaint",            # Complaint or concern about experience
    "encouragement",        # Seeking encouragement or affirmation
    "confession",           # Sharing struggles or seeking accountability
    "salvation_inquiry",    # Questions about becoming a Christian
    "volunteer_inquiry",    # Interest in volunteering or serving
    "general",              # General interaction that doesn't fit other categories
]

# Case Topics - The subject matter being discussed
# Examples: health, family, relationships, finances, etc.
CASE_TOPICS: List[str] = [
    "health",               # Physical health, illness, healing
    "family",               # Family relationships, parenting, children
    "relationships",        # Friendships, dating, conflict
    "marriage",             # Marital issues, divorce, engagement
    "finances",             # Money, debt, provision, employment
    "career",               # Work, calling, job transitions
    "spiritual_growth",     # Growing in faith, discipleship
    "grief",                # Loss, mourning, death of loved one
    "anxiety",              # Worry, fear, stress, panic
    "depression",           # Hopelessness, sadness, mental health
    "addiction",            # Substance abuse, behavioral addictions
    "salvation",            # Coming to faith, understanding gospel
    "doubt",                # Questions about faith, struggles to believe
    "guidance",             # Decision-making, discernment, direction
    "peace",                # Finding rest, calm, comfort
    "purpose",              # Life meaning, calling, destiny
    "forgiveness",          # Forgiving others, receiving forgiveness
    "suffering",            # Making sense of pain, hardship
    "church",               # Church hurt, finding community
    "parenting",            # Raising children, youth issues
    "identity",             # Self-worth, who I am in Christ
    "sin",                  # Struggling with sin, temptation
    "bible_study",          # Understanding scripture, theology
    "prayer_life",          # How to pray, prayer practice
    "evangelism",           # Sharing faith, witnessing
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
