"""
LifeLink AI backend
====================
A small multi-agent pipeline behind one FastAPI app:

  IntakeAgent -> SymptomAgent -> VisionAgent -> TriageAgent
      -> HospitalMatchAgent -> GoldenHourAgent -> DispatchAgent
      -> HandoffAgent -> FamilyAgent
                 |                    |
       PredictiveAgent          AnalyticsAgent (rolls up every case)
                 |
          CopilotAgent (chat, independent of any one case)

Everything is kept in memory (CASES dict) so the whole thing runs with
zero external services — swap `CASES` for a real DB and any agent's
internals for a real model call without touching the routes.
"""
import io
import time
import uuid

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .data import HOSPITALS, AMBULANCES, EMERGENCY_PROFILES, DOCTOR_POOL, PATIENT_ROSTER
from .models import NewCaseRequest, PhotoUploadRequest
from .agents import intake_agent, symptom_agent, vision_agent, triage_agent
from .agents import hospital_agent, golden_hour_agent, dispatch_agent
from .agents import family_agent, analytics_agent, handoff_agent, predictive_agent, copilot_agent
from .database import init_db, SessionLocal
from .db_models import CaseRecord
from .auth import require_api_key

app = FastAPI(title="LifeLink AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

CASES: dict[str, dict] = {}


def _persist_case(case: dict):
    """Upsert a case into the database. Best-effort: a DB hiccup should
    never take down the in-memory pipeline everything else relies on."""
    try:
        db = SessionLocal()
        try:
            record = db.get(CaseRecord, case["id"])
            if record:
                record.data = case
                record.created_at = case["created_at"]
            else:
                db.add(CaseRecord(id=case["id"], created_at=case["created_at"], data=case))
            db.commit()
        finally:
            db.close()
    except Exception as e:
        print(f"[warn] failed to persist case {case.get('id')}: {e}")


def log_event(case, stage, note=None):
    case["events"].append({"stage": stage, "at": time.time(), "note": note})
    case["stage"] = stage
    _persist_case(case)


def public_case(case: dict) -> dict:
    out = dict(case)
    out.pop("profile", None)
    out["golden_hour_remaining_sec"] = max(0, round(3600 - (time.time() - case["created_at"])))
    return out


def pick_doctor(specialty: str) -> str:
    import random
    pool = DOCTOR_POOL.get(specialty, DOCTOR_POOL["general"])
    return random.choice(pool)


def _require_case(case_id: str) -> dict:
    case = CASES.get(case_id)
    if not case:
        raise HTTPException(404, "case not found")
    return case


def _set_ambulance_status(ambulance_id: str, status: str):
    for a in AMBULANCES:
        if a["id"] == ambulance_id:
            a["status"] = status
            return


@app.get("/api/health")
def health():
    return {"status": "ok", "time": time.time()}


@app.get("/api/cases")
def list_cases():
    out = []
    for c in CASES.values():
        out.append({
            "id": c["id"],
            "patient_name": c["patient"]["name"],
            "label": c["label"],
            "stage": c["stage"],
            "location": f"{c['lat']:.3f}, {c['lng']:.3f}",
            "risk_level": c["triage"]["risk_level"] if c["triage"] else None,
            "severity_score": c["triage"]["severity_score"] if c["triage"] else None,
            "eta_min": c["dispatch"]["eta_min"] if c["dispatch"] else None,
            "hospital_name": c["dispatch"]["hospital_name"] if c["dispatch"] else None,
            "ambulance_id": c["dispatch"]["ambulance_id"] if c["dispatch"] else None,
            "doctor_assigned": c["dispatch"]["doctor_assigned"] if c["dispatch"] else None,
            "blood_group": c["patient"]["blood_group"],
            "allergies": c["patient"]["allergies"],
            "recommended_tx": c["triage"]["recommended_tx"] if c["triage"] else None,
        })
    out.sort(key=lambda x: x["id"])
    return out


@app.get("/api/hospitals")
def list_hospitals():
    return HOSPITALS


@app.get("/api/ambulances")
def list_ambulances():
    return AMBULANCES


@app.get("/api/patients")
def list_patients():
    return PATIENT_ROSTER


# ---------------------------------------------------------------- Intake ---
@app.post("/api/cases", dependencies=[Depends(require_api_key)])
def create_case(req: NewCaseRequest):
    resolved = intake_agent.open_case(req.emergency_type, req.patient_id)
    case_id = "PIQ-" + str(uuid.uuid4().int)[:5]
    case = {
        "id": case_id,
        "emergency_type": req.emergency_type,
        "label": resolved["profile"]["label"],
        "icon": resolved["profile"]["icon"],
        "created_at": time.time(),
        "lat": req.lat,
        "lng": req.lng,
        "patient": resolved["patient"],
        "profile": resolved["profile"],
        "stage": "reported",
        "transcript": [],
        "answered_count": 0,
        "vision": None,
        "triage": None,
        "hospitals": None,
        "golden_hour": None,
        "dispatch": None,
        "events": [],
    }
    log_event(case, "reported")
    CASES[case_id] = case
    return public_case(case)


@app.get("/api/cases/{case_id}")
def get_case(case_id: str):
    return public_case(_require_case(case_id))


# --------------------------------------------------------------- Symptom ---
@app.post("/api/cases/{case_id}/voice/next", dependencies=[Depends(require_api_key)])
def voice_next(case_id: str):
    case = _require_case(case_id)
    turn = symptom_agent.next_turn(case["profile"], case["answered_count"])
    if turn is None:
        return {"done": True, "symptom_tags": symptom_agent.extracted_tags(case["profile"], case["answered_count"])}
    case["transcript"].append({"q": turn["q"], "a": turn["a"]})
    case["answered_count"] += 1
    tags = symptom_agent.extracted_tags(case["profile"], case["answered_count"])
    done = turn["step"] + 1 >= turn["total"]
    if done:
        log_event(case, "symptoms_analyzed", note=f"{len(tags)} symptom tags extracted")
    else:
        _persist_case(case)
    return {
        "done": False,
        "step": turn["step"] + 1,
        "total": turn["total"],
        "question": turn["q"],
        "answer": turn["a"],
        "symptom_tags": tags,
    }


# ---------------------------------------------------------------- Vision ---
@app.post("/api/cases/{case_id}/photo", dependencies=[Depends(require_api_key)])
def upload_photo(case_id: str, req: PhotoUploadRequest):
    case = _require_case(case_id)
    result = vision_agent.analyze(case["profile"], req.filename)
    case["vision"] = result
    top_tag = result["tags"][0]["name"] if result["tags"] else "scene"
    log_event(case, "vision_analyzed", note=f"Vision detected {top_tag.lower()}")
    return result


# ---------------------------------------------------------------- Triage ---
@app.post("/api/cases/{case_id}/triage", dependencies=[Depends(require_api_key)])
def run_triage(case_id: str):
    case = _require_case(case_id)
    tags = symptom_agent.extracted_tags(case["profile"], case["answered_count"])
    result = triage_agent.assess(case["profile"], case["patient"], tags, case["vision"] is not None)
    case["triage"] = result
    log_event(case, "assessed", note=f"Risk {result['severity_score']}%")
    return result


@app.get("/api/cases/{case_id}/predictive")
def predictive(case_id: str):
    case = _require_case(case_id)
    result = predictive_agent.predict(case["profile"], case["triage"])
    if result is None:
        raise HTTPException(400, "triage has not run yet")
    return result


# -------------------------------------------------------------- Hospital ---
@app.get("/api/cases/{case_id}/hospitals")
def rank_hospitals(case_id: str):
    case = _require_case(case_id)
    risk = case["triage"]["risk_level"] if case["triage"] else "Moderate"
    ranked = hospital_agent.rank(
        HOSPITALS, case["lat"], case["lng"], case["emergency_type"],
        case["patient"]["blood_group"], risk,
    )
    case["hospitals"] = ranked

    gh = golden_hour_agent.decide(ranked, risk)
    case["golden_hour"] = gh
    return {
        "hospitals": gh["ranked"],
        "winner_id": gh["winner_id"],
        "nearest_id": gh["nearest_id"],
        "explanation": gh["explanation"],
    }


# -------------------------------------------------------------- Dispatch ---
@app.post("/api/cases/{case_id}/dispatch", dependencies=[Depends(require_api_key)])
def dispatch_case(case_id: str, hospital_id: str | None = None):
    case = _require_case(case_id)
    if not case["hospitals"]:
        rank_hospitals(case_id)
    ranked = case["golden_hour"]["ranked"]
    chosen = None
    if hospital_id:
        chosen = next((h for h in ranked if h["id"] == hospital_id), None)
    chosen = chosen or ranked[0]
    hosp = next(h for h in HOSPITALS if h["id"] == chosen["id"])

    specialty = hospital_agent.SPECIALTY_BY_EMERGENCY.get(case["emergency_type"], "general")
    doctor = pick_doctor(specialty)

    result = dispatch_agent.dispatch(
        AMBULANCES, case["lat"], case["lng"], hosp["lat"], hosp["lng"], hosp["name"], doctor_assigned=doctor
    )
    case["dispatch"] = result
    _set_ambulance_status(result["ambulance_id"], "dispatched")
    log_event(case, "hospital_selected", note=hosp["name"])
    log_event(case, "dispatched", note=result["ambulance_id"])
    return result


@app.get("/api/cases/{case_id}/track")
def track_case(case_id: str):
    case = _require_case(case_id)
    if not case["dispatch"]:
        raise HTTPException(400, "case has not been dispatched yet")
    pos = dispatch_agent.live_position(case["dispatch"])
    if pos["progress_pct"] > 15 and case["stage"] == "dispatched":
        log_event(case, "en_route")
    if pos["arrived"] and case["stage"] != "arrived":
        log_event(case, "arrived")
        _set_ambulance_status(case["dispatch"]["ambulance_id"], "available")
    pos["golden_hour_remaining_sec"] = max(0, round(3600 - (time.time() - case["created_at"])))
    return pos


# ---------------------------------------------------------------- Handoff --
@app.get("/api/cases/{case_id}/handoff")
def handoff(case_id: str):
    case = _require_case(case_id)
    return handoff_agent.build_handoff(case)


@app.get("/api/cases/{case_id}/report.pdf")
def report_pdf(case_id: str):
    case = _require_case(case_id)
    h = handoff_agent.build_handoff(case)

    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.pdfgen import canvas as pdfcanvas

    buf = io.BytesIO()
    c = pdfcanvas.Canvas(buf, pagesize=A4)
    w, hgt = A4
    x = 20 * mm
    y = hgt - 22 * mm

    def line(txt, size=10, bold=False, gap=6.2 * mm, color=colors.black):
        nonlocal y
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.setFillColor(color)
        c.drawString(x, y, txt)
        y -= gap

    c.setFillColor(colors.HexColor("#0B1220"))
    c.rect(0, hgt - 26 * mm, w, 26 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(x, hgt - 12 * mm, "LifeLink AI — Emergency Summary")
    c.setFont("Helvetica", 9)
    c.drawString(x, hgt - 19 * mm, f"Case {h['case_id']}  ·  Generated {time.strftime('%d %b %Y, %H:%M', time.localtime(h['generated_at']))}")
    y = hgt - 34 * mm

    line("Chief Complaint", 11, True); line(h["chief_complaint"], 10, gap=8 * mm)
    line("Patient", 11, True); line(h["patient_line"], 10, gap=8 * mm)

    risk_color = colors.HexColor("#FF3B30") if h["risk_level"] == "Critical" else colors.HexColor("#FFB020") if h["risk_level"] == "High" else colors.black
    line("AI Risk Assessment", 11, True)
    line(f"{h['risk_level']}  (severity {h['severity_score']}/100)", 10, bold=True, gap=8 * mm, color=risk_color)

    line("Key Findings", 11, True)
    for f in h["key_findings"]:
        line(f"• {f}", 9.5, gap=5.4 * mm)
    y -= 2 * mm

    line("Recommended Treatment", 11, True)
    line(h["recommended_tx"], 10, bold=True)
    for a in h["recommended_actions"]:
        line(f"✔ {a}", 9.5, gap=5.4 * mm)
    y -= 2 * mm

    line("Destination & Logistics", 11, True)
    line(f"Hospital: {h['destination'] or 'Pending'}", 9.5, gap=5.4 * mm)
    line(f"Doctor assigned: {h['doctor_assigned'] or 'Pending'}", 9.5, gap=5.4 * mm)
    line(f"Ambulance: {h['ambulance_id'] or 'Pending'}   ETA: {h['eta_min'] if h['eta_min'] is not None else '—'} min", 9.5, gap=5.4 * mm)

    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(colors.grey)
    c.drawString(x, 14 * mm, "Generated by LifeLink AI multi-agent pipeline — for demonstration purposes.")
    c.showPage()
    c.save()
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/pdf", headers={
        "Content-Disposition": f'inline; filename="lifelink-{case_id}-summary.pdf"'
    })


