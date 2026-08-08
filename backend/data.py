"""
Seed data for LifeLink AI.
All coordinates are centered around a fictional city grid so distance/ETA
math (haversine) produces realistic-looking numbers.
"""

# Roughly Delhi-NCR shaped bounding box, used only as a plausible city canvas
CITY_CENTER = {"lat": 28.6139, "lng": 77.2090}

HOSPITALS = [
    {
        "id": "apollo",
        "name": "Apollo Hospital",
        "lat": 28.5665, "lng": 77.2431,
        "trauma_team": True,
        "icu_beds_total": 40,
        "icu_beds_free": 15,
        "has_ct": True,
        "has_cath_lab": True,
        "neurosurgeon_on_call": True,
        "current_load_pct": 54,
        "success_rate_pct": 94,
        "blood_stock": {"O+": 40, "O-": 12, "A+": 30, "A-": 8, "B+": 25, "B-": 6, "AB+": 14, "AB-": 4},
        "specialties": ["trauma", "cardiac", "neuro", "burns"],
    },
    {
        "id": "fortis",
        "name": "Fortis",
        "lat": 28.5355, "lng": 77.2450,
        "trauma_team": True,
        "icu_beds_total": 24,
        "icu_beds_free": 1,
        "has_ct": True,
        "has_cath_lab": True,
        "neurosurgeon_on_call": False,
        "current_load_pct": 91,
        "success_rate_pct": 88,
        "blood_stock": {"O+": 10, "O-": 2, "A+": 14, "A-": 3, "B+": 9, "B-": 1, "AB+": 5, "AB-": 1},
        "specialties": ["cardiac", "ortho"],
    },
    {
        "id": "max",
        "name": "Max Healthcare",
        "lat": 28.5273, "lng": 77.2180,
        "trauma_team": False,
        "icu_beds_total": 20,
        "icu_beds_free": 4,
        "has_ct": True,
        "has_cath_lab": False,
        "neurosurgeon_on_call": False,
        "current_load_pct": 78,
        "success_rate_pct": 85,
        "blood_stock": {"O+": 18, "O-": 4, "A+": 20, "A-": 5, "B+": 12, "B-": 2, "AB+": 7, "AB-": 2},
        "specialties": ["ortho", "general"],
    },
    {
        "id": "medanta",
        "name": "Medanta",
        "lat": 28.4402, "lng": 77.0716,
        "trauma_team": True,
        "icu_beds_total": 36,
        "icu_beds_free": 16,
        "has_ct": True,
        "has_cath_lab": True,
        "neurosurgeon_on_call": True,
        "current_load_pct": 47,
        "success_rate_pct": 96,
        "blood_stock": {"O+": 33, "O-": 9, "A+": 28, "A-": 7, "B+": 22, "B-": 5, "AB+": 11, "AB-": 3},
        "specialties": ["trauma", "cardiac", "neuro", "maternity"],
    },
    {
        "id": "aiims",
        "name": "AIIMS Trauma Center",
        "lat": 28.5672, "lng": 77.2100,
        "trauma_team": True,
        "icu_beds_total": 50,
        "icu_beds_free": 9,
        "has_ct": True,
        "has_cath_lab": True,
        "neurosurgeon_on_call": True,
        "current_load_pct": 82,
        "success_rate_pct": 92,
        "blood_stock": {"O+": 45, "O-": 15, "A+": 35, "A-": 10, "B+": 30, "B-": 8, "AB+": 16, "AB-": 5},
        "specialties": ["trauma", "neuro", "burns", "general"],
    },
]

DOCTOR_POOL = {
    "trauma": ["Dr. R. Sharma", "Dr. N. Bhatia"],
    "cardiac": ["Dr. A. Khanna", "Dr. S. Iyer"],
    "neuro": ["Dr. P. Malhotra", "Dr. V. Rao"],
    "burns": ["Dr. K. Sen"],
    "maternity": ["Dr. M. Kapoor"],
    "ortho": ["Dr. T. Chawla"],
    "general": ["Dr. J. Verma", "Dr. L. Fernandes"],
}

AMBULANCES = [
    {"id": "AMB-101", "lat": 28.6000, "lng": 77.2200, "status": "available", "crew": "ALS", "speed_kmh": 46},
    {"id": "AMB-102", "lat": 28.5800, "lng": 77.1950, "status": "available", "crew": "BLS", "speed_kmh": 40},
    {"id": "AMB-103", "lat": 28.5500, "lng": 77.2600, "status": "available", "crew": "ALS", "speed_kmh": 48},
    {"id": "AMB-104", "lat": 28.6300, "lng": 77.1800, "status": "available", "crew": "ALS", "speed_kmh": 44},
    {"id": "AMB-105", "lat": 28.5200, "lng": 77.2000, "status": "on_call", "crew": "BLS", "speed_kmh": 38},
]

