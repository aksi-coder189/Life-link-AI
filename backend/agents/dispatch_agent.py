"""
DispatchAgent
-------------
Picks the closest available ambulance to the scene, then — once a
destination hospital is chosen — simulates the live drive: a route made of
waypoints, an ETA that recalculates as time passes, and a mid-route
"rerouted" event so the family/doctor views have something real to reflect.
"""
import time
from .geo import haversine_km, eta_minutes


def find_nearest_available(ambulances: list, lat: float, lng: float):
    candidates = [a for a in ambulances if a["status"] == "available"]
    if not candidates:
        candidates = ambulances
    best = min(candidates, key=lambda a: haversine_km(lat, lng, a["lat"], a["lng"]))
    return best


def build_route(scene_lat, scene_lng, hosp_lat, hosp_lng):
    """A gentle 3-point route (scene -> midpoint bend -> hospital) so the
    frontend has something more realistic than a straight line to draw."""
    mid_lat = (scene_lat + hosp_lat) / 2 + (hosp_lng - scene_lng) * 0.15
    mid_lng = (scene_lng + hosp_lng) / 2 - (hosp_lat - scene_lat) * 0.15
    return [
        {"lat": scene_lat, "lng": scene_lng, "label": "Scene"},
        {"lat": mid_lat, "lng": mid_lng, "label": "En route"},
        {"lat": hosp_lat, "lng": hosp_lng, "label": "Hospital"},
    ]


def dispatch(ambulances: list, scene_lat, scene_lng, hosp_lat, hosp_lng, hospital_name, doctor_assigned=None):
    amb = find_nearest_available(ambulances, scene_lat, scene_lng)
    to_scene_km = haversine_km(scene_lat, scene_lng, amb["lat"], amb["lng"])
    scene_to_hosp_km = haversine_km(scene_lat, scene_lng, hosp_lat, hosp_lng)
    total_eta_min = eta_minutes(to_scene_km, amb["speed_kmh"]) * 0.15 + eta_minutes(scene_to_hosp_km, amb["speed_kmh"])

    route = build_route(scene_lat, scene_lng, hosp_lat, hosp_lng)
    now = time.time()

    return {
        "ambulance_id": amb["id"],
        "crew": amb["crew"],
        "speed_kmh": amb["speed_kmh"],
        "hospital_name": hospital_name,
        "doctor_assigned": doctor_assigned,
        "distance_km": round(scene_to_hosp_km, 1),
        "eta_min": round(total_eta_min, 1),
        "dispatched_at": now,
        "route": route,
        "checkpoints": [
            {"label": "Dispatched", "at": now, "done": True},
            {"label": "En route", "at": now + 20, "done": False},
            {"label": "Rerouted — faster path found", "at": now + total_eta_min * 30, "done": False},
            {"label": f"Arriving {hospital_name}", "at": now + total_eta_min * 60, "done": False},
        ],
    }


def live_position(dispatch_state: dict):
    """Compute current position along the route and remaining ETA, purely
    as a function of elapsed wall-clock time since dispatch (no polling
    loop needed server-side)."""
    now = time.time()
    elapsed_min = (now - dispatch_state["dispatched_at"]) / 60
    total_min = max(0.1, dispatch_state["eta_min"])
    progress = min(1.0, elapsed_min / total_min)

    route = dispatch_state["route"]
    # progress along a 2-segment polyline
    if progress < 0.5:
        seg_t = progress / 0.5
        a, b = route[0], route[1]
    else:
        seg_t = (progress - 0.5) / 0.5
        a, b = route[1], route[2]
    lat = a["lat"] + (b["lat"] - a["lat"]) * seg_t
    lng = a["lng"] + (b["lng"] - a["lng"]) * seg_t

    remaining_min = max(0, round(total_min - elapsed_min, 1))
    checkpoints = []
    for cp in dispatch_state["checkpoints"]:
        checkpoints.append({**cp, "done": now >= cp["at"]})

    return {
        "lat": lat, "lng": lng,
        "progress_pct": round(progress * 100, 1),
        "remaining_eta_min": remaining_min,
        "arrived": progress >= 1.0,
        "checkpoints": checkpoints,
        "speed_kmh": dispatch_state["speed_kmh"],
    }
