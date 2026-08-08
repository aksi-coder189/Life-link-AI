"""
PredictiveAgent
----------------
Doesn't wait for the patient to visibly deteriorate. Uses the triage
severity score + symptom pattern to forecast the near-term risk of shock
or acute decline, so the crew can pre-empt it rather than react to it.
"""

SHOCK_TAGS = {"bleeding", "trauma", "envenomation", "burns", "chest_pain", "dyspnea", "swelling"}


def predict(profile: dict, triage: dict):
    if not triage:
        return None
    score = triage["severity_score"]
    tags = set(profile.get("symptom_tags", []))
    shock_signals = tags & SHOCK_TAGS

    if score >= 88 and shock_signals:
        window_min, prob = 5, min(96, 55 + score - 40)
        condition = "shock"
    elif score >= 75:
        window_min, prob = 12, min(90, 40 + score - 40)
        condition = "acute decline"
    elif score >= 55:
        window_min, prob = 25, min(70, 25 + score - 40)
        condition = "clinical worsening"
    else:
        return {"at_risk": False, "message": "No acute deterioration predicted in the transport window."}

    return {
        "at_risk": True,
        "condition": condition,
        "window_min": window_min,
        "probability_pct": max(10, round(prob)),
        "basis": sorted(shock_signals) or [f"Severity score {score}%"],
        "recommendation": "Pre-position crash cart and notify receiving team now" if condition == "shock"
                           else "Continuous vitals monitoring recommended en route",
    }
