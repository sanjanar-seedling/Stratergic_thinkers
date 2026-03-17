"""API Endpoints for Insights and Interventions.

Provides:
- Pattern insights (cognitive biases, decision frameworks)
- Time allocation drift analysis
- Intervention management
- Framework recommendations
- Judgment quality metrics
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import (
    FounderEvent,
    Pattern,
    Intervention,
    DecisionOutcome,
    Framework,
    FrameworkApplication,
    PatternType,
    InterventionStatus,
)
from app.services.pattern_recognition import PatternRecognitionEngine
from app.services.state_tracking import StateTrackingEngine
from app.services.rag_pipeline import RAGPipeline
from app.services.intervention import InterventionEngine
from app.core.llm_provider import get_llm_provider

logger = logging.getLogger(__name__)
router = APIRouter()


# ========== Request/Response Models ==========

class PatternResponse(BaseModel):
    """Pattern insight response."""
    id: UUID
    pattern_type: str
    name: str
    description: str
    confidence: float
    frequency: int
    first_detected: datetime
    last_seen: datetime
    metadata: dict

    class Config:
        from_attributes = True


class InterventionResponse(BaseModel):
    """Intervention response."""
    id: UUID
    trigger_type: str
    prompt_type: str
    question: str
    context: str
    priority: str
    status: str
    created_at: datetime
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True


class InterventionResponseRequest(BaseModel):
    """User response to intervention."""
    response_text: str


class FrameworkRecommendationResponse(BaseModel):
    """Framework recommendation."""
    framework_id: UUID
    name: str
    description: str
    relevance_score: float
    reasoning: str
    when_to_use: str
    example: str


class JudgmentMetricsResponse(BaseModel):
    """Judgment quality metrics."""
    total_decisions: int
    decisions_with_outcomes: int
    accuracy_rate: float  # % of correct predictions
    average_confidence: float
    calibration_score: float  # How well confidence matches accuracy
    improvement_trend: str  # "improving", "stable", "declining"


class TimeDriftResponse(BaseModel):
    """Time allocation drift."""
    category: str
    stated_priority: float
    actual_time: float
    drift_percentage: float
    severity: str
    recommendation: str


# ========== Insights Endpoints ==========

@router.get("/insights/patterns", response_model=List[PatternResponse])
async def get_patterns(
    pattern_type: Optional[str] = Query(None),
    lookback_days: int = Query(90, ge=1, le=365),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detected patterns for current user.
    
    Args:
        pattern_type: Filter by pattern type (optional)
        lookback_days: How far back to look (default: 90 days)
    """
    user_id = UUID(current_user["id"])
    cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)

    # Build query
    query = select(Pattern).where(
        and_(
            Pattern.user_id == user_id,
            Pattern.last_seen >= cutoff_date,
        )
    )

    if pattern_type:
        query = query.where(Pattern.pattern_type == pattern_type)

    query = query.order_by(desc(Pattern.confidence))

    result = await db.execute(query)
    patterns = result.scalars().all()

    return patterns


