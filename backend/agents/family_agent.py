"""
FamilyAgent
-----------
Takes the same event log every other agent writes to and rewrites it in
plain, reassuring language for the family view — no medical jargon,
no severity scores, just what's happening and when the next update lands.
"""

STAGE_COPY = {
    "reported": ("Emergency reported", "Help is on the way"),
    "symptoms_analyzed": ("Details recorded", "Everything we need has been noted"),
    "vision_analyzed": ("Scene photo reviewed", "Helps the team prepare"),
    "assessed": ("Care plan ready", "The care team has the full picture"),
    "hospital_selected": ("Hospital selected", "{hospital} — ready and waiting"),
    "dispatched": ("Ambulance dispatched", "{ambulance} is heading to the scene, {doctor} assigned"),
    "en_route": ("En route to hospital", "Live location is being shared"),
    "arrived": ("Arrived & treatment started", "{doctor} is ready and has the full picture"),
}


def build_feed(case: dict):
    feed = []

    # dispatch can legitimately be None before an ambulance is dispatched
    dispatch = case.get("dispatch") or {}

    for ev in case["events"]:
        title, sub_template = STAGE_COPY.get(
            ev["stage"],
            (ev["stage"], "")
        )

        sub = sub_template.format(
            hospital=dispatch.get(
                "hospital_name",
                "the hospital"
            ),
            ambulance=dispatch.get(
                "ambulance_id",
                "the ambulance"
            ),
            doctor=dispatch.get(
                "doctor_assigned",
                "the receiving doctor"
            ),
        ) if sub_template else ""

        feed.append({
            "title": title,
            "sub": sub,
            "at": ev["at"],
            "done": True
        })

    patient_name = (
        case["patient"]["name"].split()[0]
        if case["patient"]["name"] != "Unknown patient"
        else "The patient"
    )

    reassurance = None

    if dispatch:
        reassurance = (
            f"{patient_name} is being taken to "
            f"{dispatch['hospital_name']}, "
            f"arriving in about {dispatch['eta_min']:.0f} minutes. "
            f"The care team is ready and waiting. "
            f"You'll get an update the moment they're admitted."
        )

    return {
        "timeline": feed,
        "reassurance": reassurance
    }