"""
GoldenHourAgent — the Golden Hour Decision Engine
--------------------------------------------------
Doesn't ask "which hospital is closest" — asks "which destination gives
this patient the best chance in the golden hour, given how long it takes
to get there AND whether that hospital can actually treat them." Produces
a Golden-Hour Suitability Score (0-100), not a medical outcome prediction —
this is a routing decision, not a clinical claim.
"""

# How fast survival odds fall off with each minute of travel time, tuned
# per risk level — a Critical patient loses far more per minute than a
# Moderate one.
TIME_PENALTY_PER_MIN = {
    "Critical": 1.8,
    "High": 1.1,
    "Moderate": 0.5,
    "Low": 0.2,
}


def decide(ranked_hospitals: list, risk_level: str):
    """Takes HospitalMatchAgent's readiness-scored list and re-ranks by a
    Golden-Hour Suitability Score = f(readiness, treatment capability) -
    f(travel time). Returns the same list, augmented and re-sorted, plus
    an explicit nearest-vs-recommended comparison for the UI."""
    penalty_per_min = TIME_PENALTY_PER_MIN.get(risk_level, 0.6)
    out = []

    for h in ranked_hospitals:
        # readiness_pct anchors the "can they actually treat this patient"
        # side; eta drags it down the longer the drive.
        gh_score = h["readiness_pct"] - h["eta_min"] * penalty_per_min
        gh_score = max(3, min(99, round(gh_score)))
        out.append({**h, "golden_hour_score": gh_score})

    out.sort(key=lambda x: x["golden_hour_score"], reverse=True)
    winner = out[0]
    nearest = min(out, key=lambda x: x["distance_km"])

    explanation = (
        f"{winner['name']} has the highest Golden-Hour Suitability Score "
        f"({winner['golden_hour_score']}/100) — {winner['eta_min']} min away with "
        f"{winner['readiness_pct']}% readiness."
    )
    if nearest["id"] != winner["id"]:
        explanation += (
            f" {nearest['name']} is the nearest hospital ({nearest['distance_km']} km) but scores "
            f"{nearest['golden_hour_score']}/100 — lower treatment readiness outweighs the shorter drive."
        )

    return {
        "ranked": out,
        "winner_id": winner["id"],
        "nearest_id": nearest["id"],
        "explanation": explanation,
    }
