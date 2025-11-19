import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List
from datetime import datetime, timezone

from database import db, create_document, get_documents

app = FastAPI(title="LearnOS API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "LearnOS backend running"}


# --- Schema exposure for the data viewer (reads schemas.py automatically) ---
@app.get("/schema")
def schema_index():
    # Lightweight endpoint to let frontend know which collections exist
    return {
        "collections": [
            "session",
            "event",
            "concepttag",
            "note",
        ]
    }


# --- Minimal adaptive event pipeline ---
class EventIn(BaseModel):
    session_id: str
    app: str
    type: str
    payload: Dict[str, Any] | None = None
    ts: float | None = None


@app.post("/event")
def ingest_event(evt: EventIn):
    # Persist raw event
    doc = {
        "session_id": evt.session_id,
        "app": evt.app,
        "type": evt.type,
        "payload": evt.payload or {},
        "client_ts": evt.ts,
        "server_ts": datetime.now(timezone.utc),
    }
    create_document("event", doc)

    # Trivial concept tagging heuristic: map certain actions to tags
    tags: List[str] = []
    p = evt.payload or {}
    if evt.app == "NumberPlay":
        if p.get("operation") in {"add", "sum"}:
            tags.append("addition")
        if p.get("operation") in {"mul", "times"}:
            tags.append("multiplication")
        if isinstance(p.get("values"), list) and len(p.get("values")) >= 3:
            tags.append("pattern_recognition")
    if evt.app == "Sandboxes/Forces" and p.get("built") == "bridge":
        tags.append("equilibrium")

    for t in tags:
        create_document("concepttag", {
            "session_id": evt.session_id,
            "tag": t,
            "confidence": 0.7,
            "source_app": evt.app,
            "server_ts": datetime.now(timezone.utc)
        })

    # Simple adaptation signal for the desktop: suggest lightweight next apps
    suggestions: List[Dict[str, Any]] = []
    if "addition" in tags:
        suggestions.append({
            "id": "NumberPlay-Combos",
            "title": "Number Combos",
            "icon": "Calculator",
            "hint": "Try different ways to make the same total",
        })
    if "equilibrium" in tags:
        suggestions.append({
            "id": "Forces-Balancer",
            "title": "Balance Lab",
            "icon": "Scale",
            "hint": "Can you balance weights with fewer blocks?",
        })

    return {"ok": True, "suggestions": suggestions}


@app.get("/suggest/{session_id}")
def get_suggestions(session_id: str):
    # Look at last 20 concept tags and emit stable set of suggestions
    try:
        recent = get_documents("concepttag", {"session_id": session_id}, limit=50)
    except Exception:
        recent = []
    tags = {d.get("tag") for d in recent}
    suggestions: List[Dict[str, Any]] = []
    if "addition" in tags:
        suggestions.append({
            "id": "NumberPlay-Combos",
            "title": "Number Combos",
            "icon": "Calculator",
        })
    if "pattern_recognition" in tags:
        suggestions.append({
            "id": "PatternGarden",
            "title": "Pattern Garden",
            "icon": "Grid",
        })
    if not suggestions:
        suggestions = [
            {"id": "NumberPlay", "title": "Number Play", "icon": "Calculator"},
            {"id": "PatternGarden", "title": "Pattern Garden", "icon": "Grid"},
            {"id": "Forces", "title": "Forces Sandbox", "icon": "Orbit"},
        ]
    return {"suggestions": suggestions}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = getattr(db, 'name', '✅ Connected')
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
