# Phase 1 Baseline Execution Report

**Generated At**: `2026-08-06 03:37:50 UTC`  
**Role**: Person 5 - Evaluation & Observability Owner

> [!NOTE]
> This report documents the baseline performance and data observability status of the clean data pipeline prior to any synthetic corruption.

---

## 1. Data Ingestion & Cleaning Overview

| Parameter | Value |
| :--- | :--- |
| **Source API** | `Crossref REST API` |
| **Search Query** | `agentic retrieval augmented generation large language model` |
| **Source Filter** | `from-pub-date:2026-02-07,has-abstract:true` |
| **Raw Records Ingested** | `24` |
| **Clean Records Retained** | `24` |
| **Retained Ratio** | `100.0%` |

---

## 2. Evaluation & RAG Baseline Metrics

| Metric | Score | Target / Status |
| :--- | :--- | :--- |
| **Evaluation Test Samples** | `40` | Standard test suite |
| **Retrieval Hit Rate** | `1.0000` (`100.0%`) | Top-K Context Match |
| **Mean Token F1** | `0.5778` | String Similarity |
| **Judge Accuracy** | `0.5250` (`52.5%`) | Material Correctness |
| **Mean Judge Score** | `3.05 / 5.0` | Heuristic / LLM Score |

---

## 3. Data Quality Observability Checks

**Overall Quality Gate**: ✅ PASSED

| Check Name | Status | Details |
| :--- | :--- | :--- |
| **Row Count Gate** | `PASS` | Records: `24` |
| **paper_id Uniqueness** | `PASS` | Nulls: `0`, Dups: `0` |
| **Title Completeness** | `PASS` | Missing titles: `0` |
| **Summary Quality** | `PASS` | Short/Empty: `0` |
| **Embedding Field** | `PASS` | Missing embeddings: `0` |

---

## 4. Data Freshness Monitoring Report

**Freshness Gate**: ✅ FRESH

- **Latest Published Date**: `2026-08-01`
- **Oldest Published Date**: `2026-02-12`
- **Stale Records (> 180 days)**: `0` / `24` (`0.0%`)
- **Average Record Age**: `76.6 days`

---

## 5. Summary & Checkpoint Handoff

> [!TIP]
> All baseline metrics and quality gates have been recorded and saved in `data/results/` and `data/quality/`. The clean baseline collection `papers-baseline` is ready for comparison against Phase 3 data corruption experiments.
