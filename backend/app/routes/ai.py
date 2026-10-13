from fastapi import APIRouter, HTTPException, status

from ..schemas.schemas import (
    PricingRequest,
    PricingResponse,
    ReputationRequest,
    ReputationResponse,
)
from ..services.pricing_service import pricing_service
from ..services.reputation_service import ReputationService

router = APIRouter(prefix="/ai", tags=["AI services"])
reputation_service = ReputationService()


@router.post(
    "/pricing/estimate",
    response_model=PricingResponse,
    summary="Estimate a task price using the bundled 500-row synthetic dataset",
)
def estimate_task_price(payload: PricingRequest) -> PricingResponse:
    try:
        predicted_price = pricing_service.estimate(payload.requested_task.model_dump())
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return PricingResponse(
        predicted_price_points=predicted_price,
        training_examples=pricing_service.training_example_count,
        model="XGBoost Regressor",
        note="Model fitted on 500 synthetic examples for demonstration; prices are not verified market data.",
    )


@router.post(
    "/reputation/evaluate",
    response_model=ReputationResponse,
    summary="Evaluate worker reputation using K-Means and Arabic/English review sentiment",
)
def evaluate_worker_reputation(payload: ReputationRequest) -> ReputationResponse:
    try:
        results = reputation_service.evaluate(
            [worker.model_dump() for worker in payload.workers]
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return ReputationResponse(
        method="K-Means cohort segmentation + Arabic/English lexicon sentiment",
        workers=results,
        note=(
            "Scores are computed from the submitted cohort and reviews only; "
            "they are experimental indicators, not persisted reputation records."
        ),
    )