@router.get("/insights/biases", response_model=List[PatternResponse])
async def get_cognitive_biases(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detected cognitive biases."""
    user_id = UUID(current_user["id"])

    query = select(Pattern).where(
        and_(
            Pattern.user_id == user_id,
            Pattern.pattern_type == PatternType.COGNITIVE_BIAS,
        )
    ).order_by(desc(Pattern.last_seen))

    result = await db.execute(query)
    biases = result.scalars().all()

    return biases


@router.get("/insights/drift", response_model=List[TimeDriftResponse])
async def get_time_drift(
    lookback_days: int = Query(30, ge=7, le=90),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get time allocation drift analysis.
    
    Compares stated priorities (from weekly reviews) with actual time spent (from calendar).
    """
    user_id = UUID(current_user["id"])
    cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)

    # Get weekly review events (stated priorities)
    weekly_reviews = await db.execute(
        select(FounderEvent).where(
            and_(
                FounderEvent.user_id == user_id,
                FounderEvent.event_type == "weekly_review",
                FounderEvent.created_at >= cutoff_date,
            )
        ).order_by(desc(FounderEvent.created_at)).limit(1)
    )
    latest_review = weekly_reviews.scalar_one_or_none()

    # Get time allocation events (actual time)
    time_events = await db.execute(
        select(FounderEvent).where(
            and_(
                FounderEvent.user_id == user_id,
                FounderEvent.event_type == "time_allocation",
                FounderEvent.created_at >= cutoff_date,
            )
        )
    )
    time_data = time_events.scalars().all()

    if not latest_review or not time_data:
        return []

    # Extract stated priorities from review
    # Parse from review context or extract from text if structured
    import re
    stated_priorities = latest_review.context.get("priorities", {})
    if not stated_priorities and latest_review.scrubbed_text:
        # Simple extraction of priorities mentioned in text (e.g., "priority: product, fundraising")
        priority_match = re.search(r'priority[s]?[\s:]+([^\n]+)', latest_review.scrubbed_text, re.IGNORECASE)
        if priority_match:
            priorities_text = priority_match.group(1)
            for priority in priorities_text.split(","):
                category = priority.strip().lower()
                if category:
                    stated_priorities[category] = stated_priorities.get(category, 0) + 1

    # Calculate actual time from calendar events
    # Aggregate time allocations from all time_allocation events
    actual_time = {}
    event_count = 0
    for event in time_data:
        category_dist = event.context.get("category_distribution", {})
        if category_dist:
            for category, percentage in category_dist.items():
                actual_time[category] = actual_time.get(category, 0) + percentage
        else:
            # If no category distribution, track event count for averaging
            event_count += 1
    
    # Average out multiple events if distribution data exists
    if time_data and actual_time:
        for category in actual_time:
            actual_time[category] = actual_time[category] / len(time_data)

    # Normalize actual_time
    total = sum(actual_time.values())
    if total > 0:
        actual_time = {k: v / total for k, v in actual_time.items()}

    # Detect drift
    engine = StateTrackingEngine()
    drifts = engine.detect_time_allocation_drift(
        stated_priorities,
        actual_time,
        threshold=0.15,
    )

    return [drift.dict() for drift in drifts]


