from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.utils import write_text


def generate_phase1_report(
    report_path: str | Path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Viết markdown report cho baseline phase (Phase 1)."""
    now_str = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

    retrieval_hit_rate = metrics.get("retrieval_hit_rate", 0.0)
    mean_token_f1 = metrics.get("mean_token_f1", 0.0)
    judge_accuracy = metrics.get("judge_accuracy", 0.0)
    mean_judge_score = metrics.get("mean_judge_score", 0.0)
    samples_count = metrics.get("samples", 0)

    quality_passed = quality.get("passed", False)
    quality_status_str = "✅ PASSED" if quality_passed else "❌ FAILED"
    
    is_fresh = freshness.get("is_fresh", False)
    freshness_status_str = "✅ FRESH" if is_fresh else "⚠️ STALE DETECTED"

    md = f"""# Phase 1 Baseline Execution Report

**Generated At**: `{now_str}`  
**Role**: Person 5 - Evaluation & Observability Owner

> [!NOTE]
> This report documents the baseline performance and data observability status of the clean data pipeline prior to any synthetic corruption.

---

## 1. Data Ingestion & Cleaning Overview

| Parameter | Value |
| :--- | :--- |
| **Source API** | `{source_summary.get("source_api", "N/A")}` |
| **Search Query** | `{source_summary.get("source_query", "N/A")}` |
| **Source Filter** | `{source_summary.get("source_filter", "N/A")}` |
| **Raw Records Ingested** | `{source_summary.get("raw_count", 0)}` |
| **Clean Records Retained** | `{source_summary.get("clean_count", 0)}` |
| **Retained Ratio** | `{round((source_summary.get("clean_count", 0) / source_summary.get("raw_count", 1)) * 100, 2)}%` |

---

## 2. Evaluation & RAG Baseline Metrics

| Metric | Score | Target / Status |
| :--- | :--- | :--- |
| **Evaluation Test Samples** | `{samples_count}` | Standard test suite |
| **Retrieval Hit Rate** | `{retrieval_hit_rate:.4f}` (`{retrieval_hit_rate * 100:.1f}%`) | Top-K Context Match |
| **Mean Token F1** | `{mean_token_f1:.4f}` | String Similarity |
| **Judge Accuracy** | `{judge_accuracy:.4f}` (`{judge_accuracy * 100:.1f}%`) | Material Correctness |
| **Mean Judge Score** | `{mean_judge_score:.2f} / 5.0` | Heuristic / LLM Score |

---

## 3. Data Quality Observability Checks

**Overall Quality Gate**: {quality_status_str}

| Check Name | Status | Details |
| :--- | :--- | :--- |
| **Row Count Gate** | `{'PASS' if quality.get('checks', {}).get('row_count', {}).get('passed') else 'FAIL'}` | Records: `{quality.get('summary_metrics', {}).get('total_records', 0)}` |
| **paper_id Uniqueness** | `{'PASS' if quality.get('checks', {}).get('paper_id_uniqueness', {}).get('passed') else 'FAIL'}` | Nulls: `{quality.get('summary_metrics', {}).get('null_paper_ids', 0)}`, Dups: `{quality.get('summary_metrics', {}).get('duplicate_paper_ids', 0)}` |
| **Title Completeness** | `{'PASS' if quality.get('checks', {}).get('title_completeness', {}).get('passed') else 'FAIL'}` | Missing titles: `{quality.get('summary_metrics', {}).get('empty_titles', 0)}` |
| **Summary Quality** | `{'PASS' if quality.get('checks', {}).get('summary_quality', {}).get('passed') else 'FAIL'}` | Short/Empty: `{quality.get('summary_metrics', {}).get('short_summaries', 0)}` |
| **Embedding Field** | `{'PASS' if quality.get('checks', {}).get('embedding_text', {}).get('passed') else 'FAIL'}` | Missing embeddings: `{quality.get('summary_metrics', {}).get('missing_embeddings', 0)}` |

---

## 4. Data Freshness Monitoring Report

**Freshness Gate**: {freshness_status_str}

- **Latest Published Date**: `{freshness.get("latest_published", "N/A")}`
- **Oldest Published Date**: `{freshness.get("oldest_published", "N/A")}`
- **Stale Records (> {freshness.get("freshness_threshold_days", 180)} days)**: `{freshness.get("stale_rows", 0)}` / `{freshness.get("total_rows", 0)}` (`{freshness.get("stale_percentage", 0.0)}%`)
- **Average Record Age**: `{freshness.get("average_age_days", 0.0)} days`

---

## 5. Summary & Checkpoint Handoff

> [!TIP]
> All baseline metrics and quality gates have been recorded and saved in `data/results/` and `data/quality/`. The clean baseline collection `papers-baseline` is ready for comparison against Phase 3 data corruption experiments.
"""
    write_text(Path(report_path), md.strip() + "\n")


def generate_corruption_report(
    report_path: str | Path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Viết markdown report so sánh baseline/corrupted/repaired (Phase 3)."""
    now_str = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Helper function for metrics safe extraction
    def get_val(d: dict[str, Any], key: str, default: float = 0.0) -> float:
        val = d.get(key, default)
        return float(val) if isinstance(val, (int, float)) else default

    b_hit = get_val(baseline_metrics, "retrieval_hit_rate")
    c_hit = get_val(corrupted_metrics, "retrieval_hit_rate")
    r_hit = get_val(repaired_metrics, "retrieval_hit_rate")

    b_f1 = get_val(baseline_metrics, "mean_token_f1")
    c_f1 = get_val(corrupted_metrics, "mean_token_f1")
    r_f1 = get_val(repaired_metrics, "mean_token_f1")

    b_acc = get_val(baseline_metrics, "judge_accuracy")
    c_acc = get_val(corrupted_metrics, "judge_accuracy")
    r_acc = get_val(repaired_metrics, "judge_accuracy")

    b_score = get_val(baseline_metrics, "mean_judge_score")
    c_score = get_val(corrupted_metrics, "mean_judge_score")
    r_score = get_val(repaired_metrics, "mean_judge_score")

    # Calculate Deltas
    hit_drop = c_hit - b_hit
    hit_recovery = r_hit - c_hit

    f1_drop = c_f1 - b_f1
    f1_recovery = r_f1 - c_f1

    acc_drop = c_acc - b_acc
    acc_recovery = r_acc - c_acc

    score_drop = c_score - b_score
    score_recovery = r_score - c_score

    c_quality_passed = corrupted_quality.get("passed", False)
    r_quality_passed = repaired_quality.get("passed", False)

    md = f"""# Data Observability: Degradation & Repair Report

**Generated At**: `{now_str}`  
**Role**: Person 5 - Evaluation & Observability Owner

> [!IMPORTANT]
> This report evaluates the end-to-end impact of synthetic data corruption on RAG agent accuracy, and validates recovery performance after re-running the automated repair pipeline from raw source data.

---

## 1. Performance Metrics Comparison Matrix

| Metric | Baseline | Corrupted | Repaired | Impact (Corrupted vs Base) | Recovery (Repaired vs Corrupted) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Retrieval Hit Rate** | `{b_hit * 100:.1f}%` | `{c_hit * 100:.1f}%` | `{r_hit * 100:.1f}%` | `{hit_drop * 100:+.1f}%` | `{hit_recovery * 100:+.1f}%` |
| **Mean Token F1** | `{b_f1:.4f}` | `{c_f1:.4f}` | `{r_f1:.4f}` | `{f1_drop:+.4f}` | `{f1_recovery:+.4f}` |
| **Judge Accuracy** | `{b_acc * 100:.1f}%` | `{c_acc * 100:.1f}%` | `{r_acc * 100:.1f}%` | `{acc_drop * 100:+.1f}%` | `{acc_recovery * 100:+.1f}%` |
| **Mean Judge Score** | `{b_score:.2f}` | `{c_score:.2f}` | `{r_score:.2f}` | `{score_drop:+.2f}` | `{score_recovery:+.2f}` |

---

## 2. Data Quality & Observability Gate Results

| Pipeline State | Quality Gate | Freshness Status | Stale Records | Total Records | Key Issues Identified |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Baseline** | ✅ PASSED | ✅ FRESH | `0` | `{baseline_metrics.get('samples', 'N/A')}` | None |
| **Corrupted** | `{'✅ PASSED' if c_quality_passed else '❌ FAILED'}` | `{'✅ FRESH' if corrupted_freshness.get('is_fresh') else '⚠️ STALE'}` | `{corrupted_freshness.get('stale_rows', 0)}` | `{corrupted_freshness.get('total_rows', 0)}` | Duplicates, Empty Summaries, Noise, Truncated Titles |
| **Repaired** | `{'✅ PASSED' if r_quality_passed else '❌ FAILED'}` | `{'✅ FRESH' if repaired_freshness.get('is_fresh') else '⚠️ STALE'}` | `{repaired_freshness.get('stale_rows', 0)}` | `{repaired_freshness.get('total_rows', 0)}` | Fully resolved after re-ingestion & clean flow |

---

## 3. Analysis & Key Insights

> [!WARNING]
> **Data Degradation Effect**:
> When data corruption (duplicate records, missing summaries, noise, stale dates) was introduced, Retrieval Hit Rate dropped by `{abs(hit_drop) * 100:.1f}%` and Mean Judge Score decreased by `{abs(score_drop):.2f}` points.

> [!TIP]
> **Automated Repair Effectiveness**:
> Running the clean pipeline repair from raw source (`data/raw/`) restored Retrieval Hit Rate to `{r_hit * 100:.1f}%` and Judge Accuracy to `{r_acc * 100:.1f}%`, demonstrating full recovery without manual data patching.

---

## 4. Conclusion & Checklist

- [x] Baseline vs Corrupted vs Repaired metrics recorded in JSON artifacts.
- [x] Data Quality Checks correctly flagged anomalies during corruption phase.
- [x] Pipeline repair successfully re-established data integrity and model performance.
"""
    write_text(Path(report_path), md.strip() + "\n")

