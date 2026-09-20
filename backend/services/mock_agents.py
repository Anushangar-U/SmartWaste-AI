def analyze(text: str) -> dict:
    normalized = text.lower()
    high_risk_terms = (
        "school",
        "hospital",
        "chemical",
        "hazardous",
        "toxic",
        "syringe",
        "river",
    )
    high_risk = any(term in normalized for term in high_risk_terms)

    return {
        "waste_types": ["plastic", "organic"],
        "location": "near school" if "school" in normalized else "residential street",
        "duration_days": 5 if "five" in normalized or "5" in normalized else 2,
        "severity": "high" if high_risk else "medium",
        "issue_type": "uncollected waste",
        "summary": text.strip(),
    }


def retrieve(analysis: dict) -> dict:
    evidence = [
        {
            "chunk_id": "mock_organic_p1_c01",
            "source": "organic_waste.pdf",
            "page": 1,
            "text": "Organic waste should be collected promptly to limit odour and pests.",
            "score": 0.82,
        },
        {
            "chunk_id": "mock_collection_p2_c01",
            "source": "collection.pdf",
            "page": 2,
            "text": "Waste near schools and public facilities should be prioritised.",
            "score": 0.79,
        },
    ]
    return {
        "query": "plastic and organic uncollected waste near school for 5 days",
        "answer": (
            "The retrieved guidance supports prompt collection and prioritising "
            "waste near schools."
        ),
        "grounded": True,
        "sources": [
            {"source": item["source"], "page": item["page"]}
            for item in evidence
        ],
        "evidence": evidence,
    }


def decide(analysis: dict, retrieval: dict) -> dict:
    high_severity = analysis.get("severity") == "high"
    return {
        "priority": "high" if high_severity else "medium",
        "recommended_action": (
            "Immediate inspection and collection"
            if high_severity
            else "Schedule routine inspection and collection"
        ),
        "explanation": "Priority reflects the structured complaint analysis and retrieved guidance.",
        "supporting_sources": [
            item["source"] for item in retrieval["sources"]
        ],
        "requires_human_review": high_severity,
        "confidence": 0.85,
        "validation": {"passed": True, "issues": []},
    }
