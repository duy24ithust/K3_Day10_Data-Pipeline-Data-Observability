from __future__ import annotations

from datetime import UTC, datetime
import pandas as pd

from core.config import load_settings
from core.utils import read_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    print("\n💥 Starting Corruption, Repair & Comparison Flow...\n")

    # 1. Load settings and baseline data
    print("[1/9] Loading baseline settings and clean dataset...")
    settings = load_settings()
    baseline_metrics = read_json(settings.paths.baseline_metrics)
    baseline_df = pd.read_csv(settings.paths.clean_csv)
    print(f"      Loaded baseline clean dataset ({len(baseline_df)} records).")

    # 2. Corrupt clean dataset
    print("[2/9] Simulating synthetic data corruption...")
    corrupted_df = corrupt_clean_dataframe(baseline_df, settings.paths.corruption_log)
    print(f"      Created corrupted dataset ({len(corrupted_df)} records). Log saved to {settings.paths.corruption_log.name}.")

    # 3. Save corrupted clean artifacts
    print("[3/9] Saving corrupted clean CSV & JSON artifacts...")
    settings.paths.corrupted_clean_csv.parent.mkdir(parents=True, exist_ok=True)
    corrupted_df.to_csv(settings.paths.corrupted_clean_csv, index=False)
    corrupted_df.to_json(settings.paths.corrupted_clean_json, orient="records", indent=2)

    # 4. Build corrupted vector index
    print("[4/9] Building corrupted Chroma index and MiniLM embeddings...")
    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df,
        settings,
        embeddings_output_path=settings.paths.corrupted_embeddings_json,
    )
    print(f"      Indexed corrupted collection '{corrupted_index.collection_name}'.")

    # 5. Evaluate corrupted dataset on existing test set
    print("[5/9] Evaluating corrupted dataset performance...")
    corrupted_eval_bundle = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    print(f"      Corrupted Hit Rate: {corrupted_eval_bundle.summary['retrieval_hit_rate']:.2%}, Judge Score: {corrupted_eval_bundle.summary['mean_judge_score']:.2f}/5")

    # 6. Quality & Freshness checks on corrupted data
    print("[6/9] Running Data Quality checks & Freshness report on corrupted data...")
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, report_name="corrupted_quality")
    corrupted_freshness = build_freshness_report(
        corrupted_df,
        settings,
        settings.paths.quality_dir / "corrupted_freshness_report.json",
    )

    # 7. Repair data from raw snapshot
    print("[7/9] Repairing dataset from raw Crossref snapshot...")
    raw_records = load_raw_records(settings.paths.raw_records_json)
    repaired_df = build_clean_dataframe(raw_records, datetime.now(UTC))
    settings.paths.repaired_clean_csv.parent.mkdir(parents=True, exist_ok=True)
    repaired_df.to_csv(settings.paths.repaired_clean_csv, index=False)
    repaired_df.to_json(settings.paths.repaired_clean_json, orient="records", indent=2)
    print(f"      Repaired dataset restored ({len(repaired_df)} clean records).")

    # 8. Build repaired vector index and evaluate
    print("[8/9] Building repaired Chroma index and evaluating repaired dataset...")
    repaired_index = LocalEmbeddingIndex.build(
        repaired_df,
        settings,
        embeddings_output_path=settings.paths.repaired_embeddings_json,
    )
    repaired_eval_bundle = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    repaired_quality = run_data_quality_checks(repaired_df, settings, report_name="repaired_quality")
    repaired_freshness = build_freshness_report(
        repaired_df,
        settings,
        settings.paths.quality_dir / "repaired_freshness_report.json",
    )
    print(f"      Repaired Hit Rate: {repaired_eval_bundle.summary['retrieval_hit_rate']:.2%}, Judge Score: {repaired_eval_bundle.summary['mean_judge_score']:.2f}/5")

    # 9. Generate final comparison Markdown report
    print("[9/9] Generating final comparison markdown report...")
    generate_corruption_report(
        settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_eval_bundle.summary,
        repaired_metrics=repaired_eval_bundle.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )

    print(f"\n✅ Corruption, Repair & Comparison Flow completed successfully!")
    print(f"📄 Final comparison report written to: {settings.paths.comparison_report}\n")

