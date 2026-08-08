"""
AnalyticsAgent
--------------
Rolls every case up into metrics that are actually computed from the
case store — no fabricated "AI confidence" or "lives saved" numbers, no
random heatmap. Everything here is either a straight count/average over
real cases, or real hospital data (ICU occupancy). If it can't be
computed from state, it isn't shown.
"""
import time


def build_dashboard(cases: dict, hospitals: list):
    all_cases = list(cases.values())
    total_cases = len(all_cases)

    risk_counts = {"Critical": 0, "High": 0, "Moderate": 0, "Low": 0}
    for c in all_cases:
        if c.get("triage"):
            risk_counts[c["triage"]["risk_level"]] = risk_counts.get(c["triage"]["risk_level"], 0) + 1
    critical_cases = risk_counts["Critical"]

    # real response time: seconds between case creation and the
    # "dispatched" event, averaged over cases that actually reached that
    # stage — not a guess.
    response_times_min = []
    for c in all_cases:
        dispatched_events = [e for e in c["events"] if e["stage"] == "dispatched"]
        if dispatched_events:
            response_times_min.append((dispatched_events[0]["at"] - c["created_at"]) / 60)
    avg_response_min = round(sum(response_times_min) / len(response_times_min), 1) if response_times_min else None

    hospital_etas = [c["dispatch"]["eta_min"] for c in all_cases if c.get("dispatch")]
    avg_hospital_eta_min = round(sum(hospital_etas) / len(hospital_etas), 1) if hospital_etas else None

    ambulances_dispatched = sum(1 for c in all_cases if c.get("dispatch"))
    hospital_matches = sum(1 for c in all_cases if c.get("dispatch"))

    icu_by_hospital = [
        {"id": h["id"], "name": h["name"],
         "occupancy_pct": round((1 - h["icu_beds_free"] / h["icu_beds_total"]) * 100),
         "load_pct": h["current_load_pct"]}
        for h in hospitals
    ]
    avg_icu_occupancy_pct = round(sum(x["occupancy_pct"] for x in icu_by_hospital) / len(icu_by_hospital))

    return {
        "total_cases": total_cases,
        "critical_cases": critical_cases,
        "avg_response_min": avg_response_min,
        "avg_hospital_eta_min": avg_hospital_eta_min,
        "ambulances_dispatched": ambulances_dispatched,
        "hospital_matches": hospital_matches,
        "risk_distribution": risk_counts,
        "icu_by_hospital": icu_by_hospital,
        "avg_icu_occupancy_pct": avg_icu_occupancy_pct,
        "generated_at": time.time(),
    }
