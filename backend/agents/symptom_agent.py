"""
SymptomAgent
------------
Stands in for a real speech-to-text + NLU pipeline. Walks the bystander
through a short, emergency-specific question set (an actual ambulance
dispatcher script uses the same structure) and extracts structured
symptom tags as each answer comes in, rather than requiring anyone to type.
"""


def next_turn(profile: dict, index: int):
    questions = profile["questions"]
    if index >= len(questions):
        return None
    return {"step": index, "total": len(questions), **questions[index]}


def extracted_tags(profile: dict, answered_count: int):
    """Symptom tags 'discovered' scale with how much of the transcript has
    played, so the assessment view can show live-building evidence."""
    tags = profile["symptom_tags"]
    n = max(1, round(len(tags) * answered_count / max(1, len(profile["questions"]))))
    return tags[:n]
