"""
Mock data module for testing without Sprinklr API access.

Provides realistic sample case data for faith/evangelism conversations.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any
import random


def generate_mock_cases(num_cases: int = 50, days_back: int = 30) -> List[Dict[str, Any]]:
    """
    Generate realistic mock case data for testing.

    Args:
        num_cases: Number of mock cases to generate
        days_back: How many days back to spread the cases

    Returns:
        List of case dictionaries with conversation data
    """
    cases = []
    base_date = datetime.now()

    # Sample conversations covering different themes
    conversation_templates = [
        # Faith questions
        {
            "theme": "faith",
            "messages": [
                {"role": "user", "content": "I've been struggling with my faith lately. How do I know if God is real?"},
                {"role": "agent", "content": "Thank you for sharing that with me. Doubt is a natural part of faith. Many believers throughout history have experienced similar struggles. Can you tell me more about what's been causing you to question?"},
                {"role": "user", "content": "I just don't see evidence of God in my daily life. Everything feels random."},
                {"role": "agent", "content": "I understand. Sometimes God's presence isn't felt in dramatic ways. Many find Him in the small moments - in nature, in kindness from others, in answered prayers. Have you tried keeping a gratitude journal to notice these moments?"},
                {"role": "user", "content": "That's a good idea. I'll try that. Thank you for listening."},
            ],
            "outcome": "positive",
            "topics": ["faith", "doubt", "spiritual struggle"]
        },
        {
            "theme": "prayer",
            "messages": [
                {"role": "user", "content": "How should I pray? I feel like I'm doing it wrong."},
                {"role": "agent", "content": "There's no wrong way to pray! Prayer is simply a conversation with God. You can speak from your heart, just as you would to a close friend. What concerns you about your prayer life?"},
                {"role": "user", "content": "I don't know what to say. I end up just repeating the same things."},
                {"role": "agent", "content": "That's completely normal. You might try the ACTS model: Adoration (praising God), Confession (admitting wrongs), Thanksgiving (gratitude), and Supplication (asking for needs). This can help guide your prayers while keeping them personal."},
                {"role": "user", "content": "ACTS - I like that! I'll try using that structure."},
            ],
            "outcome": "positive",
            "topics": ["prayer", "spiritual practice", "guidance"]
        },
        {
            "theme": "evangelism",
            "messages": [
                {"role": "user", "content": "My friend asked me about my faith and I didn't know what to say. How do I share my faith without being pushy?"},
                {"role": "agent", "content": "That's a great question! The best approach is to share your personal experience - how faith has impacted your life. People connect with authentic stories. What specifically did your friend ask about?"},
                {"role": "user", "content": "She asked why I go to church every week and if I actually believe all of it."},
                {"role": "agent", "content": "You could share what church means to you personally - community, peace, guidance, etc. You don't need to defend every doctrine. Simply share why it matters to you and invite her to experience it sometime if she's curious."},
                {"role": "user", "content": "That makes sense. I was overthinking it. Thanks!"},
            ],
            "outcome": "positive",
            "topics": ["evangelism", "sharing faith", "relationships"]
        },
        {
            "theme": "grief",
            "messages": [
                {"role": "user", "content": "I lost my mother last month. Where is God in all this pain?"},
                {"role": "agent", "content": "I'm so deeply sorry for your loss. Grief is one of the hardest things we experience. Please know that God is with you in your pain, even when it doesn't feel like it. How are you coping day to day?"},
                {"role": "user", "content": "Some days are better than others. I feel guilty when I have a good moment."},
                {"role": "agent", "content": "Those good moments are gifts, not something to feel guilty about. Your mother would want you to find joy again. Grief isn't linear - it comes in waves. Have you been able to connect with others who loved her?"},
                {"role": "user", "content": "Yes, my siblings and I have been talking more. It helps to share memories."},
                {"role": "agent", "content": "That's beautiful. Those shared memories keep her legacy alive. I'm praying for continued healing for you and your family."},
            ],
            "outcome": "supportive",
            "topics": ["grief", "loss", "comfort", "family"]
        },
        {
            "theme": "bible_study",
            "messages": [
                {"role": "user", "content": "Where should I start reading the Bible? It's overwhelming."},
                {"role": "agent", "content": "Great question! Many people start with the Gospel of John - it's written to explain who Jesus is in accessible language. Or you could try Psalms for comfort and worship. Would you like some specific reading plans?"},
                {"role": "user", "content": "A reading plan would be helpful. I tried starting from Genesis but got stuck."},
                {"role": "agent", "content": "That's very common! Genesis has great stories but gets detailed. Try the YouVersion Bible app - they have guided plans for beginners. Start with a 7-day plan on a topic that interests you."},
                {"role": "user", "content": "I'll download that app. Thanks for the recommendation!"},
            ],
            "outcome": "positive",
            "topics": ["bible", "scripture", "new believer", "resources"]
        },
        {
            "theme": "doubt",
            "messages": [
                {"role": "user", "content": "I've been a Christian for years but lately I'm not sure I believe anymore."},
                {"role": "agent", "content": "Thank you for being honest about this. Long-time believers can experience seasons of doubt too. Can you share what's been challenging your beliefs?"},
                {"role": "user", "content": "I see so much suffering in the world. How can a loving God allow this?"},
                {"role": "agent", "content": "This is one of the deepest questions in theology - the problem of evil. Many scholars and believers have wrestled with it. Free will, the fallen nature of our world, and the promise of ultimate redemption are part of the Christian response. Have you read any books on this topic?"},
                {"role": "user", "content": "No, I haven't. Any recommendations?"},
                {"role": "agent", "content": "C.S. Lewis's 'The Problem of Pain' is a classic. Timothy Keller's 'Walking with God Through Pain and Suffering' is also excellent and more recent. Both address this honestly."},
            ],
            "outcome": "resource_shared",
            "topics": ["doubt", "suffering", "theology", "apologetics"]
        },
        {
            "theme": "relationships",
            "messages": [
                {"role": "user", "content": "My husband isn't a believer and it's causing tension in our marriage."},
                {"role": "agent", "content": "That can be really challenging. Mixed-faith marriages require extra patience and respect. How does the tension typically manifest?"},
                {"role": "user", "content": "He gets upset when I want to take the kids to church. He thinks I'm indoctrinating them."},
                {"role": "agent", "content": "This requires open, non-defensive conversation. Perhaps you could explain that you want the kids to learn your values, just as he shares his. Consider compromising - maybe he could share his perspective too, and let the children eventually decide for themselves."},
                {"role": "user", "content": "I never thought of it as sharing both perspectives. That might help him feel less excluded."},
            ],
            "outcome": "positive",
            "topics": ["marriage", "family", "mixed faith", "parenting"]
        },
        {
            "theme": "new_believer",
            "messages": [
                {"role": "user", "content": "I just accepted Jesus last week! What do I do now?"},
                {"role": "agent", "content": "Congratulations! What a wonderful decision! Here are some next steps: 1) Find a local church community, 2) Start reading the Bible (try the Gospel of John), 3) Talk to God daily through prayer, 4) Share your decision with someone you trust. How are you feeling?"},
                {"role": "user", "content": "Excited but also nervous. My family isn't religious."},
                {"role": "agent", "content": "That's understandable. You don't need to announce it dramatically - let your changed life speak first. Over time, they may notice positive changes and become curious. Focus on your own growth right now."},
                {"role": "user", "content": "That's good advice. I'll focus on learning more first."},
            ],
            "outcome": "positive",
            "topics": ["new believer", "conversion", "next steps", "family"]
        },
        {
            "theme": "anxiety",
            "messages": [
                {"role": "user", "content": "I have terrible anxiety and I don't know how to trust God with it."},
                {"role": "agent", "content": "Anxiety is something many believers struggle with. It's not a sign of weak faith. Have you spoken with a counselor or doctor about your anxiety?"},
                {"role": "user", "content": "No, I thought I should just pray more and it would go away."},
                {"role": "agent", "content": "Prayer is important, but God also works through medicine and counseling. Seeking professional help is not a lack of faith - it's wisdom. Consider both spiritual practices AND professional support. Philippians 4:6-7 encourages us to bring our anxieties to God, but He also provides earthly helpers."},
                {"role": "user", "content": "I hadn't thought of it that way. Maybe I'll look into talking to someone."},
            ],
            "outcome": "positive",
            "topics": ["anxiety", "mental health", "faith", "healing"]
        },
        {
            "theme": "forgiveness",
            "messages": [
                {"role": "user", "content": "Someone hurt me deeply and I can't forgive them. Does that make me a bad Christian?"},
                {"role": "agent", "content": "Forgiveness is one of the hardest things we're called to do. It's a process, not an instant event. Struggling with it doesn't make you a bad Christian - it makes you human. What happened, if you're comfortable sharing?"},
                {"role": "user", "content": "A family member betrayed my trust in a major way. Every time I see them, the anger comes back."},
                {"role": "agent", "content": "That's completely understandable. Remember, forgiveness doesn't mean forgetting or trusting them again immediately. It's releasing the burden of bitterness for your own peace. It often happens gradually. Have you talked to a pastor or counselor about this?"},
                {"role": "user", "content": "Not yet. I feel ashamed that I can't just forgive like Jesus says."},
                {"role": "agent", "content": "There's no shame in struggling. Even Peter, one of Jesus' closest disciples, needed to be taught about forgiveness multiple times. Consider speaking with someone - processing the hurt is part of healing."},
            ],
            "outcome": "supportive",
            "topics": ["forgiveness", "hurt", "healing", "family"]
        },
        {
            "theme": "purpose",
            "messages": [
                {"role": "user", "content": "I feel lost in life. How do I find God's purpose for me?"},
                {"role": "agent", "content": "Feeling lost is more common than you might think. God's purpose often unfolds gradually. What are you passionate about? What gives you joy? What are you naturally good at?"},
                {"role": "user", "content": "I love helping kids, and I'm good at teaching. But I work in finance."},
                {"role": "agent", "content": "Those passions might be pointing somewhere! You don't necessarily need to quit your job, but could you volunteer with youth groups, Sunday school, or tutoring? Sometimes purpose is found outside our day job while we earn a living."},
                {"role": "user", "content": "I never thought of volunteering as part of my purpose. That's a great idea!"},
            ],
            "outcome": "positive",
            "topics": ["purpose", "calling", "vocation", "volunteering"]
        },
        {
            "theme": "church_hurt",
            "messages": [
                {"role": "user", "content": "I was hurt by people at my old church and now I can't bring myself to go back to any church."},
                {"role": "agent", "content": "I'm so sorry that happened. Unfortunately, churches are made up of imperfect people who sometimes cause real harm. Your hesitation is completely valid. What happened, if you feel comfortable sharing?"},
                {"role": "user", "content": "There was gossip and judgment when I went through my divorce. I felt so unwelcome."},
                {"role": "agent", "content": "That's heartbreaking. Church should be a place of support, especially during difficult times. Not all churches are the same. When you're ready, you might try a different church with a different culture. But there's no rush - you can maintain your faith outside a building while you heal."},
                {"role": "user", "content": "It helps to hear that I don't have to rush back. Maybe someday I'll try again."},
            ],
            "outcome": "supportive",
            "topics": ["church hurt", "community", "healing", "divorce"]
        },
        {
            "theme": "addiction",
            "messages": [
                {"role": "user", "content": "I'm struggling with addiction and feel too ashamed to ask God for help."},
                {"role": "agent", "content": "Thank you for your courage in sharing this. God's love isn't based on our perfection - He meets us in our struggles. There is no shame in bringing this to Him. Are you getting any support or treatment?"},
                {"role": "user", "content": "I've been hiding it from everyone. You're the first person I've told."},
                {"role": "agent", "content": "Taking this first step of telling someone is huge. You don't have to face this alone. Please consider reaching out to a professional or a group like Celebrate Recovery, which is faith-based. Would you like help finding resources?"},
                {"role": "user", "content": "Yes, I think I need to talk to someone in person. Thank you for not judging me."},
                {"role": "agent", "content": "You are deeply loved, no matter what. I'm praying for your journey to freedom. Here's a link to find Celebrate Recovery meetings near you..."},
            ],
            "outcome": "resource_shared",
            "topics": ["addiction", "recovery", "shame", "help"]
        },
        {
            "theme": "skeptic",
            "messages": [
                {"role": "user", "content": "I'm an atheist but I'm curious about Christianity. Can you explain what you believe without trying to convert me?"},
                {"role": "agent", "content": "Of course! I respect your curiosity. At its core, Christianity teaches that God created us, humanity chose to separate from God through sin, and Jesus - God's son - came to restore that relationship through his death and resurrection. What specifically are you curious about?"},
                {"role": "user", "content": "Why do Christians believe Jesus was divine and not just a good teacher?"},
                {"role": "agent", "content": "Great question. Christians believe in Jesus' divinity because of his claims about himself (recorded in the Gospels), his resurrection from the dead, and the testimony of eyewitnesses who were willing to die for this belief. C.S. Lewis argued that Jesus' claims leave only three options: he was a liar, a lunatic, or truly Lord."},
                {"role": "user", "content": "Interesting. I'll have to think about that. Thanks for explaining without being preachy."},
            ],
            "outcome": "positive",
            "topics": ["apologetics", "skeptic", "curiosity", "explanation"]
        },
        {
            "theme": "teen_faith",
            "messages": [
                {"role": "user", "content": "I'm 16 and my parents make me go to church but I'm not sure I believe what they believe."},
                {"role": "agent", "content": "It's completely normal at your age to question the faith you were raised with. This is actually an important part of developing your own beliefs. What specifically are you unsure about?"},
                {"role": "user", "content": "Everything feels like rules. Don't do this, don't do that. What's the point?"},
                {"role": "agent", "content": "I understand that frustration. Faith can feel like a list of don'ts when it should be about a relationship. At its heart, Christianity is about God's love for you and finding purpose and meaning. The 'rules' are meant to protect and guide, not restrict. Have you talked to your parents or a youth leader about how you're feeling?"},
                {"role": "user", "content": "No, I'm afraid they'll be disappointed."},
                {"role": "agent", "content": "Many parents appreciate honest questions more than fake compliance. You might be surprised. Your doubt doesn't mean you're bad - it means you're thinking deeply. That's valuable."},
            ],
            "outcome": "positive",
            "topics": ["youth", "doubt", "family", "rules"]
        },
    ]

    for i in range(num_cases):
        # Pick a random conversation template
        template = random.choice(conversation_templates)

        # Generate a random date within the range
        random_days = random.randint(0, days_back)
        case_date = base_date - timedelta(days=random_days)

        # Create variations in the messages
        messages = template["messages"].copy()

        case = {
            "id": f"CASE-{10000 + i}",
            "created_at": case_date.isoformat(),
            "updated_at": case_date.isoformat(),
            "status": random.choice(["resolved", "closed"]),
            "channel": random.choice(["facebook", "instagram", "twitter", "web_chat"]),
            "brand": random.choice(["Brand1", "Radio Christian Voice", "Sharek Online"]),
            "messages": messages,
            "theme": template["theme"],
            "outcome": template["outcome"],
            "topics": template["topics"],
            "message_count": len(messages),
        }

        cases.append(case)

    return cases


def get_mock_case_by_id(case_id: str) -> Dict[str, Any] | None:
    """Get a single mock case by ID."""
    cases = generate_mock_cases(100)
    for case in cases:
        if case["id"] == case_id:
            return case
    return None


# Generate a fixed set of cases for consistent testing
MOCK_CASES = generate_mock_cases(50, days_back=30)
