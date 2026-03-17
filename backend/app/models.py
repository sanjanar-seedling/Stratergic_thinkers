"""Database Models for Event Storage.

SQLAlchemy models for:
- Users
- FounderEvents
- Patterns
- Insights
- Interventions
- DecisionOutcomes (for judgment tracking)
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    JSON,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum

Base = declarative_base()


class User(Base):
    """User account."""

    __tablename__ = "users"
    __table_args__ = {"schema": "seedlings"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    
    # Encryption keys (stored encrypted with user password)
    encryption_salt = Column(String(255))  # For key derivation
    public_key = Column(Text)  # RSA public key
    
    # Privacy settings
    privacy_settings = Column(JSON, default={})
    intervention_preferences = Column(JSON, default={})
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)
    
    # Relationships
    events = relationship("FounderEvent", back_populates="user", cascade="all, delete-orphan")
    patterns = relationship("Pattern", back_populates="user", cascade="all, delete-orphan")
    interventions = relationship("Intervention", back_populates="user", cascade="all, delete-orphan")
    decision_outcomes = relationship("DecisionOutcome", back_populates="user", cascade="all, delete-orphan")


class EventType(str, enum.Enum):
    """Event type enumeration."""
    REFLECTION = "reflection"
    DECISION_RECORD = "decision_record"
    WEEKLY_REVIEW = "weekly_review"
    TIME_ALLOCATION = "time_allocation"


class EventSource(str, enum.Enum):
    """Event source enumeration."""
    EMAIL = "email"
    SLACK = "slack"
    VOICE = "voice"
    WEB = "web"
    GOOGLE_CALENDAR = "google_calendar"


class FounderEvent(Base):
    """Founder event (reflection, decision, etc.)."""

    __tablename__ = "founder_events"
    __table_args__ = {"schema": "seedlings"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("seedlings.users.id"), nullable=False, index=True)
    
    # Event metadata
    source = Column(SQLEnum(EventSource), nullable=False)
    event_type = Column(SQLEnum(EventType), nullable=False)
    
    # Content (encrypted)
    encrypted_text = Column(Text, nullable=False)  # Encrypted content
    encryption_nonce = Column(String(255))  # For AES-GCM
    encryption_tag = Column(String(255))  # For AES-GCM
    
    # Anonymized version for AI processing
    anonymized_text = Column(Text)  # PII-stripped version
    anonymization_mapping = Column(JSON)  # Pseudonym -> original mapping (encrypted)
    
    # Context
    context = Column(JSON, default={})  # Source-specific metadata
    tags = Column(JSON, default=[])  # User-defined tags
    
    # Privacy
    privacy_mode = Column(String(50))  # "normal", "reflection_only", "no_storage"
    
    # Embeddings
    embedding = Column(JSON)  # Vector embedding for semantic search
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    processed_at = Column(DateTime)  # When AI processing completed
    archived_at = Column(DateTime)  # When moved to cold storage
    
    # Relationships
    user = relationship("User", back_populates="events")
    patterns = relationship("Pattern", secondary="seedlings.event_patterns", back_populates="events")


class PatternType(str, enum.Enum):
    """Pattern type enumeration."""
    DECISION_FRAMEWORK = "decision_framework"
    COGNITIVE_BIAS = "cognitive_bias"
    AVOIDANCE = "avoidance"
    DECISION_VELOCITY = "decision_velocity"
    EMOTIONAL_STATE = "emotional_state"
    TIME_DRIFT = "time_drift"


class Pattern(Base):
    """Detected pattern in founder behavior."""

    __tablename__ = "patterns"
    __table_args__ = {"schema": "seedlings"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("seedlings.users.id"), nullable=False, index=True)
    
    pattern_type = Column(SQLEnum(PatternType), nullable=False)
    name = Column(String(255), nullable=False)  # e.g., "Sunk Cost Fallacy"
    description = Column(Text)
    
    # Confidence and frequency
    confidence = Column(Float)  # 0.0 to 1.0
    frequency = Column(Integer)  # Number of occurrences
    
    # Pattern-specific data (renamed from metadata to avoid SQLAlchemy conflict)
    pattern_data = Column(JSON, default={})  # Pattern-specific data
    
    # Timestamps
    first_detected = Column(DateTime, nullable=False)
    last_seen = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="patterns")
    events = relationship("FounderEvent", secondary="seedlings.event_patterns", back_populates="patterns")
    interventions = relationship("Intervention", back_populates="pattern")


class EventPattern(Base):
    """Association table for events and patterns."""

    __tablename__ = "event_patterns"
    __table_args__ = {"schema": "seedlings"}

    event_id = Column(UUID(as_uuid=True), ForeignKey("seedlings.founder_events.id"), primary_key=True)
    pattern_id = Column(UUID(as_uuid=True), ForeignKey("seedlings.patterns.id"), primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class InterventionTrigger(str, enum.Enum):
    """Intervention trigger type."""
    PATTERN = "pattern"
    TIME = "time"
    CONTEXT = "context"
    DRIFT = "drift"


class InterventionStatus(str, enum.Enum):
    """Intervention status."""
    PENDING = "pending"
    SENT = "sent"
    RESPONDED = "responded"
    DISMISSED = "dismissed"
    EXPIRED = "expired"


class Intervention(Base):
    """AI intervention (reflection prompt)."""

    __tablename__ = "interventions"
    __table_args__ = {"schema": "seedlings"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("seedlings.users.id"), nullable=False, index=True)
    pattern_id = Column(UUID(as_uuid=True), ForeignKey("seedlings.patterns.id"), nullable=True)
    
    # Intervention details
    trigger_type = Column(SQLEnum(InterventionTrigger), nullable=False)
    prompt_type = Column(String(50))  # "clarifying", "challenging", "integrating"
    question = Column(Text, nullable=False)
    context = Column(Text)  # Why this question now
    priority = Column(String(20))  # "low", "medium", "high"
    
    # Status
    status = Column(SQLEnum(InterventionStatus), default=InterventionStatus.PENDING, nullable=False)
    
    # Response
    response_text = Column(Text)  # User's response (encrypted)
    response_event_id = Column(UUID(as_uuid=True), ForeignKey("seedlings.founder_events.id"))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    sent_at = Column(DateTime)
    responded_at = Column(DateTime)
    expires_at = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="interventions")
    pattern = relationship("Pattern", back_populates="interventions")


class DecisionOutcome(Base):
    """Tracks decision outcomes for judgment quality scoring."""

    __tablename__ = "decision_outcomes"
    __table_args__ = {"schema": "seedlings"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("seedlings.users.id"), nullable=False, index=True)
    decision_event_id = Column(UUID(as_uuid=True), ForeignKey("seedlings.founder_events.id"), nullable=False)
    
    # Decision details
    decision_summary = Column(Text)  # Brief summary of decision
    
    # Prediction (at time of decision)
    predicted_outcome = Column(String(50))  # "success", "failure", "neutral"
    confidence_level = Column(Float)  # 0.0 to 1.0 (how confident was the founder?)
    predicted_impact = Column(String(50))  # "high", "medium", "low"
    
    # Actual outcome (retrospective)
    actual_outcome = Column(String(50))  # "success", "failure", "neutral"
    actual_impact = Column(String(50))  # "high", "medium", "low"
    outcome_notes = Column(Text)  # What actually happened
    
    # Judgment quality metrics
    was_correct = Column(Boolean)  # Did prediction match outcome?
    calibration_error = Column(Float)  # |confidence - accuracy|
    
    # Frameworks used
    frameworks_applied = Column(JSON, default=[])  # List of framework IDs
    
    # Timestamps
    decision_date = Column(DateTime, nullable=False)
    outcome_recorded_date = Column(DateTime)  # When outcome was assessed
    followup_date = Column(DateTime)  # When to check outcome (e.g., 30/60/90 days)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="decision_outcomes")


class Framework(Base):
    """Strategic framework or mental model."""

    __tablename__ = "frameworks"
    __table_args__ = {"schema": "seedlings"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=False)
    source = Column(String(255))  # Book/article reference
    category = Column(String(100))  # "decision_making", "strategy", "execution"
    when_to_use = Column(Text)
    example = Column(Text)
    
    # Embedding for semantic search
    embedding = Column(JSON)
    
    # Usage tracking
    times_recommended = Column(Integer, default=0)
    times_applied = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FrameworkApplication(Base):
    """Tracks when a framework was applied to a decision."""

    __tablename__ = "framework_applications"
    __table_args__ = {"schema": "seedlings"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("seedlings.users.id"), nullable=False)
    framework_id = Column(UUID(as_uuid=True), ForeignKey("seedlings.frameworks.id"), nullable=False)
    decision_event_id = Column(UUID(as_uuid=True), ForeignKey("seedlings.founder_events.id"), nullable=False)
    decision_outcome_id = Column(UUID(as_uuid=True), ForeignKey("seedlings.decision_outcomes.id"))
    
    # How it was applied
    application_notes = Column(Text)  # How the founder used this framework
    was_helpful = Column(Boolean)  # Founder's self-assessment
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
