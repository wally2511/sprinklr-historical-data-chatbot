"""
Case classification service for categorizing cases by type and topic.

Uses OpenAI for efficient classification of conversations into
case_type (nature of interaction) and case_topic (subject matter).
"""

import json
import re
from typing import Dict, Optional, Any

from taxonomy import CASE_TYPES, CASE_TOPICS, normalize_case_type, normalize_case_topic


# Keyword patterns for fast fallback classification
# Refined based on Brand1 case analysis (2024)
CASE_TYPE_KEYWORDS: Dict[str, list] = {
    "testimony": ["testimony", "praise report", "thankful", "god answered", "miracle", "he healed", "praise god",
                  "thank you lord", "i accepted", "i gave my life", "i was saved", "god did", "amazing testimony"],
    "encouragement_seeking": ["need encouragement", "feeling down", "struggling", "please encourage", "need support",
                              "going through", "hard time", "difficult", "help me", "strength", "praying for me"],
    "question": ["question", "wondering", "curious", "what is", "how do", "why do", "can you explain", "?",
                 "what does", "is it wrong", "does god", "can a christian"],
    "prayer_request": ["pray for", "prayer request", "please pray", "praying for", "need prayer", "lift up",
                       "intercede", "prayer warrior"],
    "appreciation": ["thank you", "thanks", "appreciate", "grateful", "bless you", "god bless", "blessed by",
                     "love the show", "great program", "wonderful message"],
    "greeting": ["hello", "hi there", "good morning", "good evening", "hey", "howdy", "greetings",
                 "peace be with you", "shalom"],
    "resource_request": ["resource", "recommend", "book", "study material", "where can i find", "looking for",
                         "send me", "can i get", "how do i access", "download", "bible", "devotional"],
    "feedback": ["feedback", "suggestion", "just wanted to say", "love this", "great content", "amazing show",
                 "the program", "the episode", "keep up"],
    "crisis_support": ["crisis", "emergency", "urgent", "suicidal", "end my life", "want to die", "desperate",
                       "can't go on", "hopeless", "no reason to live", "in danger"],
    "counseling_request": ["need to talk", "can i speak", "counselor", "guidance", "advice", "talk to someone",
                           "need help", "please call", "can someone call"],
    "salvation_inquiry": ["how to be saved", "become a christian", "accept jesus", "what must i do", "born again",
                          "accept christ", "give my life to jesus", "salvation"],
    "evangelism_guidance": ["share my faith", "witnessing", "tell others", "evangelize", "share the gospel",
                            "reach my family", "preach", "how to share"],
    "complaint": ["complaint", "unhappy", "disappointed", "frustrated", "upset", "terrible", "wrong", "issue"],
    "confession": ["confession", "i've been struggling", "need to confess", "accountability", "admit", "sin"],
}

CASE_TOPIC_KEYWORDS: Dict[str, list] = {
    # High frequency topics (based on Brand1 analysis)
    "evangelism": ["share my faith", "witnessing", "non-believer", "gospel", "testimony", "preach", "evangelize",
                   "share the gospel", "reach others", "tell others about", "unbeliever", "lost", "witness"],
    "spiritual_growth": ["grow in faith", "devotional", "closer to god", "spiritual journey", "discipleship",
                         "mature", "grow spiritually", "deepen my faith"],
    "relationships": ["relationship", "friend", "dating", "conflict", "community", "neighbor", "coworker"],
    "media_content": ["show", "episode", "movie", "video", "content", "program", "broadcast", "radio",
                      "podcast", "channel", "watch", "listen"],
    "prayer": ["prayer", "pray", "praying", "intercession", "petition", "pray for"],
    "faith": ["faith", "believe", "trust", "trust in god", "believer", "faithful"],

    # Medium frequency topics
    "worship": ["worship", "praise", "music", "song", "hymn", "sing", "praise god"],
    "identity": ["identity", "self-worth", "who am i", "insecure", "value", "in christ"],
    "doubt": ["doubt", "questioning", "struggle to believe", "faith crisis", "not sure", "confused"],
    "community": ["community", "fellowship", "brothers and sisters", "church family", "gathering"],
    "mental_health": ["anxiety", "depression", "anxious", "depressed", "panic", "mental health",
                      "overwhelmed", "stress", "fear", "worry"],
    "bible_study": ["bible", "scripture", "verse", "theology", "word of god", "chapter", "book of"],
    "church": ["church", "pastor", "congregation", "church hurt", "ministry", "service", "attend"],
    "technology": ["app", "website", "ai", "chatbot", "technology", "digital", "online", "internet"],

    # Lower frequency topics
    "family": ["family", "parents", "children", "kids", "son", "daughter", "mother", "father"],
    "forgiveness": ["forgive", "forgiveness", "hurt", "resentment", "bitterness", "grudge"],
    "salvation": ["salvation", "saved", "accept jesus", "born again", "eternal life", "accept christ"],
    "health": ["health", "sick", "illness", "cancer", "surgery", "doctor", "hospital", "healing", "medical"],
    "suffering": ["suffering", "pain", "why me", "tragedy", "hardship", "trial", "difficult"],
    "guidance": ["guidance", "direction", "decision", "discernment", "what should i do", "god's will"],
    "finances": ["money", "financial", "debt", "bills", "unemployed", "job loss", "provision"],
    "loneliness": ["lonely", "alone", "isolated", "no one", "by myself"],
    "addiction": ["addiction", "addicted", "alcohol", "drug", "porn", "gambling", "recovery", "sober"],
    "marriage": ["marriage", "spouse", "husband", "wife", "divorce", "engaged", "wedding"],
    "grief": ["grief", "loss", "died", "death", "mourning", "passed away", "funeral", "miss them"],
    "career": ["career", "work", "boss", "job", "promotion", "calling", "employment"],
    "purpose": ["purpose", "meaning", "calling", "why am i here", "destiny"],
    "politics": ["politics", "government", "election", "leader", "country"],
}


