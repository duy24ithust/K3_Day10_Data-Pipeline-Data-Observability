from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import write_json


def build_test_set(df: pd.DataFrame, output_path: str | Path) -> list[dict[str, Any]]:
    """Tạo bộ evaluation set từ cleaned dataframe.

    Steps:
    1. Kiểm tra số lượng document.
    2. Chọn các paper đại diện.
    3. Tạo nhiều loại câu hỏi: summary, authors, date, categories.
    4. Mỗi row gồm: id, question_type, question, ground_truth, ground_truth_doc_ids.
    5. Ghi file JSON vào output_path và trả về list dict.
    """
    if df.empty:
        write_json(Path(output_path), [])
        return []

    output_path = Path(output_path)
    sample_df = df.head(10) if len(df) >= 10 else df

    test_samples: list[dict[str, Any]] = []
    sample_counter = 1

    for idx, row in sample_df.iterrows():
        paper_id = str(row["paper_id"])
        title = str(row["title"])
        summary = str(row.get("summary", ""))
        authors = str(row.get("authors_joined", ""))
        published = str(row.get("published", ""))
        categories = str(row.get("categories_joined", ""))

        # 1. Question about summary / main topic
        if summary:
            test_samples.append({
                "id": f"q_{sample_counter}_summary",
                "question_type": "summary",
                "question": f"What is the main topic or abstract of the paper '{title}'?",
                "ground_truth": summary,
                "ground_truth_doc_ids": [paper_id],
            })
            sample_counter += 1

        # 2. Question about authors
        if authors:
            test_samples.append({
                "id": f"q_{sample_counter}_authors",
                "question_type": "authors",
                "question": f"Who are the authors of the paper titled '{title}'?",
                "ground_truth": authors,
                "ground_truth_doc_ids": [paper_id],
            })
            sample_counter += 1

        # 3. Question about published date
        if published:
            test_samples.append({
                "id": f"q_{sample_counter}_date",
                "question_type": "date",
                "question": f"When was the paper '{title}' published?",
                "ground_truth": published,
                "ground_truth_doc_ids": [paper_id],
            })
            sample_counter += 1

        # 4. Question about categories
        if categories:
            test_samples.append({
                "id": f"q_{sample_counter}_categories",
                "question_type": "categories",
                "question": f"What categories or subjects does the paper '{title}' belong to?",
                "ground_truth": categories,
                "ground_truth_doc_ids": [paper_id],
            })
            sample_counter += 1

    write_json(output_path, test_samples)
    return test_samples

