def analyze(text: str) -> dict:
    return {
        "waste_types": ["plastic", "organic"],
        "location": "near school",
        "duration_days": 5,
        "severity": "high",
        "issue_type": "uncollected waste",
        "summary": "Mixed plastic and organic waste uncollected near a school for five days.",
    }

def retrieve(analysis: dict) -> dict:
    return {
        "sources": ["organic_waste.pdf", "collection.pdf"],
        "evidence": [
            "Organic waste should be collected within 48 hours to limit odour and pests.",
            "Waste near schools and public facilities should be prioritised for collection.",
        ],
    }

def decide(analysis: dict, retrieval: dict) -> dict:
    return {
        "priority": "HIGH",
        "recommendation": "Immediate inspection and collection",
        "explanation": "Waste has been uncollected for 5 days near a school with odour reported.",
        "sources": retrieval["sources"],
        "human_review": True,
    }