"""
HandoffAgent — AI Medical Handoff
-----------------------------------
Turns everything gathered so far into the concise, structured summary a
doctor actually wants in the 15 seconds before a patient arrives — not a
transcript dump. This is what gets pushed to the hospital console and
what the downloadable report is built from.
"""
import time


def build_handoff(case: dict):
    p = case["patient"]
    triage = case.get("triage") or {}
    vision = case.get("vision")
    dispatch = case.get("dispatch")

    vitals_known = []
    if p.get("age"):
        vitals_known.append(f"{p['age']}-year-old {('male' if p.get('sex')=='M' else 'female') if p.get('sex') else ''}".strip())
    if p.get("blood_group") and p["blood_group"] != "Unknown":
        vitals_known.append(f"Blood group {p['blood_group']}")
    if p.get("diabetic"):
        vitals_known.append("Diabetic")
    if p.get("allergies"):
        vitals_known.append(f"Allergic to {', '.join(p['allergies'])}")

    findings = []
    for q in case.get("transcript", []):
        findings.append(q["a"])
    if vision:
        findings += [f"{t['name']}: {t['value']}" for t in vision["tags"]]

    return {
        "generated_at": time.time(),
        "case_id": case["id"],
        "chief_complaint": case["label"],
        "patient_line": ", ".join(vitals_known) if vitals_known else "Patient identity unconfirmed",
        "risk_level": triage.get("risk_level", "Pending"),
        "severity_score": triage.get("severity_score"),
        "key_findings": findings[:6],
        "recommended_tx": triage.get("recommended_tx", "Pending assessment"),
        "recommended_actions": triage.get("recommended_actions", []),
        "eta_min": dispatch["eta_min"] if dispatch else None,
        "destination": dispatch["hospital_name"] if dispatch else None,
        "doctor_assigned": dispatch.get("doctor_assigned") if dispatch else None,
        "ambulance_id": dispatch["ambulance_id"] if dispatch else None,
    }
