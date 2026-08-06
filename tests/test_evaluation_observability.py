from datetime import UTC, datetime
from pathlib import Path
import json
import pytest
import pandas as pd

from core.config import load_settings
from evaluation.testset import build_test_set
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report, generate_phase1_report


@pytest.fixture
def sample_clean_df():
    return pd.DataFrame([
        {
            "paper_id": "10.1000/1",
            "title": "Agentic RAG Architecture and Observability",
            "summary": "This paper presents a complete evaluation and data observability framework for RAG.",
            "authors": ["Alice Smith", "Bob Jones"],
            "categories": ["cs.AI", "cs.CL"],
            "published": "2026-02-01",
            "authors_joined": "Alice Smith, Bob Jones",
            "categories_joined": "cs.AI, cs.CL",
            "summary_chars": 82,
            "age_days": 10,
            "text_for_embedding": "Title: Agentic RAG Architecture\nSummary: Test",
        },
        {
            "paper_id": "10.1000/2",
            "title": "Data Quality Monitoring in AI Pipelines",
            "summary": "A comprehensive study on detection of data drift and corruption in ML pipelines.",
            "authors": ["Charlie Brown"],
            "categories": ["cs.DB"],
            "published": "2026-01-15",
            "authors_joined": "Charlie Brown",
            "categories_joined": "cs.DB",
            "summary_chars": 78,
            "age_days": 27,
            "text_for_embedding": "Title: Data Quality Monitoring\nSummary: Test 2",
        },
    ])


@pytest.fixture
def sample_corrupted_df():
    return pd.DataFrame([
        {
            "paper_id": "10.1000/1",  # Duplicate paper_id
            "title": "",  # Empty title
            "summary": "",  # Empty summary
            "authors": [],
            "categories": [],
            "published": "2020-01-01",
            "authors_joined": "",
            "categories_joined": "",
            "summary_chars": 0,
            "age_days": 200,  # Stale record > 180 days
            "text_for_embedding": "",
        },
        {
            "paper_id": "10.1000/1",  # Duplicate paper_id
            "title": "Corrupted Paper",
            "summary": "Short",  # < 20 chars
            "authors": ["Charlie"],
            "categories": ["cs.DB"],
            "published": "2020-01-01",
            "authors_joined": "Charlie",
            "categories_joined": "cs.DB",
            "summary_chars": 5,
            "age_days": 250,
            "text_for_embedding": "Corrupted",
        },
    ])


def test_build_test_set(sample_clean_df, tmp_path):
    output_json = tmp_path / "test_set.json"
    result = build_test_set(sample_clean_df, output_json)

    assert isinstance(result, list)
    assert len(result) > 0
    assert output_json.exists()

    # Verify JSON format
    data = json.loads(output_json.read_text(encoding="utf-8"))
    assert len(data) == len(result)

    first = data[0]
    assert "id" in first
    assert "question_type" in first
    assert "question" in first
    assert "ground_truth" in first
    assert "ground_truth_doc_ids" in first
    assert first["ground_truth_doc_ids"] == ["10.1000/1"]


def test_run_data_quality_checks_pass(sample_clean_df, tmp_path):
    settings = load_settings()
    # Override quality_dir to temp path
    settings_with_tmp = load_settings()
    object.__setattr__(settings_with_tmp.paths, "quality_dir", tmp_path)

    res = run_data_quality_checks(sample_clean_df, settings_with_tmp, "test_clean_quality")

    assert res["passed"] is True
    assert res["total_rows"] == 2
    assert res["summary_metrics"]["null_paper_ids"] == 0
    assert res["summary_metrics"]["duplicate_paper_ids"] == 0
    assert (tmp_path / "test_clean_quality.json").exists()


def test_run_data_quality_checks_fail(sample_corrupted_df, tmp_path):
    settings = load_settings()
    object.__setattr__(settings.paths, "quality_dir", tmp_path)

    res = run_data_quality_checks(sample_corrupted_df, settings, "test_corrupted_quality")

    assert res["passed"] is False
    assert res["summary_metrics"]["duplicate_paper_ids"] > 0
    assert res["summary_metrics"]["empty_titles"] > 0
    assert res["summary_metrics"]["empty_summaries"] > 0
    assert res["summary_metrics"]["stale_records"] > 0


def test_build_freshness_report(sample_clean_df, tmp_path):
    settings = load_settings()
    output_report = tmp_path / "freshness.json"

    res = build_freshness_report(sample_clean_df, settings, output_report)

    assert res["is_fresh"] is True
    assert res["stale_rows"] == 0
    assert res["total_rows"] == 2
    assert res["latest_published"] == "2026-02-01"
    assert res["oldest_published"] == "2026-01-15"
    assert output_report.exists()


def test_generate_phase1_report(tmp_path):
    report_path = tmp_path / "phase1_report.md"
    source_summary = {
        "source_api": "Crossref REST API",
        "source_query": "agentic retrieval",
        "source_filter": "has-abstract:true",
        "raw_count": 24,
        "clean_count": 20,
    }
    metrics = {
        "samples": 8,
        "retrieval_hit_rate": 1.0,
        "mean_token_f1": 0.85,
        "judge_accuracy": 1.0,
        "mean_judge_score": 4.5,
    }
    quality = {
        "passed": True,
        "summary_metrics": {"total_records": 20, "null_paper_ids": 0, "duplicate_paper_ids": 0, "empty_titles": 0, "short_summaries": 0, "missing_embeddings": 0},
    }
    freshness = {
        "is_fresh": True,
        "latest_published": "2026-02-01",
        "oldest_published": "2026-01-01",
        "stale_rows": 0,
        "total_rows": 20,
        "stale_percentage": 0.0,
        "average_age_days": 15.5,
        "freshness_threshold_days": 180,
    }

    generate_phase1_report(report_path, source_summary, metrics, quality, freshness)

    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "# Phase 1 Baseline Execution Report" in content
    assert "Retrieval Hit Rate" in content
    assert "1.0000" in content


def test_generate_corruption_report(tmp_path):
    report_path = tmp_path / "corruption_report.md"
    b_metrics = {"retrieval_hit_rate": 1.0, "mean_token_f1": 0.8, "judge_accuracy": 1.0, "mean_judge_score": 4.5, "samples": 10}
    c_metrics = {"retrieval_hit_rate": 0.5, "mean_token_f1": 0.3, "judge_accuracy": 0.4, "mean_judge_score": 2.0, "samples": 10}
    r_metrics = {"retrieval_hit_rate": 1.0, "mean_token_f1": 0.8, "judge_accuracy": 1.0, "mean_judge_score": 4.5, "samples": 10}

    c_quality = {"passed": False}
    r_quality = {"passed": True}

    c_freshness = {"is_fresh": False, "stale_rows": 5, "total_rows": 10}
    r_freshness = {"is_fresh": True, "stale_rows": 0, "total_rows": 10}

    generate_corruption_report(
        report_path,
        b_metrics,
        c_metrics,
        r_metrics,
        c_quality,
        r_quality,
        c_freshness,
        r_freshness,
    )

    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "# Data Observability: Degradation & Repair Report" in content
    assert "Performance Metrics Comparison Matrix" in content
    assert "Baseline" in content
    assert "Corrupted" in content
    assert "Repaired" in content
