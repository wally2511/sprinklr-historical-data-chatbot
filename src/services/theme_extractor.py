"""
Theme extraction service for categorizing conversations.

Provides both keyword-based and LLM-based theme extraction methods.
"""

from typing import Optional, Dict, List


# Theme keywords mapping - covers faith-based conversation topics
THEME_KEYWORDS: Dict[str, List[str]] = {
    "faith": [
        "faith", "believe", "god is real", "spiritual", "christianity",
        "jesus", "christ", "lord", "salvation", "saved", "born again",
        "testimony", "witness", "miracle", "blessing", "blessed"
    ],
    "prayer": [
        "pray", "prayer", "praying", "intercession", "intercede",
        "petition", "supplication", "worship", "praise", "devotion",
        "quiet time", "meditation", "fasting"
    ],
    "grief": [
        "loss", "died", "death", "passed away", "mourning", "grieving",
        "grief", "funeral", "memorial", "bereaved", "widow", "orphan",
        "lost my", "miss them", "heaven", "afterlife"
    ],
    "anxiety": [
        "anxious", "anxiety", "worried", "worry", "panic", "fear",
        "stressed", "stress", "overwhelmed", "nervous", "scared",
        "afraid", "depression", "depressed", "mental health"
    ],
    "doubt": [
        "doubt", "doubting", "questioning", "not sure", "uncertain",
        "struggling to believe", "lost faith", "crisis of faith",
        "why does god", "where is god", "does god exist"
    ],
    "relationships": [
        "marriage", "married", "spouse", "husband", "wife", "divorce",
        "dating", "relationship", "family", "children", "parenting",
        "conflict", "reconciliation", "forgiveness in relationship"
    ],
    "forgiveness": [
        "forgive", "forgiveness", "forgiving", "hurt", "betrayal",
        "resentment", "bitterness", "grudge", "reconcile", "apology",
        "sorry", "guilt", "shame", "confession"
    ],
    "bible_study": [
        "bible", "scripture", "verse", "chapter", "gospel", "psalm",
        "proverbs", "genesis", "revelation", "new testament", "old testament",
        "reading plan", "study", "devotional", "commentary"
    ],
    "evangelism": [
        "evangelism", "share faith", "witness", "testimony", "gospel",
        "spread the word", "mission", "missionary", "outreach", "convert",
        "non-believer", "atheist", "seeker", "curious about"
    ],
    "new_believer": [
        "new believer", "just accepted", "new christian", "recently saved",
        "born again", "baptism", "baptized", "first steps", "new to faith",
        "started believing", "gave my life"
    ],
    "church_hurt": [
        "church hurt", "hurt by church", "bad experience", "toxic church",
        "judgmental", "hypocrite", "hypocritical", "left church",
        "can't go back", "wounded", "spiritual abuse"
    ],
    "addiction": [
        "addiction", "addicted", "substance", "alcohol", "drugs", "porn",
        "pornography", "gambling", "recovery", "sober", "sobriety",
        "aa", "celebrate recovery", "rehab", "relapse"
    ],
    "purpose": [
        "purpose", "calling", "vocation", "direction", "career",
        "what should i do", "god's will", "discernment", "decision",
        "meaning", "meaningless", "lost in life", "fulfillment"
    ],
    "suffering": [
        "suffering", "pain", "illness", "sick", "disease", "cancer",
        "chronic", "hospital", "diagnosis", "why me", "theodicy",
        "problem of evil", "injustice", "tragedy"
    ],
    "teen_faith": [
        "teenager", "teen", "youth", "young", "parents make me",
        "don't believe", "church is boring", "friends don't understand",
        "peer pressure", "school", "college"
    ],
    "skeptic": [
        "skeptic", "skeptical", "atheist", "agnostic", "don't believe",
        "prove", "evidence", "science", "evolution", "logical",
        "rational", "contradiction", "inconsistent"
    ],
}

# All valid themes for reference
VALID_THEMES = list(THEME_KEYWORDS.keys()) + ["general"]


def extract_theme_keywords(conversation: str) -> str:
    """
    Extract theme from conversation using keyword matching.

    This is a fast, cost-effective method that works well for
    categorizing conversations with clear topic indicators.

    Args:
        conversation: The full conversation text

    Returns:
        The detected theme name, or "general" if no clear match
    """
    if not conversation:
        return "general"

    text_lower = conversation.lower()

    # Score each theme based on keyword matches
    scores: Dict[str, int] = {}
    for theme, keywords in THEME_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            if keyword in text_lower:
                # Longer keywords get more weight
                weight = len(keyword.split())
                score += weight
        scores[theme] = score

    # Find the theme with the highest score
    if scores:
        best_theme = max(scores, key=scores.get)
        if scores[best_theme] > 0:
            return best_theme

    return "general"


class ThemeExtractor:
    """
    Theme extractor service with support for both keyword and LLM-based extraction.
    """

    def __init__(self, llm_client=None, method: str = "keyword"):
        """
        Initialize the theme extractor.

        Args:
            llm_client: Optional Anthropic/OpenAI client for LLM-based extraction
            method: "keyword" for fast keyword matching, "llm" for LLM-based
        """
        self.llm_client = llm_client
        self.method = method

    def extract_theme(self, conversation: str) -> str:
        """
        Extract the primary theme from a conversation.

        Args:
            conversation: The full conversation text

        Returns:
            The detected theme name
        """
        if self.method == "llm" and self.llm_client:
            return self._extract_theme_llm(conversation)
        else:
            return extract_theme_keywords(conversation)

    def _extract_theme_llm(self, conversation: str) -> str:
        """
        Extract theme using LLM for more nuanced understanding.

        Args:
            conversation: The conversation text

        Returns:
            The detected theme name
        """
        if not self.llm_client or not conversation:
            return extract_theme_keywords(conversation)

        try:
            themes_list = ", ".join(VALID_THEMES)
            prompt = f"""Analyze this conversation and classify it into ONE of these themes:
{themes_list}

Conversation:
{conversation[:3000]}

Respond with only the theme name, nothing else."""

            response = self.llm_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=50,
                messages=[{"role": "user", "content": prompt}]
            )

            theme = response.content[0].text.strip().lower().replace(" ", "_")

            # Validate the response is a known theme
            if theme in VALID_THEMES:
                return theme
            else:
                # Fallback to keyword extraction
                return extract_theme_keywords(conversation)

        except Exception as e:
            print(f"Warning: LLM theme extraction failed: {e}")
            return extract_theme_keywords(conversation)

    def get_available_themes(self) -> List[str]:
        """Get list of all available themes."""
        return VALID_THEMES.copy()
