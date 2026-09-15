"""
Phase 25 – AI Evaluation Engine & Regression Detection

Coordinates evaluation runs, scores outputs against ground truth,
and gates deployments by comparing against active baseline metrics.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session
import structlog

from app.evaluation.metrics.der import DEREvaluator
from app.evaluation.metrics.ragas import RAGASEvaluator
from app.evaluation.metrics.wer import WEREvaluator
from app.evaluation.models import AITrace, EvaluationRun, ModelRegistry
from app.evaluation.schemas import RegressionCheckResponse

logger = structlog.get_logger(__name__)


class EvaluationEngine:
    """
    Automated evaluation framework calculating ASR, Diarization, and RAG metrics.
    Detects regressions against active baselines to block degraded pipeline versions.
    """

    DEFAULT_TOLERANCES = {
        "max_wer_increase": 0.05,        # Max acceptable increase in WER (+5%)
        "max_der_increase": 0.05,        # Max acceptable increase in DER (+5%)
        "max_faithfulness_drop": 0.08,   # Max acceptable drop in Faithfulness (-8%)
        "max_relevance_drop": 0.08,      # Max acceptable drop in Answer Relevance (-8%)
    }

    def __init__(self, db: Session) -> None:
        self.db = db
        self.wer_evaluator = WEREvaluator()
        self.der_evaluator = DEREvaluator()
        self.ragas_evaluator = RAGASEvaluator()

    def evaluate_asr_dataset(
        self,
        samples: List[Dict[str, str]],
    ) -> Dict[str, float]:
        """
        samples: list of dicts with 'reference' and 'hypothesis'.
        Returns average WER and CER.
        """
        if not samples:
            return {"wer": 0.0, "cer": 0.0, "sample_count": 0}

        total_wer = 0.0
        total_cer = 0.0
        for s in samples:
            res_wer = self.wer_evaluator.evaluate_wer(s.get("reference", ""), s.get("hypothesis", ""))
            res_cer = self.wer_evaluator.evaluate_cer(s.get("reference", ""), s.get("hypothesis", ""))
            total_wer += res_wer["wer"]
            total_cer += res_cer["cer"]

        n = len(samples)
        return {
            "wer": round(total_wer / n, 4),
            "cer": round(total_cer / n, 4),
            "sample_count": n,
        }

    def evaluate_diarization_dataset(
        self,
        samples: List[Dict[str, List[Dict[str, Any]]]],
    ) -> Dict[str, float]:
        """
        samples: list of dicts with 'reference_segments' and 'hypothesis_segments'.
        Returns average DER.
        """
        if not samples:
            return {"der": 0.0, "sample_count": 0}

        total_der = 0.0
        for s in samples:
            der_res = self.der_evaluator.evaluate_der(
                reference_segments=s.get("reference_segments", []),
                hypothesis_segments=s.get("hypothesis_segments", []),
            )
            total_der += der_res["der"]

        n = len(samples)
        return {
            "der": round(total_der / n, 4),
            "sample_count": n,
        }

    def evaluate_rag_dataset(
        self,
        samples: List[Dict[str, Any]],
    ) -> Dict[str, float]:
        """
        samples: list of dicts with 'query', 'answer', 'context_chunks', and optional 'ground_truth'.
        Returns average Faithfulness, Answer Relevance, Context Precision, and Context Recall.
        """
        if not samples:
            return {
                "faithfulness": 1.0,
                "answer_relevance": 1.0,
                "context_precision": 1.0,
                "context_recall": 1.0,
                "sample_count": 0,
            }

        f_sum = 0.0
        rel_sum = 0.0
        p_sum = 0.0
        r_sum = 0.0

        for s in samples:
            metrics = self.ragas_evaluator.evaluate_all(
                query=s.get("query", ""),
                answer=s.get("answer", ""),
                retrieved_chunks=s.get("context_chunks", []),
                ground_truth=s.get("ground_truth"),
            )
            f_sum += metrics["faithfulness"]
            rel_sum += metrics["answer_relevance"]
            p_sum += metrics["context_precision"]
            r_sum += metrics["context_recall"]

        n = len(samples)
        return {
            "faithfulness": round(f_sum / n, 4),
            "answer_relevance": round(rel_sum / n, 4),
            "context_precision": round(p_sum / n, 4),
            "context_recall": round(r_sum / n, 4),
            "sample_count": n,
        }

    def check_regression(
        self,
        tenant_id: UUID,
        dataset_name: str,
        current_metrics: Dict[str, float],
    ) -> RegressionCheckResponse:
        """
        Compares current evaluation metrics against the latest active baseline for the dataset.
        Returns whether a quality regression occurred.
        """
        # Find latest historical run for same dataset
        baseline_run = (
            self.db.query(EvaluationRun)
            .filter(
                EvaluationRun.tenant_id == tenant_id,
                EvaluationRun.dataset_name == dataset_name,
                EvaluationRun.status == "PASSED",
            )
            .order_by(EvaluationRun.created_at.desc())
            .first()
        )

        if not baseline_run:
            return RegressionCheckResponse(
                is_regression=False,
                current_metrics=current_metrics,
                baseline_metrics={},
                degraded_metrics=[],
                message="No prior baseline found; establishing new baseline.",
            )

        baseline_metrics = {
            "wer": baseline_run.wer,
            "der": baseline_run.der,
            "faithfulness": baseline_run.faithfulness,
            "answer_relevance": baseline_run.answer_relevance,
        }

        degraded = []

        # Check WER (lower is better)
        if current_metrics.get("wer") is not None and baseline_metrics.get("wer") is not None:
            if current_metrics["wer"] > (baseline_metrics["wer"] + self.DEFAULT_TOLERANCES["max_wer_increase"]):
                degraded.append("wer")

        # Check DER (lower is better)
        if current_metrics.get("der") is not None and baseline_metrics.get("der") is not None:
            if current_metrics["der"] > (baseline_metrics["der"] + self.DEFAULT_TOLERANCES["max_der_increase"]):
                degraded.append("der")

        # Check Faithfulness (higher is better)
        if current_metrics.get("faithfulness") is not None and baseline_metrics.get("faithfulness") is not None:
            if current_metrics["faithfulness"] < (baseline_metrics["faithfulness"] - self.DEFAULT_TOLERANCES["max_faithfulness_drop"]):
                degraded.append("faithfulness")

        # Check Answer Relevance (higher is better)
        if current_metrics.get("answer_relevance") is not None and baseline_metrics.get("answer_relevance") is not None:
            if current_metrics["answer_relevance"] < (baseline_metrics["answer_relevance"] - self.DEFAULT_TOLERANCES["max_relevance_drop"]):
                degraded.append("answer_relevance")

        is_reg = len(degraded) > 0
        msg = f"Regression detected in: {', '.join(degraded)}" if is_reg else "All quality thresholds met."

        return RegressionCheckResponse(
            is_regression=is_reg,
            current_metrics={k: v for k, v in current_metrics.items() if v is not None},
            baseline_metrics={k: v for k, v in baseline_metrics.items() if v is not None},
            degraded_metrics=degraded,
            message=msg,
        )

    def run_and_record_evaluation(
        self,
        tenant_id: UUID,
        name: str,
        pipeline_version: str,
        dataset_name: str,
        asr_samples: Optional[List[Dict[str, str]]] = None,
        diarization_samples: Optional[List[Dict[str, Any]]] = None,
        rag_samples: Optional[List[Dict[str, Any]]] = None,
    ) -> EvaluationRun:
        """
        Executes full benchmark evaluation across domains, computes regression gating,
        and saves an EvaluationRun record in PostgreSQL.
        """
        metrics: Dict[str, float] = {}
        sample_count = 0

        if asr_samples:
            asr_res = self.evaluate_asr_dataset(asr_samples)
            metrics["wer"] = asr_res["wer"]
            metrics["cer"] = asr_res["cer"]
            sample_count += len(asr_samples)

        if diarization_samples:
            der_res = self.evaluate_diarization_dataset(diarization_samples)
            metrics["der"] = der_res["der"]
            sample_count += len(diarization_samples)

        if rag_samples:
            rag_res = self.evaluate_rag_dataset(rag_samples)
            metrics["faithfulness"] = rag_res["faithfulness"]
            metrics["answer_relevance"] = rag_res["answer_relevance"]
            metrics["context_precision"] = rag_res["context_precision"]
            metrics["context_recall"] = rag_res["context_recall"]
            sample_count += len(rag_samples)

        reg_check = self.check_regression(
            tenant_id=tenant_id,
            dataset_name=dataset_name,
            current_metrics=metrics,
        )

        status = "REGRESSED" if reg_check.is_regression else "PASSED"

        eval_run = EvaluationRun(
            tenant_id=tenant_id,
            name=name,
            pipeline_version=pipeline_version,
            dataset_name=dataset_name,
            sample_count=sample_count,
            wer=metrics.get("wer"),
            cer=metrics.get("cer"),
            der=metrics.get("der"),
            faithfulness=metrics.get("faithfulness"),
            answer_relevance=metrics.get("answer_relevance"),
            context_precision=metrics.get("context_precision"),
            context_recall=metrics.get("context_recall"),
            status=status,
            metrics_summary_json={
                "metrics": metrics,
                "regression_check": {
                    "is_regression": reg_check.is_regression,
                    "degraded_metrics": reg_check.degraded_metrics,
                    "message": reg_check.message,
                },
            },
            error_message=reg_check.message if reg_check.is_regression else None,
        )

        self.db.add(eval_run)
        self.db.commit()
        self.db.refresh(eval_run)
        return eval_run

    def record_trace(
        self,
        tenant_id: UUID,
        trace_id: str,
        span_id: str,
        stage: str,
        model_name: str,
        latency_ms: float,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        estimated_cost_usd: float = 0.0,
        meeting_id: Optional[UUID] = None,
        status: str = "SUCCESS",
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AITrace:
        """Logs an AI execution trace for latency, token, and cost observability."""
        trace = AITrace(
            tenant_id=tenant_id,
            trace_id=trace_id,
            span_id=span_id,
            stage=stage,
            model_name=model_name,
            meeting_id=meeting_id,
            latency_ms=latency_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            estimated_cost_usd=estimated_cost_usd,
            status=status,
            error_message=error_message,
            metadata_json=metadata or {},
        )
        self.db.add(trace)
        self.db.commit()
        self.db.refresh(trace)
        return trace
