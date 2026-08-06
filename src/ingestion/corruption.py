from __future__ import annotations

from pathlib import Path
import pandas as pd

from core.utils import compact_join, write_json


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: Path | str) -> pd.DataFrame:
    """Simulate nhiều dạng data corruption trên cleaned DataFrame.

    Steps:
    1. Drop một số latest records (bản ghi mới nhất theo published).
    2. Blank summary ở một số dòng.
    3. Inject noise vào text/summary.
    4. Cắt ngắn title (truncate title).
    5. Làm published date cũ đi (stale published date).
    6. Tạo thêm các dòng trùng lặp (duplicate rows).
    7. Rebuild lại `text_for_embedding`, `summary_chars`, `age_days`.
    8. Ghi corruption log vào output_log_path.
    """
    if df.empty:
        write_json(Path(output_log_path), {"initial_records_count": 0, "final_corrupted_records_count": 0, "actions_executed": []})
        return df.copy()

    corrupted_df = df.copy().reset_index(drop=True)
    logs = []

    total_initial = len(corrupted_df)

    # 1. Drop một số latest records (3 bài mới nhất)
    corrupted_df = corrupted_df.sort_values(by="published", ascending=False).reset_index(drop=True)
    dropped_ids = []
    if len(corrupted_df) > 5:
        dropped_ids = corrupted_df.iloc[:3]["paper_id"].tolist()
        corrupted_df = corrupted_df.iloc[3:].reset_index(drop=True)
        logs.append({
            "type": "drop_latest_records",
            "count": len(dropped_ids),
            "paper_ids": dropped_ids,
            "description": "Dropped 3 newest records to simulate missing recent data"
        })

    n = len(corrupted_df)

    # 2. Blank summary ở một số dòng
    blanked_ids = []
    if n > 0:
        indices_to_blank = [0, min(1, n - 1)]
        for idx in set(indices_to_blank):
            paper_id = corrupted_df.at[idx, "paper_id"]
            corrupted_df.at[idx, "summary"] = ""
            blanked_ids.append(paper_id)
        logs.append({
            "type": "blank_summary",
            "count": len(blanked_ids),
            "paper_ids": blanked_ids,
            "description": "Erased summary text to simulate missing metadata"
        })

    # 3. Inject noise vào summary
    noise_ids = []
    if n > 2:
        idx = 2
        paper_id = corrupted_df.at[idx, "paper_id"]
        original = str(corrupted_df.at[idx, "summary"])
        corrupted_df.at[idx, "summary"] = original + " [NOISE_CORRUPTED_TEXT_XYZ_12345_GARBAGE]"
        noise_ids.append(paper_id)
        logs.append({
            "type": "inject_noise",
            "count": len(noise_ids),
            "paper_ids": noise_ids,
            "description": "Injected synthetic noise tokens into summary"
        })

    # 4. Truncate title
    truncated_ids = []
    if n > 3:
        idx = 3
        paper_id = corrupted_df.at[idx, "paper_id"]
        corrupted_df.at[idx, "title"] = str(corrupted_df.at[idx, "title"])[:5]
        truncated_ids.append(paper_id)
        logs.append({
            "type": "truncate_title",
            "count": len(truncated_ids),
            "paper_ids": truncated_ids,
            "description": "Truncated title to 5 characters"
        })

    # 5. Stale published date (set lùi 365 ngày)
    stale_ids = []
    if n > 4:
        idx = 4
        paper_id = corrupted_df.at[idx, "paper_id"]
        corrupted_df.at[idx, "published"] = "2024-01-01"
        corrupted_df.at[idx, "age_days"] = int(corrupted_df.at[idx, "age_days"]) + 365
        stale_ids.append(paper_id)
        logs.append({
            "type": "stale_published_date",
            "count": len(stale_ids),
            "paper_ids": stale_ids,
            "description": "Shifted publication date to 2024-01-01 (stale data)"
        })

    # 6. Add duplicate rows (nhân bản 2 dòng đầu tiên)
    dup_ids = []
    if n > 1:
        duplicates = corrupted_df.iloc[:2].copy()
        dup_ids = duplicates["paper_id"].tolist()
        corrupted_df = pd.concat([corrupted_df, duplicates], ignore_index=True)
        logs.append({
            "type": "add_duplicate_rows",
            "count": len(duplicates),
            "paper_ids": dup_ids,
            "description": "Duplicated 2 rows to introduce duplicate paper_ids"
        })

    # 7. Rebuild summary_chars và text_for_embedding
    for i in range(len(corrupted_df)):
        title = str(corrupted_df.at[i, "title"])
        summary = str(corrupted_df.at[i, "summary"])
        authors = corrupted_df.at[i, "authors"]
        categories = corrupted_df.at[i, "categories"]

        authors_joined = compact_join(authors, ", ") if isinstance(authors, list) else str(authors)
        categories_joined = compact_join(categories, ", ") if isinstance(categories, list) else str(categories)

        corrupted_df.at[i, "summary_chars"] = len(summary)
        corrupted_df.at[i, "authors_joined"] = authors_joined
        corrupted_df.at[i, "categories_joined"] = categories_joined

        text_parts = [f"Title: {title}"]
        if authors_joined:
            text_parts.append(f"Authors: {authors_joined}")
        if categories_joined:
            text_parts.append(f"Categories: {categories_joined}")
        if summary:
            text_parts.append(f"Summary: {summary}")
        corrupted_df.at[i, "text_for_embedding"] = "\n".join(text_parts)

    # 8. Ghi corruption log vào output_log_path
    log_payload = {
        "initial_records_count": total_initial,
        "final_corrupted_records_count": len(corrupted_df),
        "actions_executed": logs
    }
    write_json(Path(output_log_path), log_payload)

    return corrupted_df

