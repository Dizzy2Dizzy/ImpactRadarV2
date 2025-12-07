"""
Ensemble ML Model API Router

Endpoints for model comparison, performance tracking, and ensemble scoring.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import desc, select

from database import get_db, close_db_session
from releaseradar.db.models import ModelPerformanceRecord, NeuralModelRegistry, Event
from releaseradar.ml.serving_ensemble import EnsembleScoringService
from api.utils.auth import get_current_user_with_plan
from api.utils.paywall import require_plan
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ensemble", tags=["ensemble"])


class ModelComparisonResponse(BaseModel):
    """Response model for model comparison"""
    xgboost: Dict[str, Any]
    neural: Dict[str, Any]
    ensemble_mode: str
    primary_model: str


class EnsemblePredictionResponse(BaseModel):
    """Response model for ensemble prediction"""
    event_id: int
    ml_adjusted_score: int
    predicted_return: float
    confidence: float
    xgboost_prediction: Optional[float]
    xgboost_weight: float
    neural_prediction: Optional[float]
    neural_weight: float
    primary_model: str
    model_source: str


class ModelPerformanceResponse(BaseModel):
    """Response model for model performance records"""
    id: int
    model_name: str
    model_type: str
    horizon: str
    directional_accuracy: float
    mae: Optional[float]
    rmse: Optional[float]
    sharpe_ratio: Optional[float]
    n_samples: int
    ensemble_weight: Optional[float]
    is_primary: bool
    recorded_date: date
    
    class Config:
        from_attributes = True


class NeuralModelResponse(BaseModel):
    """Response model for neural model registry"""
    id: int
    model_name: str
    version: str
    status: str
    training_samples: Optional[int]
    epochs_trained: Optional[int]
    directional_accuracy: Optional[float]
    deployed_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class RetrainRequest(BaseModel):
    """Request model for retraining neural model"""
    lookback_days: int = Field(365, ge=30, le=730, description="Days of history to use")
    min_samples: int = Field(500, ge=100, le=5000, description="Minimum training samples")


@router.get(
    "/compare",
    response_model=ModelComparisonResponse,
    summary="Compare model performances",
    description="Get comparison of XGBoost and Neural network model performances"
)
async def compare_models(
    horizon: str = Query("1d", description="Prediction horizon: 1d, 5d, 20d"),
    user_data: dict = Depends(get_current_user_with_plan),
    db: Session = Depends(get_db)
):
    """Compare ensemble model performances"""
    require_plan(
        user_data["plan"],
        "pro",
        "Model comparison",
        user_data.get("trial_ends_at")
    )
    
    try:
        service = EnsembleScoringService(db)
        comparison = service.get_model_comparison(horizon)
        
        return ModelComparisonResponse(**comparison)
        
    finally:
        close_db_session(db)


@router.get(
    "/predict/{event_id}",
    response_model=EnsemblePredictionResponse,
    summary="Get ensemble prediction for an event",
    description="Generate combined prediction from XGBoost and Neural network models"
)
async def get_ensemble_prediction(
    event_id: int,
    horizon: str = Query("1d", description="Prediction horizon"),
    user_data: dict = Depends(get_current_user_with_plan),
    db: Session = Depends(get_db)
):
    """Get ensemble prediction for a specific event"""
    require_plan(
        user_data["plan"],
        "pro",
        "Ensemble predictions",
        user_data.get("trial_ends_at")
    )
    
    try:
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event {event_id} not found"
            )
        
        service = EnsembleScoringService(db)
        prediction = service.predict_single(event_id, horizon)
        
        if not prediction:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Could not generate prediction for this event"
            )
        
        return EnsemblePredictionResponse(
            event_id=event_id,
            **prediction.to_dict()
        )
        
    finally:
        close_db_session(db)


@router.get(
    "/performance",
    response_model=List[ModelPerformanceResponse],
    summary="Get model performance history",
    description="Get historical performance records for ensemble models"
)
async def get_performance_history(
    model_type: Optional[str] = Query(None, description="Filter by model type: xgboost, neural"),
    horizon: str = Query("1d", description="Prediction horizon"),
    limit: int = Query(30, ge=1, le=90, description="Number of records"),
    user_data: dict = Depends(get_current_user_with_plan),
    db: Session = Depends(get_db)
):
    """Get model performance history"""
    require_plan(
        user_data["plan"],
        "pro",
        "Model performance tracking",
        user_data.get("trial_ends_at")
    )
    
    try:
        query = db.query(ModelPerformanceRecord).filter(
            ModelPerformanceRecord.horizon == horizon
        )
        
        if model_type:
            query = query.filter(ModelPerformanceRecord.model_type == model_type)
        
        records = query.order_by(desc(ModelPerformanceRecord.recorded_date)).limit(limit).all()
        
        return [ModelPerformanceResponse.from_orm(r) for r in records]
        
    finally:
        close_db_session(db)


@router.get(
    "/models",
    response_model=List[NeuralModelResponse],
    summary="List neural models",
    description="Get all registered neural network models"
)
async def list_neural_models(
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    user_data: dict = Depends(get_current_user_with_plan),
    db: Session = Depends(get_db)
):
    """List all neural models in registry"""
    require_plan(
        user_data["plan"],
        "pro",
        "Neural model registry",
        user_data.get("trial_ends_at")
    )
    
    try:
        query = db.query(NeuralModelRegistry)
        
        if status_filter:
            query = query.filter(NeuralModelRegistry.status == status_filter)
        
        models = query.order_by(desc(NeuralModelRegistry.created_at)).all()
        
        return [NeuralModelResponse.from_orm(m) for m in models]
        
    finally:
        close_db_session(db)


@router.post(
    "/retrain",
    response_model=Dict[str, Any],
    summary="Retrain neural model",
    description="Trigger retraining of the neural network model"
)
async def retrain_neural_model(
    request: RetrainRequest,
    user_data: dict = Depends(get_current_user_with_plan),
    db: Session = Depends(get_db)
):
    """Trigger neural model retraining (admin only)"""
    if not user_data.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    try:
        service = EnsembleScoringService(db)
        result = service.retrain_neural_model(
            lookback_days=request.lookback_days,
            min_samples=request.min_samples
        )
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=result["error"]
            )
        
        return result
        
    finally:
        close_db_session(db)


@router.get(
    "/weights",
    response_model=Dict[str, float],
    summary="Get current ensemble weights",
    description="Get the current weighting between XGBoost and Neural models"
)
async def get_ensemble_weights(
    horizon: str = Query("1d", description="Prediction horizon"),
    user_data: dict = Depends(get_current_user_with_plan),
    db: Session = Depends(get_db)
):
    """Get current ensemble model weights"""
    require_plan(
        user_data["plan"],
        "free",
        "Ensemble weights",
        user_data.get("trial_ends_at")
    )
    
    try:
        service = EnsembleScoringService(db)
        comparison = service.get_model_comparison(horizon)
        
        return {
            "xgboost": comparison["xgboost"]["weight"],
            "neural": comparison["neural"]["weight"],
            "primary_model": comparison["primary_model"]
        }
        
    finally:
        close_db_session(db)
