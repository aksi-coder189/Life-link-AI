import math


def haversine_km(lat1, lng1, lat2, lng2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def eta_minutes(distance_km, speed_kmh):
    if speed_kmh <= 0:
        return 99
    # +18% for real-road vs straight-line distance, converted to minutes
    road_km = distance_km * 1.18
    return round((road_km / speed_kmh) * 60, 1)