# ---------------------------------------------------------------- Family ---
@app.get("/api/cases/{case_id}/family")
def family_view(case_id: str):
    case = _require_case(case_id)
    return family_agent.build_feed(case)


# ---------------------------------------------------------------- Copilot --
class CopilotMessage(BaseModel):
    message: str
    case_id: str | None = None


@app.post("/api/copilot")
def copilot(msg: CopilotMessage):
    case = CASES.get(msg.case_id) if msg.case_id else None
    return copilot_agent.respond(msg.message, case)


# ------------------------------------------------------------- Analytics ---
@app.get("/api/analytics/dashboard")
def analytics_dashboard():
    return analytics_agent.build_dashboard(CASES, HOSPITALS)


# ------------------------------------------------------------------ Seed ---
def _seed_case(emergency_type, patient_id, lat, lng):
    resolved = intake_agent.open_case(emergency_type, patient_id)
    case_id = "PIQ-" + str(uuid.uuid4().int)[:5]
    case = {
        "id": case_id, "emergency_type": emergency_type,
        "label": resolved["profile"]["label"], "icon": resolved["profile"]["icon"],
        "created_at": time.time(), "lat": lat, "lng": lng,
        "patient": resolved["patient"], "profile": resolved["profile"],
        "stage": "reported", "transcript": [], "answered_count": 0,
        "vision": None, "triage": None, "hospitals": None, "golden_hour": None, "dispatch": None,
        "events": [],
    }
    log_event(case, "reported")
    for _ in resolved["profile"]["questions"]:
        symptom_agent.next_turn(case["profile"], case["answered_count"])
        case["answered_count"] += 1
    case["vision"] = vision_agent.analyze(case["profile"], "scene.jpg")
    tags = symptom_agent.extracted_tags(case["profile"], case["answered_count"])
    case["triage"] = triage_agent.assess(case["profile"], case["patient"], tags, True)
    log_event(case, "assessed")
    ranked = hospital_agent.rank(HOSPITALS, lat, lng, emergency_type, case["patient"]["blood_group"], case["triage"]["risk_level"])
    case["hospitals"] = ranked
    gh = golden_hour_agent.decide(ranked, case["triage"]["risk_level"])
    case["golden_hour"] = gh
    hosp = next(h for h in HOSPITALS if h["id"] == gh["winner_id"])
    specialty = hospital_agent.SPECIALTY_BY_EMERGENCY.get(emergency_type, "general")
    case["dispatch"] = dispatch_agent.dispatch(AMBULANCES, lat, lng, hosp["lat"], hosp["lng"], hosp["name"], doctor_assigned=pick_doctor(specialty))
    _set_ambulance_status(case["dispatch"]["ambulance_id"], "dispatched")
    log_event(case, "hospital_selected")
    log_event(case, "dispatched")
    CASES[case_id] = case


@app.on_event("startup")
def on_startup():
    init_db()
    _load_cases_from_db()
    if not CASES:
        _seed_case("accident", "anita-29", 28.60, 77.19)
        _seed_case("heart_attack", "suresh-61", 28.55, 77.23)


def _load_cases_from_db():
    try:
        db = SessionLocal()
        try:
            for record in db.query(CaseRecord).all():
                CASES[record.id] = record.data
        finally:
            db.close()
    except Exception as e:
        print(f"[warn] failed to load cases from database: {e}")




# ------------------------------------------------------- Serve frontend ---
from pathlib import Path

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
