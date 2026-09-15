"""
Phase 25 – AI Evaluation & Observability Models (SQLAlchemy 2.0)

Entities:
  - EvaluationRun: Historical track of evaluation benchmark sessions, metrics, and quality thresholds.
  - ModelRegistry: Versioned AI model configurations, tasks (ASR, DIARIZATION, EMBEDDINGS, LLM), and status.
  - PromptRegistry: Versioned prompt templates, system instructions, and input variable specifications.
  - AITrace: Observability spans tracking latency, token usage, cost, and errors without leaking sensitive context.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TenantMixin


class EvaluationRun(TenantMixin, Base):
    """
    Session record representing an evaluation benchmark execution.
    Tracks ASR (WER/CER), Diarization (DER), and RAG quality metrics.
    """

    __tablename__ = "evaluation_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    pipeline_version: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    dataset_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    sample_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # ASR Metrics
    wer: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Word Error Rate
    cer: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Character Error Rate

    # Diarization Metrics
    der: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Diarization Error Rate

    # RAG Triad / RAGAS Metrics (0.0 to 1.0)
    faithfulness: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    answer_relevance: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    context_precision: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    context_recall: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Gating & regression status: PASSED | REGRESSED | FAILED
    status: Mapped[str] = mapped_column(String(50), default="PASSED", nullable=False, index=True)
    metrics_summary_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class ModelRegistry(Base):
    """
    Enterprise registry for AI models across ASR, Diarization, Embeddings, and LLMs.
    Guarantees asset versioning and deployment lifecycle management.
    """

    __tablename__ = "model_registry"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    task_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )  # ASR | DIARIZATION | EMBEDDING | LLM
    provider_name: Mapped[str] = mapped_column(String(100), nullable=False)  # faster-whisper, pyannote, sentence-transformers, ollama, openai
    artifact_uri: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    parameters_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Baseline performance metadata
    baseline_latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    baseline_quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Lifecycle: ACTIVE | DEPRECATED | STAGING
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE", nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_model_registry_name_version", "model_name", "model_version", unique=True),
    )


class PromptRegistry(TenantMixin, Base):
    """
    Versioned prompt templates with parameter schemas and author attribution.
    """

    __tablename__ = "prompt_registry"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    template_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    user_prompt_template: Mapped[str] = mapped_column(Text, nullable=False)
    input_variables: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ACTIVE | ARCHIVED | DRAFT
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE", nullable=False, index=True)
    author_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_prompt_registry_tenant_name_ver", "tenant_id", "template_name", "version", unique=True),
    )


class AITrace(TenantMixin, Base):
    """
    Observability record for individual AI inference/pipeline executions.
    Measures latency, token consumption, and cost without storing raw sensitive context.
    """

    __tablename__ = "ai_traces"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    span_id: Mapped[str] = mapped_column(String(64), nullable=False)
    parent_span_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Pipeline Stage: QUERY_REWRITE | RETRIEVAL | GENERATION | EXTRACTION | ASR | DIARIZATION
    stage: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    meeting_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("meetings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Performance & Tokens
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Financial Cost Estimation (USD)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Status: SUCCESS | ERROR
    status: Mapped[str] = mapped_column(String(30), default="SUCCESS", nullable=False, index=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
