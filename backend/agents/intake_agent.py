"""
IntakeAgent
-----------
First agent to touch a report. Resolves the caller's location and, where
possible, links the case to a known patient record (the way a real system
would match against a health-ID or insurance lookup). Falls back to an
"unknown patient" placeholder that gets filled in as data arrives.
"""
import random
from ..data import PATIENT_ROSTER, EMERGENCY_PROFILES


def resolve_patient(patient_id: str | None):
    if patient_id:
        for p in PATIENT_ROSTER:
            if p["id"] == patient_id:
                return {**p, "known": True}
    # Unknown caller — system proceeds without history, flags it clearly
    return {
        "id": None,
        "name": "Unknown patient",
        "age": None,
        "sex": None,
        "blood_group": "Unknown",
        "allergies": [],
        "diabetic": None,
        "medications": [],
        "insurance_active": None,
        "known": False,
    }


def open_case(emergency_type: str, patient_id: str | None):
    profile = EMERGENCY_PROFILES.get(emergency_type, EMERGENCY_PROFILES["other"])
    patient = resolve_patient(patient_id)
    return {
        "profile": profile,
        "patient": patient,
    }
