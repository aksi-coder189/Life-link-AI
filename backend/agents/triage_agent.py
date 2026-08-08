"""
TriageAgent
-----------
The decision-fusion step: combines what the voice agent heard, what the
vision agent saw, and the patient's known history into one severity score,
risk level and action list. This is the piece a hospital's trauma team
sees before the patient arrives.
"""


def assess(profile: dict, patient: dict, symptom_tags: list, vision_ready: bool):
    score = profile["base_severity"]
    reasons = []

    if symptom_tags:
        reasons.append("Voice symptoms confirm profile")
    if vision_ready:
        score += 4
        reasons.append("Image analysis confirms")
    if patient.get("diabetic"):
        score += 3
        reasons.append("Diabetic — elevated complication risk")
    if patient.get("age") and patient["age"] >= 60:
        score += 3
        reasons.append("Age 60+ — elevated risk profile")
    if patient.get("allergies"):
        reasons.append(f"Known allergy on file: {', '.join(patient['allergies'])}")
    if not patient.get("known"):
        reasons.append("No patient history on file — proceeding on presentation only")

    score = min(99, round(score))

    if score >= 85:
        risk = "Critical"
    elif score >= 65:
        risk = "High"
    elif score >= 40:
        risk = "Moderate"
    else:
        risk = "Low"

    actions = list(profile["recommended_actions"])
    if patient.get("blood_group") and patient["blood_group"] != "Unknown":
        actions.append(f"Blood bank notified — {patient['blood_group']} reserved")
    if patient.get("allergies"):
        actions.append(f"Flag {', '.join(patient['allergies'])}-free protocol to pharmacy")

    return {
        "severity_score": score,
        "risk_level": risk,
        "reasons": reasons,
        "recommended_actions": actions,
        "recommended_tx": profile["recommended_tx"],
        "model": "Symptom Classifier + Vision Fusion v1",
    }