@router.post("/insights/analyze", response_model=dict)
async def trigger_analysis(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger on-demand analysis of recent events.
    
    Returns:
        Summary of detected patterns and insights
    """
    user_id = UUID(current_user["id"])
    cutoff_date = datetime.utcnow() - timedelta(days=90)

    # Fetch recent events
    result = await db.execute(
        select(FounderEvent).where(
            and_(
                FounderEvent.user_id == user_id,
                FounderEvent.created_at >= cutoff_date,
            )
        ).order_by(FounderEvent.created_at)
    )
    events = result.scalars().all()

    if not events:
        return {"message": "No events to analyze"}

    # Convert to dict format for analysis engines
    event_dicts = [
        {
            "id": str(e.id),
            "event_type": e.event_type.value,
            "text": e.anonymized_text or "[encrypted]",
            "created_at": e.created_at.isoformat(),
            "context": e.context,
        }
        for e in events
    ]

    # Run pattern recognition
    pattern_engine = PatternRecognitionEngine()
    patterns = pattern_engine.analyze_decision_patterns(event_dicts)
    biases = pattern_engine.detect_cognitive_biases(event_dicts)
    avoidance = pattern_engine.detect_avoidance_patterns(event_dicts)

    # Run state tracking
    state_engine = StateTrackingEngine()
    emotional_analysis = state_engine.analyze_emotional_patterns(event_dicts)

    return {
        "analyzed_events": len(events),
        "patterns_detected": len(patterns),
        "biases_detected": len(biases),
        "avoidance_patterns": len(avoidance),
        "emotional_analysis": emotional_analysis,
        "timestamp": datetime.utcnow().isoformat(),
    }


# ========== Intervention Endpoints ==========

@router.get("/interventions", response_model=List[InterventionResponse])
async def get_interventions(
    status: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get interventions for current user.
    
    Args:
        status: Filter by status (pending, sent, responded, dismissed, expired)
    """
    user_id = UUID(current_user["id"])

    query = select(Intervention).where(Intervention.user_id == user_id)

    if status:
        query = query.where(Intervention.status == status)
    else:
        # Default: show pending and sent
        query = query.where(
            Intervention.status.in_([InterventionStatus.PENDING, InterventionStatus.SENT])
        )

    query = query.order_by(desc(Intervention.created_at))

    result = await db.execute(query)
    interventions = result.scalars().all()

    return interventions


@router.post("/interventions/{intervention_id}/respond")
async def respond_to_intervention(
    intervention_id: UUID,
    response: InterventionResponseRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Respond to an intervention."""
    user_id = UUID(current_user["id"])

    # Get intervention
    result = await db.execute(
        select(Intervention).where(
            and_(
                Intervention.id == intervention_id,
                Intervention.user_id == user_id,
            )
        )
    )
    intervention = result.scalar_one_or_none()

    if not intervention:
        raise HTTPException(status_code=404, detail="Intervention not found")

    # Update intervention
    intervention.response_text = response.response_text
    intervention.status = InterventionStatus.RESPONDED
    intervention.responded_at = datetime.utcnow()

    # Create a new FounderEvent from the response for analysis
    response_event = FounderEvent(
        user_id=current_user["id"],
        source="web",
        event_type="reflection",
        scrubbed_text=response.response_text,
        context={
            "intervention_id": str(intervention_id),
            "response_to": intervention.prompt_text,
            "auto_generated": False,
        },
    )
    db.add(response_event)
    
    # Queue follow-up analysis via Redis
    try:
        import redis as redis_lib
        redis_client = redis_lib.from_url("redis://localhost:6379", decode_responses=True)
        redis_client.xadd(
            "analysis_tasks",
            {
                "user_id": str(current_user["id"]),
                "event_id": str(response_event.id),
                "action": "analyze_intervention_response",
            }
        )
        logger.info(f"Follow-up analysis queued for intervention response: {intervention_id}")
    except Exception as e:
        logger.warning(f"Failed to queue follow-up analysis: {e}")

    await db.commit()

    return {"message": "Response recorded", "intervention_id": str(intervention_id)}


@router.post("/interventions/{intervention_id}/dismiss")
async def dismiss_intervention(
    intervention_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Dismiss an intervention without responding."""
    user_id = UUID(current_user["id"])

    result = await db.execute(
        select(Intervention).where(
            and_(
                Intervention.id == intervention_id,
                Intervention.user_id == user_id,
            )
        )
    )
    intervention = result.scalar_one_or_none()

    if not intervention:
        raise HTTPException(status_code=404, detail="Intervention not found")

    intervention.status = InterventionStatus.DISMISSED
    await db.commit()

    return {"message": "Intervention dismissed"}


# ========== Framework Endpoints ==========

@router.get("/frameworks", response_model=List[dict])
async def list_frameworks(
    category: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List all available frameworks."""
    query = select(Framework)

    if category:
        query = query.where(Framework.category == category)

    query = query.order_by(Framework.name)

    result = await db.execute(query)
    frameworks = result.scalars().all()

    return [
        {
            "id": str(f.id),
            "name": f.name,
            "description": f.description,
            "source": f.source,
            "category": f.category,
            "when_to_use": f.when_to_use,
            "example": f.example,
            "times_recommended": f.times_recommended,
            "times_applied": f.times_applied,
        }
        for f in frameworks
    ]


@router.post("/frameworks/recommend", response_model=List[FrameworkRecommendationResponse])
async def recommend_frameworks(
    context: str,
    top_k: int = Query(3, ge=1, le=10),
    current_user: dict = Depends(get_current_user),
):
    """Get framework recommendations for a given context.
    
    Args:
        context: The decision or situation text
        top_k: Number of recommendations to return
    """
    llm = get_llm_provider()
    rag = RAGPipeline(llm)

    # Get recommendations
    result = await rag.suggest_frameworks_for_decision(context)

    recommendations = []
    for rec in result.get("recommendations", []):
        framework = rec["framework"]
        recommendations.append(
            FrameworkRecommendationResponse(
                framework_id=framework.get("id", "unknown"),
                name=framework["name"],
                description=framework["description"],
                relevance_score=rec["relevance_score"],
                reasoning=rec["reasoning"],
                when_to_use=framework["when_to_use"],
                example=framework["example"],
            )
        )

    return recommendations


# ========== Judgment Quality Endpoints ==========

@router.get("/judgment/metrics", response_model=JudgmentMetricsResponse)
async def get_judgment_metrics(
    lookback_days: int = Query(365, ge=30, le=730),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get judgment quality metrics.
    
    Analyzes how well the founder's predictions match actual outcomes.
    """
    user_id = UUID(current_user["id"])
    cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)

    # Get all decision outcomes
    result = await db.execute(
        select(DecisionOutcome).where(
            and_(
                DecisionOutcome.user_id == user_id,
                DecisionOutcome.decision_date >= cutoff_date,
            )
        ).order_by(DecisionOutcome.decision_date)
    )
    outcomes = result.scalars().all()

    total_decisions = len(outcomes)
    decisions_with_outcomes = len([o for o in outcomes if o.actual_outcome is not None])

    if decisions_with_outcomes == 0:
        return JudgmentMetricsResponse(
            total_decisions=total_decisions,
            decisions_with_outcomes=0,
            accuracy_rate=0.0,
            average_confidence=0.0,
            calibration_score=0.0,
            improvement_trend="insufficient_data",
        )

    # Calculate metrics
    correct_predictions = sum(1 for o in outcomes if o.was_correct)
    accuracy_rate = correct_predictions / decisions_with_outcomes

    confidences = [o.confidence_level for o in outcomes if o.confidence_level is not None]
    average_confidence = sum(confidences) / len(confidences) if confidences else 0.0

    calibration_errors = [o.calibration_error for o in outcomes if o.calibration_error is not None]
    calibration_score = 1.0 - (sum(calibration_errors) / len(calibration_errors)) if calibration_errors else 0.0

    # Calculate improvement trend
    if len(outcomes) >= 10:
        mid = len(outcomes) // 2
        first_half_accuracy = sum(1 for o in outcomes[:mid] if o.was_correct) / mid
        second_half_accuracy = sum(1 for o in outcomes[mid:] if o.was_correct) / (len(outcomes) - mid)

        if second_half_accuracy > first_half_accuracy + 0.1:
            improvement_trend = "improving"
        elif second_half_accuracy < first_half_accuracy - 0.1:
            improvement_trend = "declining"
        else:
            improvement_trend = "stable"
    else:
        improvement_trend = "insufficient_data"

    return JudgmentMetricsResponse(
        total_decisions=total_decisions,
        decisions_with_outcomes=decisions_with_outcomes,
        accuracy_rate=accuracy_rate,
        average_confidence=average_confidence,
        calibration_score=calibration_score,
        improvement_trend=improvement_trend,
    )


@router.post("/judgment/record-outcome/{decision_id}")
async def record_decision_outcome(
    decision_id: UUID,
    actual_outcome: str,
    actual_impact: str,
    outcome_notes: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record the actual outcome of a past decision.
    
    Args:
        decision_id: ID of the DecisionOutcome record
        actual_outcome: "success", "failure", or "neutral"
        actual_impact: "high", "medium", or "low"
        outcome_notes: What actually happened
    """
    user_id = UUID(current_user["id"])

    result = await db.execute(
        select(DecisionOutcome).where(
            and_(
                DecisionOutcome.id == decision_id,
                DecisionOutcome.user_id == user_id,
            )
        )
    )
    outcome = result.scalar_one_or_none()

    if not outcome:
        raise HTTPException(status_code=404, detail="Decision outcome not found")

    # Update outcome
    outcome.actual_outcome = actual_outcome
    outcome.actual_impact = actual_impact
    outcome.outcome_notes = outcome_notes
    outcome.outcome_recorded_date = datetime.utcnow()

    # Calculate judgment quality
    outcome.was_correct = outcome.predicted_outcome == actual_outcome
    
    # Calibration error: |confidence - accuracy|
    # If correct, accuracy = 1.0; if wrong, accuracy = 0.0
    accuracy = 1.0 if outcome.was_correct else 0.0
    outcome.calibration_error = abs(outcome.confidence_level - accuracy)

    await db.commit()

    return {
        "message": "Outcome recorded",
        "was_correct": outcome.was_correct,
        "calibration_error": outcome.calibration_error,
    }
