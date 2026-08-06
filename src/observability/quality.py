from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Tạo bộ data quality checks cho Data Observability.

    Checks:
    1. Row count >= 1.
    2. paper_id not null và unique.
    3. title not null và không rỗng.
    4. Độ dài summary >= 20 ký tự.
    5. Freshness dựa vào age_days <= freshness_threshold_days.
    6. text_for_embedding không được rỗng.
    """
    total_rows = len(df)
    
    if total_rows == 0:
        check_results = {
            "report_name": report_name,
            "timestamp": datetime.now(UTC).isoformat(),
            "total_rows": 0,
            "passed": False,
            "checks": {
                "row_count": {"passed": False, "message": "DataFrame is empty (0 records)"},
            },
            "summary_metrics": {
                "total_records": 0,
                "null_paper_ids": 0,
                "duplicate_paper_ids": 0,
                "empty_titles": 0,
                "empty_summaries": 0,
                "short_summaries": 0,
                "stale_records": 0,
                "missing_embeddings": 0,
            }
        }
        report_path = settings.paths.quality_dir / f"{report_name}.json"
        write_json(report_path, check_results)
        return check_results

    # 1. Row count check
    row_count_passed = total_rows >= 1

    # 2. paper_id check
    null_paper_ids = int(df["paper_id"].isnull().sum()) if "paper_id" in df else total_rows
    duplicate_paper_ids = int(df["paper_id"].duplicated().sum()) if "paper_id" in df else total_rows
    paper_id_passed = (null_paper_ids == 0) and (duplicate_paper_ids == 0)

    # 3. title check
    empty_titles = int((df["title"].isnull() | (df["title"].str.strip() == "")).sum()) if "title" in df else total_rows
    title_passed = (empty_titles == 0)

    # 4. summary length check
    empty_summaries = int((df["summary"].isnull() | (df["summary"].str.strip() == "")).sum()) if "summary" in df else total_rows
    short_summaries = int((df["summary"].str.len() < 20).sum()) if "summary" in df else total_rows
    summary_passed = (empty_summaries == 0) and (short_summaries == 0)

    # 5. freshness check (age_days)
    threshold = settings.freshness_threshold_days
    stale_records = int((df["age_days"] > threshold).sum()) if "age_days" in df else total_rows
    freshness_passed = (stale_records == 0)

    # 6. text_for_embedding check
    missing_embeddings = int((df["text_for_embedding"].isnull() | (df["text_for_embedding"].str.strip() == "")).sum()) if "text_for_embedding" in df else total_rows
    embedding_passed = (missing_embeddings == 0)

    all_passed = bool(
        row_count_passed
        and paper_id_passed
        and title_passed
        and summary_passed
        and freshness_passed
        and embedding_passed
    )

    check_results = {
        "report_name": report_name,
        "timestamp": datetime.now(UTC).isoformat(),
        "total_rows": total_rows,
        "passed": all_passed,
        "checks": {
            "row_count": {
                "passed": row_count_passed,
                "count": total_rows,
            },
            "paper_id_uniqueness": {
                "passed": paper_id_passed,
                "null_count": null_paper_ids,
                "duplicate_count": duplicate_paper_ids,
            },
            "title_completeness": {
                "passed": title_passed,
                "empty_count": empty_titles,
            },
            "summary_quality": {
                "passed": summary_passed,
                "empty_count": empty_summaries,
                "short_count": short_summaries,
            },
            "freshness": {
                "passed": freshness_passed,
                "stale_count": stale_records,
                "threshold_days": threshold,
            },
            "embedding_text": {
                "passed": embedding_passed,
                "missing_count": missing_embeddings,
            },
        },
        "summary_metrics": {
            "total_records": total_rows,
            "null_paper_ids": null_paper_ids,
            "duplicate_paper_ids": duplicate_paper_ids,
            "empty_titles": empty_titles,
            "empty_summaries": empty_summaries,
            "short_summaries": short_summaries,
            "stale_records": stale_records,
            "missing_embeddings": missing_embeddings,
        },
    }

    report_path = settings.paths.quality_dir / f"{report_name}.json"
    write_json(report_path, check_results)
    return check_results


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path: str | Path) -> dict[str, Any]:
    """Tổng hợp freshness report.

    Steps:
    1. Tìm latest và oldest published date.
    2. Đếm số dòng stale (age_days > freshness_threshold_days).
    3. Tạo payload: latest_published, oldest_published, stale_rows, total_rows, is_fresh.
    4. Ghi JSON report vào report_path.
    """
    total_rows = len(df)
    threshold = settings.freshness_threshold_days

    if total_rows == 0:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "latest_published": "N/A",
            "oldest_published": "N/A",
            "stale_rows": 0,
            "fresh_rows": 0,
            "total_rows": 0,
            "stale_percentage": 0.0,
            "average_age_days": 0.0,
            "freshness_threshold_days": threshold,
            "is_fresh": False,
        }
        write_json(Path(report_path), payload)
        return payload

    published_series = df["published"].dropna() if "published" in df else pd.Series(dtype=str)
    published_dates = published_series[published_series.str.strip() != ""]

    latest_pub = str(published_dates.max()) if not published_dates.empty else "N/A"
    oldest_pub = str(published_dates.min()) if not published_dates.empty else "N/A"

    stale_rows = int((df["age_days"] > threshold).sum()) if "age_days" in df else 0
    fresh_rows = total_rows - stale_rows
    stale_percentage = round((stale_rows / total_rows) * 100, 2)
    avg_age = round(float(df["age_days"].mean()), 1) if "age_days" in df else 0.0

    is_fresh = bool(stale_rows == 0)

    payload = {
        "timestamp": datetime.now(UTC).isoformat(),
        "latest_published": latest_pub,
        "oldest_published": oldest_pub,
        "stale_rows": stale_rows,
        "fresh_rows": fresh_rows,
        "total_rows": total_rows,
        "stale_percentage": stale_percentage,
        "average_age_days": avg_age,
        "freshness_threshold_days": threshold,
        "is_fresh": is_fresh,
    }

    write_json(Path(report_path), payload)
    return payload

