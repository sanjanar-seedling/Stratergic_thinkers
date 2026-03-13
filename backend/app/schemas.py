from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models import EventSource, EventType

class FounderEventCreate(BaseModel):
    source: EventSource
    event_type: EventType
    text: str
    encrypted: bool = False
    context: Optional[Dict[str, Any]] = None

class FounderEventResponse(BaseModel):
    id: str
    source: EventSource
    event_type: EventType
    scrubbed_text: str
    context: Optional[Dict[str, Any]] = None
    created_at: datetime

class DecisionCreate(BaseModel):
    title: str
    rationale: str
    expected_outcome: str
    expected_outcome_date: Optional[str] = None
    confidence_score: float
    alternatives: List[str] = []

class DecisionResponse(DecisionCreate):
    id: str
    status: str
    actual_outcome: Optional[str] = None
    outcome_score: Optional[float] = None
    created_at: datetime

class DecisionResolve(BaseModel):
    actual_outcome: str
    outcome_score: float

class TranscriptionResponse(BaseModel):
    text: str
    duration_seconds: float

class DashboardStats(BaseModel):
    total_decisions: int
    avg_accuracy: float
    biases_caught: int
    open_decisions: int

class BiasDetection(BaseModel):
    id: str
    bias_type: str
    description: str
    severity: str
    created_at: datetime

class GrowthDataPoint(BaseModel):
    month: str
    confidence: float
    accuracy: float
    reflection_count: int

class SparringContinueRequest(BaseModel):
    conversation_history: List[Dict[str, str]]
    user_message: str

class IntegrationSyncResponse(BaseModel):
    status: str
    events_created: int
    services_synced: List[str]
