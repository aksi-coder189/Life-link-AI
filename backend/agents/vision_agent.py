"""
VisionAgent
-----------
Stands in for a CV model reading an uploaded scene/injury photo. In this
demo it returns the emergency-type's characteristic findings; swap
`analyze()` for a real image-classification call (e.g. a vision model
prompted for injury tags) without touching any other agent.
"""
import time


def analyze(profile: dict, filename: str):
    return {
        "filename": filename,
        "analyzed_at": time.time(),
        "tags": profile["vision_tags"],
    }