def classify_by_keywords(conversation: str) -> Dict[str, str]:
    """
    Classify a conversation using keyword matching (fast fallback).

    Args:
        conversation: The conversation text to classify

    Returns:
        Dictionary with case_type and case_topic
    """
    text_lower = conversation.lower() if conversation else ""

    # Score case types
    type_scores: Dict[str, int] = {}
    for case_type, keywords in CASE_TYPE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            type_scores[case_type] = score

    # Score case topics
    topic_scores: Dict[str, int] = {}
    for topic, keywords in CASE_TOPIC_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            topic_scores[topic] = score

    # Get best matches
    case_type = max(type_scores, key=type_scores.get) if type_scores else "general"
    case_topic = max(topic_scores, key=topic_scores.get) if topic_scores else "general"

    return {
        "case_type": case_type,
        "case_topic": case_topic
    }


class CaseClassifier:
    """
    Classifies conversations into case_type and case_topic categories.

    Uses OpenAI for accurate classification with keyword-based fallback.
    """

    def __init__(
        self,
        openai_client: Optional[Any] = None,
        model: str = "gpt-4o-mini"
    ):
        """
        Initialize the case classifier.

        Args:
            openai_client: OpenAI client for LLM classification
            model: OpenAI model to use (default: gpt-4o-mini for speed/cost)
        """
        self.openai_client = openai_client
        self.model = model

    def classify(self, conversation: str) -> Dict[str, str]:
        """
        Classify a conversation into case_type and case_topic.

        Args:
            conversation: The full conversation text

        Returns:
            Dictionary with "case_type" and "case_topic" keys
        """
        if not conversation or not conversation.strip():
            return {"case_type": "general", "case_topic": "general"}

        # Try LLM classification first
        if self.openai_client:
            try:
                return self._classify_with_llm(conversation)
            except Exception as e:
                print(f"Warning: LLM classification failed: {e}")
                # Fall through to keyword classification

        # Fallback to keyword classification
        return classify_by_keywords(conversation)

    def _classify_with_llm(self, conversation: str) -> Dict[str, str]:
        """
        Classify using OpenAI LLM.

        Args:
            conversation: The conversation text

        Returns:
            Classification dictionary
        """
        # Truncate long conversations
        conv_truncated = conversation[:3000]

        prompt = f"""Classify this customer service conversation from a faith-based organization.

CASE TYPES (the nature/intent of the interaction):
{', '.join(CASE_TYPES)}

CASE TOPICS (the subject matter being discussed):
{', '.join(CASE_TOPICS)}

CONVERSATION:
{conv_truncated}

Return ONLY valid JSON with exactly this format:
{{"case_type": "one_of_the_types_above", "case_topic": "one_of_the_topics_above"}}"""

        response = self.openai_client.chat.completions.create(
            model=self.model,
            max_tokens=50,
            temperature=0,  # Deterministic output
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = response.choices[0].message.content.strip()

        # Parse JSON from response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())

            # Normalize and validate
            case_type = normalize_case_type(result.get("case_type", "general"))
            case_topic = normalize_case_topic(result.get("case_topic", "general"))

            return {
                "case_type": case_type,
                "case_topic": case_topic
            }

        # If parsing fails, use keyword fallback
        return classify_by_keywords(conversation)

    def classify_batch(
        self,
        conversations: list,
        batch_size: int = 10
    ) -> list:
        """
        Classify multiple conversations efficiently.

        Args:
            conversations: List of conversation texts
            batch_size: Number of conversations to process in parallel

        Returns:
            List of classification dictionaries
        """
        results = []
        for conv in conversations:
            results.append(self.classify(conv))
        return results
