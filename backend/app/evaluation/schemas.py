"""
Phase 25 – AI Evaluation & Observability Schemas (Pydantic v2)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EvaluationMetricScores(BaseModel):
    wer: Optional[float] = Field(None, description="Word Error Rate")
    cer: Optional[float] = Field(None, description="Character Error Rate")
    der: Optional[float] = Field(None, description="Diarization Error Rate")
    faithfulness: Optional[float] = Field(None, description="RAG Faithfulness (0.0 to 1.0)")
    answer_relevance: Optional[float] = Field(None, description="RAG Answer Relevance (0.0 to 1.0)")
    context_precision: Optional[float] = Field(None, description="RAG Context Precision (0.0 to 1.0)")
    context_recall: Optional[float] = Field(None, description="RAG Context Recall (0.0 to 1.0)")


class EvaluationRunCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    pipeline_version: str = Field(..., min_length=1, max_length=100)
    dataset_name: str = Field(..., min_length=1, max_length=255)
    sample_count: int = Field(0, ge=0)
    metrics: EvaluationMetricScores
    status: str = Field("PASSED", description="PASSED | REGRESSED | FAILED")
    metrics_summary: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None


class EvaluationRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    name: str
    pipeline_version: str
    dataset_name: str
    sample_count: int
    wer: Optional[float] = None
    cer: Optional[float] = None
    der: Optional[float] = None
    faithfulness: Optional[float] = None
    answer_relevance: Optional[float] = None
    context_precision: Optional[float] = None
    context_recall: Optional[float] = None
    status: str
    metrics_summary_json: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    created_at: datetime


class ModelRegistryCreate(BaseModel):
    model_name: str = Field(..., min_length=1, max_length=100)
    model_version: str = Field(..., min_length=1, max_length=50)
    task_type: str = Field(..., description="ASR | DIARIZATION | EMBEDDING | LLM")
    provider_name: str = Field(..., min_length=1, max_length=100)
    artifact_uri: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    baseline_latency_ms: Optional[float] = None
    baseline_quality_score: Optional[float] = None
    status: str = "ACTIVE"


class ModelRegistryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    model_name: str
    model_version: str
    task_type: str
    provider_name: str
    artifact_uri: Optional[str] = None
    parameters_json: Dict[str, Any] = Field(default_factory=dict)
    baseline_latency_ms: Optional[float] = None
    baseline_quality_score: Optional[float] = None
    status: str
    created_at: datetime
    updated_at: datetime


class PromptRegistryCreate(BaseModel):
    template_name: str = Field(..., min_length=1, max_length=100)
    version: int = Field(1, ge=1)
    system_prompt: str
    user_prompt_template: str
    input_variables: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    status: str = "ACTIVE"


class PromptRegistryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    template_name: str
    version: int
    system_prompt: str
    user_prompt_template: str
    input_variables: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    status: str
    author_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime


class AITraceCreate(BaseModel):
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    stage: str = Field(..., description="QUERY_REWRITE | RETRIEVAL | GENERATION | EXTRACTION | ASR | DIARIZATION")
    model_name: str
    meeting_id: Optional[UUID] = None
    latency_ms: float
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    status: str = "SUCCESS"
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AITraceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    stage: str
    model_name: str
    meeting_id: Optional[UUID] = None
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    status: str
    error_message: Optional[str] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class CostAggregationResponse(BaseModel):
    tenant_id: UUID
    total_traces: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    total_estimated_cost_usd: float
    by_stage: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    by_model: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


class QualityOverviewResponse(BaseModel):
    tenant_id: UUID
    average_wer: Optional[float] = None
    average_der: Optional[float] = None
    average_faithfulness: Optional[float] = None
    average_answer_relevance: Optional[float] = None
    hallucination_rate: Optional[float] = None
    total_evaluations: int = 0
    regression_count: int = 0


class RegressionCheckResponse(BaseModel):
    is_regression: bool
    current_metrics: Dict[str, float]
    baseline_metrics: Dict[str, float]
    degraded_metrics: List[str]
    message: str
