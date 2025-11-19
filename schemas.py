"""
Database Schemas for LearnOS

Each Pydantic model corresponds to a MongoDB collection. The collection name
is the lowercase of the class name.

- Event -> "event"
- ConceptTag -> "concepttag"
- Session -> "session"
- Note -> "note"

These schemas power adaptive behavior: we log user interactions as Events,
extract lightweight ConceptTags, and keep per-session state.
"""
from typing import Optional, List, Literal, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class Session(BaseModel):
    user_id: Optional[str] = Field(None, description="Anonymous or known user id")
    session_id: str = Field(..., description="Unique session id from frontend")
    context: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary session context")

class Event(BaseModel):
    session_id: str = Field(..., description="Session identifier")
    app: str = Field(..., description="Which app generated the event")
    type: Literal[
        "open_app",
        "close_app",
        "action",
        "discovery",
        "milestone"
    ]
    payload: Dict[str, Any] = Field(default_factory=dict)
    ts: Optional[datetime] = Field(default=None, description="Client timestamp")

class ConceptTag(BaseModel):
    session_id: str
    tag: str = Field(..., description="Concept keyword e.g., 'addition', 'symmetry'")
    confidence: float = Field(0.5, ge=0, le=1)
    source_app: str = Field(...)

class Note(BaseModel):
    session_id: str
    app: str
    content: str

# Example Product/User kept for reference but unused by LearnOS core
class User(BaseModel):
    name: str
    email: str
    is_active: bool = True

class Product(BaseModel):
    title: str
    price: float
    in_stock: bool = True