# A small roster of known patients (so returning "patients" get a rich history,
# mirroring what a real system would pull from health records / insurance link)
PATIENT_ROSTER = [
    {
        "id": "rahul-34",
        "name": "Rahul Verma", "age": 34, "sex": "M",
        "blood_group": "B+", "allergies": ["Penicillin"], "diabetic": True,
        "medications": ["Metformin"], "insurance_active": True,
    },
    {
        "id": "anita-29",
        "name": "Anita Menon", "age": 29, "sex": "F",
        "blood_group": "O-", "allergies": [], "diabetic": False,
        "medications": [], "insurance_active": True,
    },
    {
        "id": "suresh-61",
        "name": "Suresh Kumar", "age": 61, "sex": "M",
        "blood_group": "AB+", "allergies": ["Sulfa drugs"], "diabetic": True,
        "medications": ["Atorvastatin", "Amlodipine"], "insurance_active": True,
    },
    {
        "id": "priya-26",
        "name": "Priya Sharma", "age": 26, "sex": "F",
        "blood_group": "A+", "allergies": [], "diabetic": False,
        "medications": [], "insurance_active": False,
    },
]

# Rule-based voice triage scripts per emergency type — a lightweight stand-in
# for a real speech + NLU pipeline. Each entry drives SymptomAgent's dialogue
# and seeds the tags VisionAgent will "detect" in an uploaded scene photo.
EMERGENCY_PROFILES = {
    "accident": {
        "label": "Road Accident",
        "icon": "car",
        "questions": [
            {"q": "Is the patient conscious and breathing?", "a": "Yes, but disoriented"},
            {"q": "Is there visible bleeding?", "a": "Yes — from the arm, heavy"},
            {"q": "Can the patient move all limbs?", "a": "No — right arm won't move"},
            {"q": "Any signs of head injury?", "a": "Yes — hit the windshield"},
        ],
        "symptom_tags": ["trauma", "bleeding", "possible_fracture", "head_injury"],
        "vision_tags": [
            {"name": "Possible fracture", "value": "Right forearm"},
            {"name": "Bleeding", "value": "Heavy"},
            {"name": "Head trauma", "value": "Suspected"},
            {"name": "Body region", "value": "Upper limb / torso"},
        ],
        "base_severity": 78,
        "recommended_actions": [
            "Alert trauma team before arrival",
            "Reserve CT slot at destination",
            "Begin spinal precaution protocol",
            "Start IV fluids en route",
        ],
        "recommended_tx": "Trauma workup + CT",
    },
    "heart_attack": {
        "label": "Heart Attack",
        "icon": "heart",
        "questions": [
            {"q": "Is there chest pain right now?", "a": "Yes — severe, radiating to left arm"},
            {"q": "Any shortness of breath?", "a": "Yes, since it started"},
            {"q": "Sweating or nausea?", "a": "Yes, both"},
            {"q": "Any history of heart disease?", "a": "Yes — on blood pressure medication"},
        ],
        "symptom_tags": ["chest_pain", "radiating_pain", "dyspnea", "diaphoresis"],
        "vision_tags": [
            {"name": "Skin tone", "value": "Pale, clammy"},
            {"name": "Distress level", "value": "High"},
            {"name": "Posture", "value": "Clutching chest"},
            {"name": "Consciousness", "value": "Alert"},
        ],
        "base_severity": 92,
        "recommended_actions": [
            "Pre-alert cardiac cath lab",
            "Prepare aspirin + nitroglycerin protocol",
            "12-lead ECG en route",
            "Hold cath lab slot, do not release",
        ],
        "recommended_tx": "Cath lab — suspected STEMI",
    },
    "stroke": {
        "label": "Stroke",
        "icon": "brain",
        "questions": [
            {"q": "Facial drooping on one side?", "a": "Yes — left side"},
            {"q": "Can they raise both arms?", "a": "No — left arm drifts down"},
            {"q": "Is speech slurred?", "a": "Yes, noticeably"},
            {"q": "What time did symptoms start?", "a": "About 22 minutes ago"},
        ],
        "symptom_tags": ["facial_droop", "arm_weakness", "slurred_speech", "fast_positive"],
        "vision_tags": [
            {"name": "Facial symmetry", "value": "Asymmetric — left droop"},
            {"name": "FAST score", "value": "3/3 positive"},
            {"name": "Consciousness", "value": "Alert but confused"},
            {"name": "Onset window", "value": "Within thrombolysis window"},
        ],
        "base_severity": 90,
        "recommended_actions": [
            "Pre-alert stroke team + neurologist",
            "Reserve CT/MRI slot immediately",
            "Prepare thrombolysis protocol",
            "Note last-known-well time for care team",
        ],
        "recommended_tx": "Emergency CT + thrombolysis eval",
    },
    "burns": {
        "label": "Burns",
        "icon": "flame",
        "questions": [
            {"q": "What caused the burn?", "a": "Kitchen gas flare-up"},
            {"q": "How much of the body is affected?", "a": "Looks like an arm and part of the chest"},
            {"q": "Any difficulty breathing?", "a": "Slight, from smoke"},
            {"q": "Blistering or charring visible?", "a": "Yes — blistering"},
        ],
        "symptom_tags": ["burns", "smoke_inhalation", "blistering"],
        "vision_tags": [
            {"name": "Burn depth", "value": "2nd degree, blistering"},
            {"name": "Body surface area", "value": "~12%"},
            {"name": "Airway risk", "value": "Mild smoke exposure"},
            {"name": "Body region", "value": "Right arm + chest"},
        ],
        "base_severity": 70,
        "recommended_actions": [
            "Alert burns unit",
            "Prepare fluid resuscitation (Parkland formula)",
            "Airway monitoring en route",
            "Sterile burn dressing on arrival",
        ],
        "recommended_tx": "Burns unit admission",
    },
    "pregnancy": {
        "label": "Pregnancy Emergency",
        "icon": "baby",
        "questions": [
            {"q": "How many weeks pregnant?", "a": "About 36 weeks"},
            {"q": "Any bleeding or fluid loss?", "a": "Yes — light bleeding"},
            {"q": "How far apart are contractions?", "a": "Every 4 minutes"},
            {"q": "Any previous pregnancy complications?", "a": "None reported"},
        ],
        "symptom_tags": ["active_labor", "bleeding", "third_trimester"],
        "vision_tags": [
            {"name": "Gestational stage", "value": "~36 weeks"},
            {"name": "Distress level", "value": "Moderate"},
            {"name": "Bleeding", "value": "Light, active"},
            {"name": "Contractions", "value": "Regular, 4 min apart"},
        ],
        "base_severity": 65,
        "recommended_actions": [
            "Alert maternity / labour ward",
            "Prepare delivery suite on standby",
            "Fetal monitoring en route if available",
            "Notify on-call OB-GYN",
        ],
        "recommended_tx": "Maternity ward admission",
    },
    "poisoning": {
        "label": "Poisoning",
        "icon": "skull",
        "questions": [
            {"q": "What was ingested, if known?", "a": "Unknown pills, possibly overdose"},
            {"q": "When did it happen?", "a": "Within the last hour"},
            {"q": "Is the patient conscious?", "a": "Yes, but drowsy"},
            {"q": "Any vomiting?", "a": "Yes, once"},
        ],
        "symptom_tags": ["altered_consciousness", "suspected_overdose", "vomiting"],
        "vision_tags": [
            {"name": "Pupil response", "value": "Sluggish"},
            {"name": "Consciousness", "value": "Drowsy, responsive"},
            {"name": "Substance found", "value": "Unlabeled tablets"},
            {"name": "Airway", "value": "Clear for now"},
        ],
        "base_severity": 74,
        "recommended_actions": [
            "Alert poison control / toxicology",
            "Prepare activated charcoal protocol if indicated",
            "Continuous airway + consciousness monitoring",
            "Bring sample of substance to ER",
        ],
        "recommended_tx": "Toxicology workup",
    },
    "snake_bite": {
        "label": "Snake Bite",
        "icon": "snake",
        "questions": [
            {"q": "Where was the bite?", "a": "Lower left leg"},
            {"q": "Can you describe the snake, if seen?", "a": "Dark, patterned, seen briefly"},
            {"q": "Any swelling or discoloration?", "a": "Yes, spreading swelling"},
            {"q": "Any difficulty breathing or blurred vision?", "a": "Slight blurred vision"},
        ],
        "symptom_tags": ["envenomation", "swelling", "neuro_symptoms"],
        "vision_tags": [
            {"name": "Bite site", "value": "Lower left leg, swelling"},
            {"name": "Discoloration", "value": "Spreading"},
            {"name": "Neuro signs", "value": "Blurred vision reported"},
            {"name": "Time since bite", "value": "~15 min"},
        ],
        "base_severity": 80,
        "recommended_actions": [
            "Alert ER for antivenom availability",
            "Keep limb immobilized, below heart level",
            "Do not apply tourniquet — flag to crew",
            "Monitor for respiratory involvement",
        ],
        "recommended_tx": "Antivenom + observation",
    },
    "other": {
        "label": "General Emergency",
        "icon": "plus",
        "questions": [
            {"q": "Is the patient conscious and breathing?", "a": "Yes"},
            {"q": "What is the main symptom right now?", "a": "Severe abdominal pain"},
            {"q": "How long has this been going on?", "a": "About 40 minutes"},
            {"q": "Any known medical conditions?", "a": "Unknown"},
        ],
        "symptom_tags": ["acute_pain", "unclear_cause"],
        "vision_tags": [
            {"name": "Distress level", "value": "Moderate-high"},
            {"name": "Consciousness", "value": "Alert"},
            {"name": "Visible injury", "value": "None obvious"},
            {"name": "Body language", "value": "Guarding abdomen"},
        ],
        "base_severity": 55,
        "recommended_actions": [
            "General surgical team on standby",
            "Pain management en route",
            "Basic diagnostics on arrival",
        ],
        "recommended_tx": "General ER workup",
    },
}
