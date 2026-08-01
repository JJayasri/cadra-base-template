"""Intent router — keyword-heuristic classifier with a clean interface for LLM swap."""

from dataclasses import dataclass

# Domain keywords — if any match, the question is in-domain
DOMAIN_KEYWORDS = {
    "sales", "target", "volume", "revenue", "unit", "stock", "promotion",
    "discount", "distributor", "sku", "brand", "category", "product",
    "mrp", "price", "territory", "region", "market", "customer",
    "glucojoy", "sparkclean", "chairaja", "morninggold", "teabliss",
    "nutribite", "crispking", "snacko", "munchmore", "cruncho",
    "silknaturals", "herbacare", "shinelux", "powerfoam", "washwell",
    "fmcg", "primary sales", "stockout", "inventory", "supply",
    "monthly", "weekly", "quarter", "year", "fy", "inr",
    "mumbai", "delhi", "bangalore", "bengaluru", "kolkata", "chennai",
    "hyderabad", "pune", "ahmedabad", "jaipur", "lucknow", "patna", "guwahati",
    "north", "south", "east", "west",
    "spike", "dip", "decline", "drop", "increase", "decrease", "trend",
    "data", "report", "figure", "number", "performance",
    "month", "week", "q1", "q2", "q3", "q4",
}

# WHAT keywords — ordered by specificity (longer phrases first)
WHAT_PATTERNS = [
    "what were", "what is", "what are", "what was",
    "how many", "how much",
    "show me", "show the",
    "tell me", "list",
    "give me", "give the",
    "what's",
]

# WHY keywords
WHY_PATTERNS = [
    "why did", "why is", "why was", "why are", "why does", "why do",
    "what caused", "what led", "what is the reason",
    "reason for", "root cause",
    "what explains",
]

# WHAT_TO_DO keywords
WHAT_TO_DO_PATTERNS = [
    "what should", "what can we", "what would you",
    "recommend", "suggestion", "suggest",
    "what to do", "how to improve", "how to fix",
    "next step", "action item", "action plan",
    "what do you advise",
]


@dataclass
class IntentResult:
    intent: str
    confidence: float


def classify_intent(question: str) -> IntentResult:
    cleaned = question.lower().strip()
    if not cleaned:
        return IntentResult(intent="OUT_OF_DOMAIN", confidence=0.0)

    # Check if in-domain at all
    has_domain_keyword = any(kw in cleaned for kw in DOMAIN_KEYWORDS)
    if not has_domain_keyword:
        return IntentResult(intent="OUT_OF_DOMAIN", confidence=0.8)

    # Score each intent
    what_score = _score_patterns(cleaned, WHAT_PATTERNS)
    why_score = _score_patterns(cleaned, WHY_PATTERNS)
    what_to_do_score = _score_patterns(cleaned, WHAT_TO_DO_PATTERNS)

    scores = {
        "WHAT": what_score,
        "WHY": why_score,
        "WHAT_TO_DO": what_to_do_score,
    }

    best_intent = max(scores, key=scores.get)
    best_score = scores[best_intent]

    # Tie-break: if scores are equal, prefer WHAT as default
    if best_score == 0:
        best_intent = "WHAT"
        best_score = 0.5
    else:
        best_score = min(0.5 + best_score * 0.1, 0.95)

    return IntentResult(intent=best_intent, confidence=round(best_score, 2))


def _score_patterns(cleaned: str, patterns: list[str]) -> int:
    score = 0
    for pat in patterns:
        if pat in cleaned:
            # Longer patterns get more weight
            score += len(pat.split())
    return score