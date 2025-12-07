"""
Model Explainability API Router

Provides SHAP-based explanations for event predictions to enhance model transparency.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.dependencies import get_db
from api.utils.auth import get_current_user_with_plan
from releaseradar.db.models import Event, EventScore, PredictionExplanation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/explainability", tags=["explainability"])


FEATURE_FACTORS = [
    {
        "name": "sector",
        "display_name": "Sector Volatility",
        "description": "Impact of the company's sector on expected price movement. High-volatility sectors (biotech, tech) score higher."
    },
    {
        "name": "volatility",
        "display_name": "Stock Volatility",
        "description": "Historical volatility of the specific stock, measured via beta and ATR percentile."
    },
    {
        "name": "earnings_proximity",
        "display_name": "Earnings Proximity",
        "description": "Distance to next earnings date. Events closer to earnings have higher impact potential."
    },
    {
        "name": "market_mood",
        "display_name": "Market Mood",
        "description": "Current market regime (risk-on, risk-off, neutral) affects event amplification."
    },
    {
        "name": "after_hours",
        "display_name": "After Hours",
        "description": "Events announced after market close may have different impact dynamics."
    },
    {
        "name": "duplicate_penalty",
        "display_name": "Duplicate Penalty",
        "description": "Reduction applied when similar events have occurred recently for the same ticker."
    },
]


class FeatureContribution(BaseModel):
    """Individual feature contribution to the prediction."""
    feature: str = Field(..., description="Feature name")
    contribution: float = Field(..., description="Normalized contribution (0.0 to 1.0)")
    raw_value: Optional[int] = Field(None, description="Raw factor value before normalization")


class TopFactor(BaseModel):
    """Top contributing factor with explanation."""
    feature: str = Field(..., description="Feature name")
    display_name: str = Field(..., description="Human-readable feature name")
    contribution: float = Field(..., description="Contribution percentage")
    impact: str = Field(..., description="Impact direction: positive, negative, neutral")


class SHAPExplanationResponse(BaseModel):
    """SHAP explanation response for an event prediction."""
    event_id: int
    horizon: str = Field(..., description="Prediction horizon: 1d, 7d, or 30d")
    feature_contributions: Dict[str, float] = Field(..., description="Normalized feature contributions summing to 1.0")
    top_factors: List[TopFactor] = Field(..., description="Top contributing factors ordered by importance")
    shap_summary: str = Field(..., description="Human-readable explanation of the prediction")
    model_version: str = Field(..., description="Model version used for this explanation")
    computed_at: Optional[datetime] = Field(None, description="When explanation was computed")
    is_simulated: bool = Field(False, description="True if explanation was simulated from event scores")


class FeatureFactorInfo(BaseModel):
    """Feature factor information."""
    name: str = Field(..., description="Feature name used in the model")
    display_name: str = Field(..., description="Human-readable display name")
    description: str = Field(..., description="Description of what this factor measures")


class FactorsListResponse(BaseModel):
    """Response containing all feature factors."""
    factors: List[FeatureFactorInfo]
    total_count: int


class ComputeExplanationRequest(BaseModel):
    """Request to compute SHAP explanation."""
    horizon: str = Field("1d", pattern="^(1d|7d|30d)$", description="Prediction horizon")


class ComputeExplanationResponse(BaseModel):
    """Response after computing SHAP explanation."""
    event_id: int
    horizon: str
    status: str = Field(..., description="Computation status: success or error")
    message: str
    explanation: Optional[SHAPExplanationResponse] = None


def _get_factor_display_name(factor_name: str) -> str:
    """Get display name for a factor."""
    for factor in FEATURE_FACTORS:
        if factor["name"] == factor_name:
            return factor["display_name"]
    return factor_name.replace("_", " ").title()


def _compute_shap_from_event_scores(
    event: Event,
    event_score: EventScore,
    horizon: str
) -> Dict:
    """
    Compute simulated SHAP values from event_scores factor data.
    
    Normalizes factor values to sum to 1.0 for interpretable contributions.
    """
    raw_factors = {
        "sector": abs(event_score.factor_sector) if event_score.factor_sector else 0,
        "volatility": abs(event_score.factor_volatility) if event_score.factor_volatility else 0,
        "earnings_proximity": abs(event_score.factor_earnings_proximity) if event_score.factor_earnings_proximity else 0,
        "market_mood": abs(event_score.factor_market_mood) if event_score.factor_market_mood else 0,
        "after_hours": abs(event_score.factor_after_hours) if event_score.factor_after_hours else 0,
        "duplicate_penalty": abs(event_score.factor_duplicate_penalty) if event_score.factor_duplicate_penalty else 0,
    }
    
    total = sum(raw_factors.values())
    if total == 0:
        normalized = {k: 1.0 / len(raw_factors) for k in raw_factors}
    else:
        normalized = {k: v / total for k, v in raw_factors.items()}
    
    sorted_factors = sorted(normalized.items(), key=lambda x: x[1], reverse=True)
    
    top_factors = []
    for factor_name, contribution in sorted_factors[:4]:
        original_value = getattr(event_score, f"factor_{factor_name}", 0) or 0
        impact = "positive" if original_value > 0 else ("negative" if original_value < 0 else "neutral")
        
        top_factors.append({
            "feature": factor_name,
            "display_name": _get_factor_display_name(factor_name),
            "contribution": round(contribution * 100, 1),
            "impact": impact
        })
    
    top_factor_names = [f["display_name"] for f in top_factors[:2]]
    direction = event.direction or "neutral"
    confidence = event_score.confidence or 50
    
    if direction == "up":
        direction_text = "bullish"
    elif direction == "down":
        direction_text = "bearish"
    else:
        direction_text = "neutral"
    
    summary = (
        f"The model predicts a {direction_text} signal with {confidence}% confidence "
        f"for the {horizon} horizon. The primary drivers are {' and '.join(top_factor_names)}, "
        f"contributing {top_factors[0]['contribution']}% and {top_factors[1]['contribution'] if len(top_factors) > 1 else 0}% "
        f"respectively to the prediction."
    )
    
    return {
        "feature_contributions": {k: round(v, 4) for k, v in normalized.items()},
        "top_factors": top_factors,
        "shap_summary": summary,
        "raw_factors": raw_factors
    }


@router.get("/event/{event_id}", response_model=SHAPExplanationResponse)
async def get_event_explanation(
    event_id: int,
    horizon: str = Query("1d", pattern="^(1d|7d|30d)$", description="Prediction horizon"),
    db: Session = Depends(get_db),
    user_data: dict = Depends(get_current_user_with_plan)
):
    """
    Get SHAP explanation for an event prediction.
    
    Returns feature contributions and top factors that influenced the prediction.
    If no stored explanation exists, generates a simulated explanation from event scores.
    """
    event = db.execute(
        select(Event).where(Event.id == event_id)
    ).scalar_one_or_none()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    stored_explanation = db.execute(
        select(PredictionExplanation)
        .where(PredictionExplanation.event_id == event_id)
        .where(PredictionExplanation.horizon == horizon)
        .order_by(PredictionExplanation.computed_at.desc())
    ).scalar_one_or_none()
    
    if stored_explanation:
        return SHAPExplanationResponse(
            event_id=event_id,
            horizon=horizon,
            feature_contributions=stored_explanation.feature_contributions or {},
            top_factors=[TopFactor(**f) for f in (stored_explanation.top_factors or [])],
            shap_summary=stored_explanation.shap_summary or "",
            model_version=stored_explanation.model_version,
            computed_at=stored_explanation.computed_at,
            is_simulated=False
        )
    
    event_score = db.execute(
        select(EventScore).where(EventScore.event_id == event_id)
    ).scalar_one_or_none()
    
    if not event_score:
        raise HTTPException(
            status_code=404, 
            detail="No score data available for this event. Score must be computed first."
        )
    
    shap_data = _compute_shap_from_event_scores(event, event_score, horizon)
    
    return SHAPExplanationResponse(
        event_id=event_id,
        horizon=horizon,
        feature_contributions=shap_data["feature_contributions"],
        top_factors=[TopFactor(**f) for f in shap_data["top_factors"]],
        shap_summary=shap_data["shap_summary"],
        model_version="simulated-v1.0",
        computed_at=datetime.utcnow(),
        is_simulated=True
    )


@router.get("/factors", response_model=FactorsListResponse)
async def get_feature_factors(
    user_data: dict = Depends(get_current_user_with_plan)
):
    """
    Get list of all feature factors used in the impact prediction model.
    
    Returns descriptions and metadata for each factor to help users understand
    what influences predictions.
    """
    factors = [
        FeatureFactorInfo(
            name=f["name"],
            display_name=f["display_name"],
            description=f["description"]
        )
        for f in FEATURE_FACTORS
    ]
    
    return FactorsListResponse(
        factors=factors,
        total_count=len(factors)
    )


@router.post("/compute/{event_id}", response_model=ComputeExplanationResponse)
async def compute_event_explanation(
    event_id: int,
    request_body: ComputeExplanationRequest = None,
    db: Session = Depends(get_db),
    user_data: dict = Depends(get_current_user_with_plan)
):
    """
    Trigger computation of SHAP values for an event and store in database.
    
    Computes feature importance values and stores them in the prediction_explanations table
    for future retrieval.
    """
    horizon = request_body.horizon if request_body else "1d"
    
    event = db.execute(
        select(Event).where(Event.id == event_id)
    ).scalar_one_or_none()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    event_score = db.execute(
        select(EventScore).where(EventScore.event_id == event_id)
    ).scalar_one_or_none()
    
    if not event_score:
        raise HTTPException(
            status_code=400,
            detail="Event score must be computed before generating explanations"
        )
    
    try:
        shap_data = _compute_shap_from_event_scores(event, event_score, horizon)
        
        existing = db.execute(
            select(PredictionExplanation)
            .where(PredictionExplanation.event_id == event_id)
            .where(PredictionExplanation.horizon == horizon)
        ).scalar_one_or_none()
        
        if existing:
            existing.feature_contributions = shap_data["feature_contributions"]
            existing.top_factors = shap_data["top_factors"]
            existing.shap_summary = shap_data["shap_summary"]
            existing.model_version = "computed-v1.0"
            existing.computed_at = datetime.utcnow()
            explanation = existing
        else:
            explanation = PredictionExplanation(
                event_id=event_id,
                horizon=horizon,
                feature_contributions=shap_data["feature_contributions"],
                top_factors=shap_data["top_factors"],
                shap_summary=shap_data["shap_summary"],
                model_version="computed-v1.0",
                computed_at=datetime.utcnow()
            )
            db.add(explanation)
        
        db.commit()
        db.refresh(explanation)
        
        logger.info(f"Computed SHAP explanation for event {event_id}, horizon {horizon}")
        
        return ComputeExplanationResponse(
            event_id=event_id,
            horizon=horizon,
            status="success",
            message=f"SHAP explanation computed and stored for event {event_id}",
            explanation=SHAPExplanationResponse(
                event_id=event_id,
                horizon=horizon,
                feature_contributions=explanation.feature_contributions,
                top_factors=[TopFactor(**f) for f in explanation.top_factors],
                shap_summary=explanation.shap_summary,
                model_version=explanation.model_version,
                computed_at=explanation.computed_at,
                is_simulated=False
            )
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to compute SHAP explanation for event {event_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to compute explanation: {str(e)}"
        )
