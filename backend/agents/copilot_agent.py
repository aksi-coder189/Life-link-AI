"""
CopilotAgent
-------------
Two modes:

1. Case-grounded Q&A — when a case_id is supplied, the copilot answers
   directly from that case's real state (patient, symptoms, vision
   findings, triage, hospital choice, ambulance, ETA) instead of guessing.
   This is pattern-matched against a fixed set of question intents below;
   swapping this for a real LLM call means feeding it the same case
   context as a prompt instead of pattern-matching the question.
2. Free-text symptom triage — when no case context answers the question
   (or none is supplied), falls back to keyword-matched possible-causes +
   immediate-actions, standing in for an LLM clinical-reasoning call.
"""

INTENTS = [
    (["hospital selected", "hospital chosen", "which hospital", "hospital match"], "why_hospital"),
    (["critical", "risk level", "this risky", "why risky"], "why_critical"),
    (["vision", "detect", "photo show", "image show"], "vision_findings"),
    (["eta", "how long", "arrive", "when will"], "current_eta"),
    (["prepare", "doctor should", "get ready"], "doctor_prep"),
    (["status", "what's happening", "give me an update", "summary"], "status_summary"),
]

SYMPTOM_RULES = [
    (["unconscious", "not responding", "unresponsive"],
     ["Stroke", "Cardiac Arrest", "Severe Trauma", "Hypoglycemia"],
     ["Check airway & breathing", "Attach ECG", "Trauma alert to receiving hospital"]),
    (["chest pain", "chest tightness"],
     ["Myocardial Infarction", "Angina", "Aortic Dissection"],
     ["12-lead ECG", "Aspirin per protocol", "Pre-alert cath lab"]),
    (["breathing", "breath", "gasping", "suffocat"],
     ["Airway obstruction", "Asthma/COPD exacerbation", "Pulmonary embolism"],
     ["High-flow oxygen", "Sit patient upright", "Prepare airway kit"]),
    (["bleeding", "blood loss", "hemorrhag"],
     ["Arterial bleed", "Internal hemorrhage", "Coagulopathy"],
     ["Direct pressure on wound", "IV access x2", "Type & crossmatch blood"]),
    (["seizure", "convulsi", "fitting"],
     ["Epileptic seizure", "Eclampsia", "Head trauma"],
     ["Protect from injury, do not restrain", "Time the seizure", "Prepare anticonvulsant protocol"]),
    (["fever", "high temperature"],
     ["Sepsis", "Infection", "Heat stroke"],
     ["Check temperature trend", "IV fluids", "Blood cultures on arrival"]),
    (["pregnan", "labour", "labor", "contraction"],
     ["Active labour", "Preeclampsia", "Placental abruption"],
     ["Time contractions", "Notify maternity ward", "Monitor for bleeding"]),
]
DEFAULT_SYMPTOM = (
    ["General deterioration", "Unclear etiology — needs on-scene assessment"],
    ["Monitor vitals continuously", "Prepare general trauma/medical bay", "Reassess every 2 minutes"],
)


def _match_intent(text: str):
    for keywords, intent in INTENTS:
        if any(k in text for k in keywords):
            return intent
    return None


def _answer_from_case(intent: str, case: dict):
    triage = case.get("triage")
    vision = case.get("vision")
    dispatch = case.get("dispatch")
    gh = case.get("golden_hour")

    if intent == "why_hospital":
        if not dispatch or not gh:
            return "No hospital has been selected for this case yet — run hospital matching first."
        return gh.get("explanation", f"{dispatch['hospital_name']} was selected by the Golden Hour Decision Engine.")

    if intent == "why_critical":
        if not triage:
            return "Triage hasn't run yet for this case."
        reasons = "; ".join(triage["reasons"])
        return f"Risk is {triage['risk_level']} (severity {triage['severity_score']}/100) because: {reasons}."

    if intent == "vision_findings":
        if not vision:
            return "No scene photo has been analyzed for this case yet."
        findings = "; ".join(f"{t['name']}: {t['value']}" for t in vision["tags"])
        return f"Vision assessment found: {findings}."

    if intent == "current_eta":
        if not dispatch:
            return "Ambulance hasn't been dispatched yet — no ETA available."
        return f"{dispatch['ambulance_id']} is en route to {dispatch['hospital_name']}, ETA {dispatch['eta_min']} min."

    if intent == "doctor_prep":
        if not triage:
            return "Run triage first to get a recommended preparation list."
        actions = "; ".join(triage["recommended_actions"])
        return f"Recommended Tx: {triage['recommended_tx']}. Prepare: {actions}."

    if intent == "status_summary":
        parts = [f"Case {case['id']} — {case['label']}, stage: {case['stage']}."]
        if triage:
            parts.append(f"Risk {triage['risk_level']} ({triage['severity_score']}/100).")
        if dispatch:
            parts.append(f"En route to {dispatch['hospital_name']}, ETA {dispatch['eta_min']} min, doctor {dispatch['doctor_assigned']}.")
        return " ".join(parts)

    return None


def respond(message: str, case: dict | None = None):
    text = message.lower()

    if case:
        intent = _match_intent(text)
        if intent:
            answer = _answer_from_case(intent, case)
            if answer:
                return {"grounded": True, "answer": answer, "causes": [], "actions": []}

    for keywords, causes, actions in SYMPTOM_RULES:
        if any(k in text for k in keywords):
            return {"grounded": False, "answer": None, "causes": causes, "actions": actions}

    causes, actions = DEFAULT_SYMPTOM
    return {"grounded": False, "answer": None, "causes": causes, "actions": actions}
