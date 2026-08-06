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
    print("\n🚀 Starting Baseline Phase 1 Pipeline...\n")

    # 1. Load settings
    print("[1/8] Loading project settings and configurations...")
    settings = load_settings()

    # 2. Load or fetch raw records
    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        print("[2/8] Fetching raw records from Crossref API...")
        raw_records = fetch_source_records(settings)
    else:
        print("[2/8] Loading raw records from local JSON snapshot...")
        raw_records = load_raw_records(settings.paths.raw_records_json)
    print(f"      Loaded {len(raw_records)} raw paper records.")

    # 3. Clean data
    print("[3/8] Building clean dataset...")
    clean_df = build_clean_dataframe(raw_records, datetime.now(UTC))
    print(f"      Cleaned dataset contains {len(clean_df)} valid records.")

    # 4. Save clean CSV and JSON artifacts
    print("[4/8] Saving clean CSV and JSON artifacts...")
    settings.paths.clean_csv.parent.mkdir(parents=True, exist_ok=True)
    clean_df.to_csv(settings.paths.clean_csv, index=False)
    clean_df.to_json(settings.paths.clean_json, orient="records", indent=2)

    # 5. Build Chroma index
    print("[5/8] Building Chroma vector index and MiniLM embeddings...")
    index = LocalEmbeddingIndex.build(clean_df, settings)
    print(f"      Indexed {len(index.documents)} documents in collection '{index.collection_name}'.")

    # 6. Build or load evaluation set
    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        print("[6/8] Building evaluation test set...")
        build_test_set(clean_df, settings.paths.eval_testset)
    else:
        print("[6/8] Using existing evaluation test set...")

    # 7. Run evaluation
    print("[7/8] Running evaluation (QA agent & LLM judge scoring)...")
    eval_bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    print(f"      Evaluation completed. Hit Rate: {eval_bundle.summary['retrieval_hit_rate']:.2%}, Judge Score: {eval_bundle.summary['mean_judge_score']:.2f}/5")

    # 8. Run data quality checks & freshness report
    print("[8/8] Running Data Quality checks & generating Freshness report...")
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

    print(f"\n✅ Phase 1 Baseline Pipeline completed successfully!")
    print(f"📄 Report written to: {settings.paths.baseline_report}\n")

