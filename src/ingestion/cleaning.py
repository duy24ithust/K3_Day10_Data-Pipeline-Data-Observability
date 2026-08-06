from __future__ import annotations

from datetime import datetime, timezone
import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records thành DataFrame chuẩn bị sẵn sàng cho Embedding.

    Steps:
    1. Normalize title, summary, authors, categories.
    2. Parse published/updated date sang datetime.
    3. Tính age_days dựa trên run_date.
    4. Tạo các cột helper:
       - authors_joined
       - categories_joined
       - summary_chars
       - text_for_embedding
    5. Drop duplicates và filter bản ghi rác (title rỗng hoặc summary rỗng).
    6. Sort dataframe và return.
    """
    if not records:
        return pd.DataFrame(columns=[
            "paper_id", "title", "summary", "authors", "categories",
            "primary_category", "published", "updated", "abs_url", "pdf_url",
            "comment", "authors_joined", "categories_joined", "summary_chars",
            "age_days", "text_for_embedding"
        ])

    # Standardize run_date timezone for subtraction
    if run_date.tzinfo is not None:
        ref_date = run_date.astimezone(timezone.utc).replace(tzinfo=None)
    else:
        ref_date = run_date

    rows = []
    for rec in records:
        title = normalize_whitespace(rec.title)
        summary = normalize_whitespace(rec.summary)

        # Clean authors and categories lists
        authors_clean = [normalize_whitespace(a) for a in rec.authors if normalize_whitespace(a)]
        categories_clean = [normalize_whitespace(c) for c in rec.categories if normalize_whitespace(c)]

        authors_joined = compact_join(authors_clean, ", ")
        categories_joined = compact_join(categories_clean, ", ")
        summary_chars = len(summary)

        # Parse published date
        pub_str = (rec.published or "").strip()
        pub_dt = None
        if pub_str:
            try:
                dt = pd.to_datetime(pub_str, errors="coerce")
                if pd.notna(dt):
                    pub_dt = dt.to_pydatetime()
                    if pub_dt.tzinfo is not None:
                        pub_dt = pub_dt.astimezone(timezone.utc).replace(tzinfo=None)
            except Exception:
                pub_dt = None

        if pub_dt is not None:
            age_days = max(0, (ref_date - pub_dt).days)
            pub_formatted = pub_dt.strftime("%Y-%m-%d")
        else:
            age_days = 9999
            pub_formatted = pub_str

        # Build composite text_for_embedding
        text_parts = [f"Title: {title}"]
        if authors_joined:
            text_parts.append(f"Authors: {authors_joined}")
        if categories_joined:
            text_parts.append(f"Categories: {categories_joined}")
        if summary:
            text_parts.append(f"Summary: {summary}")
        text_for_embedding = "\n".join(text_parts)

        rows.append({
            "paper_id": rec.paper_id.strip(),
            "title": title,
            "summary": summary,
            "authors": authors_clean,
            "categories": categories_clean,
            "primary_category": rec.primary_category,
            "published": pub_formatted,
            "updated": rec.updated,
            "abs_url": rec.abs_url,
            "pdf_url": rec.pdf_url,
            "comment": rec.comment,
            "authors_joined": authors_joined,
            "categories_joined": categories_joined,
            "summary_chars": summary_chars,
            "age_days": age_days,
            "text_for_embedding": text_for_embedding,
        })

    df = pd.DataFrame(rows)

    # Filter out invalid records (empty title or empty summary)
    df = df[df["title"].str.len() > 0]
    df = df[df["summary_chars"] > 0]

    # Deduplicate by paper_id (keep first occurrence)
    df = df.drop_duplicates(subset=["paper_id"], keep="first")

    # Sort by published date descending and reset index
    df = df.sort_values(by="published", ascending=False).reset_index(drop=True)

    return df

