"""
Phase 25 – AI Evaluation & Observability API Endpoints

Provides authenticated endpoints for:
  - Evaluation run history and benchmarking
  - Quality metrics overview and hallucination tracking
  - Token and financial cost aggregation per tenant
  - AI observability traces
  - Model and Prompt registries
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.evaluation.engine import EvaluationEngine
from app.evaluation.models import AITrace, EvaluationRun, ModelRegistry, PromptRegistry
from app.evaluation.schemas import (
    AITraceResponse,
    CostAggregationResponse,
    EvaluationRunResponse,
    ModelRegistryCreate,
    ModelRegistryResponse,
    PromptRegistryCreate,
    PromptRegistryResponse,
    QualityOverviewResponse,
)
from app.schemas.auth import CurrentUserContext
from app.security.dependencies import get_current_user

router = APIRouter()


@router.get(
    "/runs",
    response_model=List[EvaluationRunResponse],
    summary="List historical evaluation runs for current tenant",
)
def list_evaluation_runs(
    dataset_name: Optional[str] = Query(None, description="Filter by dataset name"),
    pipeline_version: Optional[str] = Query(None, description="Filter by pipeline version"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
) -> List[EvaluationRunResponse]:
    tenant_id = current_user.organization_id
    q = db.query(EvaluationRun).filter(EvaluationRun.tenant_id == tenant_id)

    if dataset_name:
        q = q.filter(EvaluationRun.dataset_name == dataset_name)
    if pipeline_version:
        q = q.filter(EvaluationRun.pipeline_version == pipeline_version)

    runs = q.order_by(EvaluationRun.created_at.desc()).limit(limit).all()
    return [EvaluationRunResponse.model_validate(r) for r in runs]


@router.get(
    "/quality",
    response_model=QualityOverviewResponse,
    summary="Get aggregated quality metrics and hallucination rates",
)
def get_quality_overview(
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
) -> QualityOverviewResponse:
    tenant_id = current_user.organization_id
    runs = db.query(EvaluationRun).filter(EvaluationRun.tenant_id == tenant_id).all()

    if not runs:
        return QualityOverviewResponse(tenant_id=tenant_id, total_evaluations=0, regression_count=0)

    wer_vals = [r.wer for r in runs if r.wer is not None]
    der_vals = [r.der for r in runs if r.der is not None]
    faith_vals = [r.faithfulness for r in runs if r.faithfulness is not None]
    rel_vals = [r.answer_relevance for r in runs if r.answer_relevance is not None]
    reg_count = sum(1 for r in runs if r.status == "REGRESSED")

    avg_wer = round(sum(wer_vals) / len(wer_vals), 4) if wer_vals else None
    avg_der = round(sum(der_vals) / len(der_vals), 4) if der_vals else None
    avg_faith = round(sum(faith_vals) / len(faith_vals), 4) if faith_vals else None
    avg_rel = round(sum(rel_vals) / len(rel_vals), 4) if rel_vals else None
    hallucination_rate = round(1.0 - avg_faith, 4) if avg_faith is not None else None

    return QualityOverviewResponse(
        tenant_id=tenant_id,
        average_wer=avg_wer,
        average_der=avg_der,
        average_faithfulness=avg_faith,
        average_answer_relevance=avg_rel,
        hallucination_rate=hallucination_rate,
        total_evaluations=len(runs),
        regression_count=reg_count,
    )


@router.get(
    "/costs",
    response_model=CostAggregationResponse,
    summary="Aggregate token consumption and financial cost for tenant",
)
def get_cost_aggregation(
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
) -> CostAggregationResponse:
    tenant_id = current_user.organization_id
    traces = db.query(AITrace).filter(AITrace.tenant_id == tenant_id).all()

    total_prompt = 0
    total_comp = 0
    total_tokens = 0
    total_cost = 0.0
    by_stage: Dict[str, Dict[str, Any]] = {}
    by_model: Dict[str, Dict[str, Any]] = {}

    for t in traces:
        total_prompt += t.prompt_tokens
        total_comp += t.completion_tokens
        total_tokens += t.total_tokens
        total_cost += t.estimated_cost_usd

        # Aggregate by stage
        st = t.stage
        if st not in by_stage:
            by_stage[st] = {"total_tokens": 0, "cost_usd": 0.0, "count": 0}
        by_stage[st]["total_tokens"] += t.total_tokens
        by_stage[st]["cost_usd"] = round(by_stage[st]["cost_usd"] + t.estimated_cost_usd, 6)
        by_stage[st]["count"] += 1

        # Aggregate by model
        md = t.model_name
        if md not in by_model:
            by_model[md] = {"total_tokens": 0, "cost_usd": 0.0, "count": 0}
        by_model[md]["total_tokens"] += t.total_tokens
        by_model[md]["cost_usd"] = round(by_model[md]["cost_usd"] + t.estimated_cost_usd, 6)
        by_model[md]["count"] += 1

    return CostAggregationResponse(
        tenant_id=tenant_id,
        total_traces=len(traces),
        total_prompt_tokens=total_prompt,
        total_completion_tokens=total_comp,
        total_tokens=total_tokens,
        total_estimated_cost_usd=round(total_cost, 6),
        by_stage=by_stage,
        by_model=by_model,
    )


@router.get(
    "/traces",
    response_model=List[AITraceResponse],
    summary="List individual AI observability traces",
)
def list_ai_traces(
    stage: Optional[str] = Query(None, description="Filter by pipeline stage"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
) -> List[AITraceResponse]:
    tenant_id = current_user.organization_id
    q = db.query(AITrace).filter(AITrace.tenant_id == tenant_id)

    if stage:
        q = q.filter(AITrace.stage == stage.upper())

    traces = q.order_by(AITrace.created_at.desc()).limit(limit).all()
    return [AITraceResponse.model_validate(t) for t in traces]


@router.get(
    "/models",
    response_model=List[ModelRegistryResponse],
    summary="List registered AI models",
)
def list_registered_models(
    task_type: Optional[str] = Query(None, description="ASR | DIARIZATION | EMBEDDING | LLM"),
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
) -> List[ModelRegistryResponse]:
    q = db.query(ModelRegistry)
    if task_type:
        q = q.filter(ModelRegistry.task_type == task_type.upper())
    models = q.order_by(ModelRegistry.model_name.asc(), ModelRegistry.model_version.desc()).all()
    return [ModelRegistryResponse.model_validate(m) for m in models]


@router.post(
    "/models",
    response_model=ModelRegistryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new model version",
)
def register_model(
    payload: ModelRegistryCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
) -> ModelRegistryResponse:
    existing = (
        db.query(ModelRegistry)
        .filter(
            ModelRegistry.model_name == payload.model_name,
            ModelRegistry.model_version == payload.model_version,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Model '{payload.model_name}' version '{payload.model_version}' already registered.",
        )

    model = ModelRegistry(
        model_name=payload.model_name,
        model_version=payload.model_version,
        task_type=payload.task_type.upper(),
        provider_name=payload.provider_name,
        artifact_uri=payload.artifact_uri,
        parameters_json=payload.parameters,
        baseline_latency_ms=payload.baseline_latency_ms,
        baseline_quality_score=payload.baseline_quality_score,
        status=payload.status.upper(),
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return ModelRegistryResponse.model_validate(model)


@router.get(
    "/prompts",
    response_model=List[PromptRegistryResponse],
    summary="List registered prompt templates for tenant",
)
def list_registered_prompts(
    template_name: Optional[str] = Query(None, description="Filter by template name"),
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
) -> List[PromptRegistryResponse]:
    tenant_id = current_user.organization_id
    q = db.query(PromptRegistry).filter(PromptRegistry.tenant_id == tenant_id)
    if template_name:
        q = q.filter(PromptRegistry.template_name == template_name)
    prompts = q.order_by(PromptRegistry.template_name.asc(), PromptRegistry.version.desc()).all()
    return [PromptRegistryResponse.model_validate(p) for p in prompts]


@router.post(
    "/prompts",
    response_model=PromptRegistryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new version of a prompt template",
)
def register_prompt_template(
    payload: PromptRegistryCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUserContext = Depends(get_current_user),
) -> PromptRegistryResponse:
    tenant_id = current_user.organization_id

    existing = (
        db.query(PromptRegistry)
        .filter(
            PromptRegistry.tenant_id == tenant_id,
            PromptRegistry.template_name == payload.template_name,
            PromptRegistry.version == payload.version,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Prompt '{payload.template_name}' v{payload.version} already exists.",
        )

    prompt = PromptRegistry(
        tenant_id=tenant_id,
        template_name=payload.template_name,
        version=payload.version,
        system_prompt=payload.system_prompt,
        user_prompt_template=payload.user_prompt_template,
        input_variables=payload.input_variables,
        description=payload.description,
        status=payload.status.upper(),
        author_id=current_user.user_id,
    )
    db.add(prompt)
    db.commit()
    db.refresh(prompt)
    return PromptRegistryResponse.model_validate(prompt)
