from datetime import datetime, timezone
import pytest
import pandas as pd

from ingestion.crossref import PaperRecord
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe


def test_corrupt_clean_dataframe(tmp_path):
    records = [
        PaperRecord(
            paper_id=f"10.1000/{i}",
            title=f"Paper Title {i}",
            summary=f"This is summary content for paper number {i}.",
            authors=["Author A"],
            categories=["cs.AI"],
            primary_category="cs.AI",
            published=f"2026-02-0{i+1}",
            updated="",
            abs_url="",
            pdf_url="",
            comment=""
        ) for i in range(10)
    ]

    run_date = datetime(2026, 3, 1, tzinfo=timezone.utc)
    clean_df = build_clean_dataframe(records, run_date)

    log_path = tmp_path / "corruption_log.json"
    corrupted_df = corrupt_clean_dataframe(clean_df, log_path)

    assert isinstance(corrupted_df, pd.DataFrame)
    assert log_path.exists()
    assert len(corrupted_df) > 0
    # Duplicates were appended
    assert corrupted_df["paper_id"].duplicated().any()
