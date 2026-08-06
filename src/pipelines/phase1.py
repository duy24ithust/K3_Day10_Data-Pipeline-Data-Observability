from __future__ import annotations

from datetime import UTC, datetime

from core.config import load_settings
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    # 1. Load settings
    settings = load_settings()

    # 2. Load or fetch raw records
    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        raw_records = fetch_source_records(settings)
    else:
        raw_records = load_raw_records(settings.paths.raw_records_json)

    # 3. Clean data
    clean_df = build_clean_dataframe(raw_records, datetime.now(UTC))

    # 4. Save clean CSV and JSON artifacts
    settings.paths.clean_csv.parent.mkdir(parents=True, exist_ok=True)
    clean_df.to_csv(settings.paths.clean_csv, index=False)
    clean_df.to_json(settings.paths.clean_json, orient="records", indent=2)

    # 5. Build Chroma index
    index = LocalEmbeddingIndex.build(clean_df, settings)

    # 6. Build or load evaluation set
    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        build_test_set(clean_df, settings.paths.eval_testset)

    # 7. Run evaluation
    eval_bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )

    # 8. Run data quality checks & freshness report
    quality = run_data_quality_checks(clean_df, settings, report_name="baseline_quality")
    freshness = build_freshness_report(clean_df, settings, settings.paths.freshness_report)

    # 9. Generate baseline markdown report
    source_summary = {
        "source_api": settings.source_api,
        "source_query": settings.source_query,
        "source_filter": settings.source_filter,
        "raw_count": len(raw_records),
        "clean_count": len(clean_df),
    }
    generate_phase1_report(
        settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=eval_bundle.summary,
        quality=quality,
        freshness=freshness,
    )

