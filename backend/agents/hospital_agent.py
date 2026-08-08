"""
HospitalMatchAgent — now doubling as the Hospital Readiness Predictor.
-----------------------------------------------------------------------
Scores every hospital in the network against this specific case: does it
have a trauma team, an ICU bed, the right specialty, the right blood type
in stock, how busy is it right now, and how far is it — in that order of
importance. "Readiness" isn't just "do they have a bed" — a hospital
running at 90%+ load gets penalised even with beds technically free,
because a real trauma team can't context-switch instantly.
"""
from .geo import haversine_km, eta_minutes

SPECIALTY_BY_EMERGENCY = {
    "accident": "trauma",
    "heart_attack": "cardiac",
    "stroke": "neuro",
    "burns": "burns",
    "pregnancy": "maternity",
    "poisoning": "general",
    "snake_bite": "general",
    "other": "general",
}

AMBULANCE_SPEED_KMH = 45  # used for hospital ETA before an ambulance is assigned


def predict_readiness(h: dict, needed_specialty: str) -> dict:
    """Readiness Prediction: can this hospital actually treat the patient
    the moment they arrive, given current load — not just its equipment
    list. Returns a 0-100 readiness_pct plus the factors behind it."""
    icu_free_pct = h["icu_beds_free"] / h["icu_beds_total"]
    readiness = 100.0
    factors = []

    if h["icu_beds_free"] < 2:
        readiness -= 30; factors.append("ICU beds nearly full")
    else:
        factors.append(f"{h['icu_beds_free']} ICU beds free")

    if h["current_load_pct"] >= 85:
        readiness -= 25; factors.append("Trauma team at high load")
    elif h["current_load_pct"] >= 65:
        readiness -= 10; factors.append("Moderate current load")
    else:
        factors.append("Low current load")

    if needed_specialty not in h["specialties"]:
        readiness -= 20; factors.append(f"No {needed_specialty} specialist on site")
    else:
        factors.append(f"{needed_specialty.title()} specialist available")

    if not h["trauma_team"]:
        readiness -= 10

    readiness = max(5, min(99, round(readiness - (1 - icu_free_pct) * 5)))
    return {"readiness_pct": readiness, "factors": factors}


def rank(hospitals: list, case_lat: float, case_lng: float, emergency_type: str,
         blood_group: str, risk_level: str):
    needed_specialty = SPECIALTY_BY_EMERGENCY.get(emergency_type, "general")
    scored = []

    for h in hospitals:
        dist = haversine_km(case_lat, case_lng, h["lat"], h["lng"])
        eta = eta_minutes(dist, AMBULANCE_SPEED_KMH)
        readiness = predict_readiness(h, needed_specialty)

        score = 50.0
        reasons_pos, reasons_neg = [], []

        if h["trauma_team"]:
            score += 15; reasons_pos.append("Trauma Team Ready")
        else:
            reasons_neg.append("No Trauma Team")

        icu_free_pct = h["icu_beds_free"] / h["icu_beds_total"]
        if h["icu_beds_free"] >= 2:
            score += 12; reasons_pos.append("ICU Available")
        else:
            reasons_neg.append("No ICU")
        score += icu_free_pct * 8

        if needed_specialty in h["specialties"]:
            score += 12
            reasons_pos.append(f"{needed_specialty.title()} specialty on site")

        if h["has_ct"]:
            score += 5; reasons_pos.append("CT Ready")
        if needed_specialty == "cardiac" and h["has_cath_lab"]:
            score += 6; reasons_pos.append("Cath lab on site")
        if needed_specialty == "neuro" and h["neurosurgeon_on_call"]:
            score += 6; reasons_pos.append("Neurosurgeon Available")

        # workload — a busy hospital is a slower hospital, regardless of beds
        if h["current_load_pct"] < 60:
            score += 6; reasons_pos.append(f"Low current load ({h['current_load_pct']}%)")
        elif h["current_load_pct"] > 85:
            score -= 10; reasons_neg.append(f"High current load ({h['current_load_pct']}%)")

        if h["success_rate_pct"] >= 92:
            score += 4; reasons_pos.append(f"{h['success_rate_pct']}% treatment success rate")

        stock = h["blood_stock"].get(blood_group, 0) if blood_group and blood_group != "Unknown" else None
        if stock is not None:
            if stock >= 5:
                score += 6; reasons_pos.append(f"Blood {blood_group} in stock")
            elif stock > 0:
                score += 2
            else:
                reasons_neg.append(f"Blood {blood_group} low/out")

        # Distance penalty — closer is better, but readiness dominates
        score -= min(20, dist * 0.9)
        if risk_level == "Critical":
            score -= min(10, eta * 0.3)

        score = max(1, min(99, round(score)))

        scored.append({
            "id": h["id"], "name": h["name"],
            "score": score,
            "readiness_pct": readiness["readiness_pct"],
            "readiness_factors": readiness["factors"],
            "distance_km": round(dist, 1),
            "eta_min": eta,
            "icu_beds_free": h["icu_beds_free"],
            "icu_beds_total": h["icu_beds_total"],
            "trauma_team": h["trauma_team"],
            "current_load_pct": h["current_load_pct"],
            "success_rate_pct": h["success_rate_pct"],
            "why_positive": reasons_pos[:5],
            "why_negative": reasons_neg[:3],
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored
