from datetime import datetime, timezone
import pytest
import pandas as pd

from ingestion.crossref import PaperRecord
from ingestion.cleaning import build_clean_dataframe


def test_build_clean_dataframe_basic():
    records = [
        PaperRecord(
            paper_id="10.1000/182",
            title="  Test  Title  with   spaces  ",
            summary="This is a test summary for paper 1.",
            authors=["Alice Smith ", " Bob Jones"],
            categories=["cs.AI", "cs.CL"],
            primary_category="cs.AI",
            published="2026-01-01",
            updated="2026-01-02",
            abs_url="https://doi.org/10.1000/182",
            pdf_url="",
            comment="Test comment"
        ),
        PaperRecord(
            paper_id="10.1000/182",  # Duplicate paper_id
            title="Duplicate Title",
            summary="Duplicate summary.",
            authors=["Alice Smith"],
            categories=["cs.AI"],
            primary_category="cs.AI",
            published="2026-01-01",
            updated="2026-01-02",
            abs_url="https://doi.org/10.1000/182",
            pdf_url="",
            comment=""
        ),
        PaperRecord(
            paper_id="10.1000/183",
            title="Empty Summary Paper",
            summary="   ",  # Empty summary -> should be filtered out
            authors=["Charlie Brown"],
            categories=["math.PR"],
            primary_category="math.PR",
            published="2026-02-01",
            updated="",
            abs_url="",
            pdf_url="",
            comment=""
        )
    ]

    run_date = datetime(2026, 3, 1, tzinfo=timezone.utc)
    df = build_clean_dataframe(records, run_date)

    assert isinstance(df, pd.DataFrame)
    # Duplicate paper_id 10.1000/182 kept first, empty summary paper 10.1000/183 filtered out
    assert len(df) == 1
    
    row = df.iloc[0]
    assert row["paper_id"] == "10.1000/182"
    assert row["title"] == "Test Title with spaces"
    assert row["authors_joined"] == "Alice Smith, Bob Jones"
    assert row["categories_joined"] == "cs.AI, cs.CL"
    assert row["summary_chars"] == len("This is a test summary for paper 1.")
    assert row["age_days"] == 59  # 2026-03-01 minus 2026-01-01
    
    # Check text_for_embedding
    assert "Title: Test Title with spaces" in row["text_for_embedding"]
    assert "Authors: Alice Smith, Bob Jones" in row["text_for_embedding"]
    assert "Summary: This is a test summary for paper 1." in row["text_for_embedding"]
