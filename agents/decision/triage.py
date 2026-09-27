"""Project triage safeguards, not statutory collection deadlines or medical advice."""
import re

HAZARDS = ("hazardous", "medical", "chemical", "toxic", "biohazard", "syringe", "sharp", "gas leak", "radioactive")


def hazard_mentions(text):
    affirmative, uncertain = False, False
    for clause in re.split(r"[.!?;,]|\b(?:but|however|although)\b", text.lower()):
        for term in HAZARDS:
            for match in re.finditer(r"\b" + re.escape(term) + r"s?\b", clause):
                if re.search(r"\b(unsure|uncertain|possible|possibly|suspect|suspected|may|might)\b|not sure|cannot rule out|can't rule out", clause):
                    uncertain = True
                    continue
                before = clause[:match.start()]
                before = re.sub(r"\bnot only\b", "", before)
                window = " ".join(before.split()[-5:])
                negations = list(re.finditer(r"\b(no|not|without|neither)\b", window))
                if negations and re.search(r"\b(and|but)\b", window[negations[-1].end():]):
                    # Negation spanning a conjunction is not confidently scoped.
                    uncertain = True
                elif not negations:
                    affirmative = True
    return affirmative, uncertain


def clarification_questions(analysis):
    questions = []
    if not analysis.get("location") or analysis["location"].strip().lower() in {"unknown", "unclear", "not specified"}:
        questions.append("Where is the waste located? A public area or landmark is enough; avoid personal addresses.")
    if analysis.get("duration_days") is None:
        questions.append("How long has the waste been present? You may answer 'unknown'.")
    types = analysis.get("waste_types") or []
    if not types or all(str(t).lower() in {"unknown", "mixed", "waste"} for t in types):
        questions.append("Are chemicals, medical waste or sharp objects visible? Do not touch or approach the waste to check.")
    return questions[:3]
