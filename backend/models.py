from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class NewCaseRequest(BaseModel):
    emergency_type: str            # key into EMERGENCY_PROFILES
    lat: float
    lng: float
    patient_id: Optional[str] = None   # roster id, or None -> unknown patient generated


class PhotoUploadRequest(BaseModel):
    filename: Optional[str] = "scene.jpg"


class CaseOut(BaseModel):
    id: str
    emergency_type: str
    label: str
    icon: str
    created_at: float
    lat: float
    lng: float
    patient: Dict[str, Any]
    stage: str
    transcript: List[Dict[str, str]]
    vision: Optional[List[Dict[str, str]]] = None
    triage: Optional[Dict[str, Any]] = None
    hospitals: Optional[List[Dict[str, Any]]] = None
    dispatch: Optional[Dict[str, Any]] = None
    events: List[Dict[str, Any]]
