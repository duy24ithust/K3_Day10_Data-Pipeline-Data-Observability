# 📘 Báo Cáo & Hướng Dẫn Kỹ Thuật: Cleaning & Data Corruption (Người 3)

---

## 🎯 PART 1: CHECKPOINT 1 — LÀM SẠCH DỮ LIỆU (CLEANING)

### 1. Ý Nghĩa & Mục Tiêu Của Bước Cleaning
Trong hệ thống **Retrieval-Augmented Generation (RAG)** và **Data Pipeline**, dữ liệu thô (raw data) thu thập từ các nguồn bên ngoài (như Crossref API) thường chứa nhiều rác:
- Tiêu đề hoặc Abstract chứa các ký tự khoảng trắng thừa, thẻ HTML (`<i>`, `<b>`, `<jats:p>`).
- Dữ liệu bị trùng lặp bản ghi do API trả về nhiều lần.
- Một số bài báo thiếu Abstract/Summary hoặc tiêu đề rỗng.
- Ngày tháng chưa được chuẩn hóa dẫn đến việc không tính được độ tươi dữ liệu (**Freshness**).

👉 **Ý nghĩa cốt lõi của bước Cleaning**: Chuyển đổi dữ liệu thô từ `data/raw/crossref_records.json` thành cấu trúc dữ liệu sạch, đồng nhất và tối ưu ngữ nghĩa (`data/clean/`), giúp Vector Database (ChromaDB) index đúng thông tin và RAG Agent tra cứu chính xác nhất.

---

### 2. Phân Tích Thiết Kế Kỹ Thuật (Why & Design Decisions)

#### 2.1. Chuẩn hóa chuỗi (Text Normalization)
* **Tại sao cần làm?** Chuỗi chứa ký tự xuống dòng (`\n`), tab (`\t`), hoặc nhiều dấu cách thừa sẽ làm tăng số lượng token vô ích và giảm điểm tương đồng cosine (Cosine Similarity) khi tạo Vector Embedding.
* **Cách xử lý**: Dùng hàm `normalize_whitespace()` để quy đổi tất cả chuỗi trắng thành 1 dấu cách đơn và `strip()` hai đầu.

#### 2.2. Xây dựng cột `text_for_embedding` (Tối ưu Ngữ nghĩa cho Vector DB)
* **Tại sao cần làm?** Nếu chỉ embed mỗi `summary`, Vector DB sẽ thiếu ngữ cảnh về tác giả và chủ đề bài báo. Nếu embed từng trường riêng lẻ, ta sẽ mất nhiều lượt query.
* **Cách xử lý**: Tổng hợp các trường dữ liệu quan trọng nhất thành một văn bản theo định dạng:
  ```text
  Title: {title}
  Authors: {authors_joined}
  Categories: {categories_joined}
  Summary: {summary}
  ```

#### 2.3. Khử trùng lặp (`paper_id`) & Lọc bản ghi hỏng
* **Tại sao cần làm?** Trùng lặp `paper_id` khiến Vector DB lưu trùng vector, gây lãng phí bộ nhớ và trả về các kết quả trùng lặp khi Retrieve.
* **Cách xử lý**: 
  - Lọc bỏ bản ghi có `title` rỗng hoặc `summary_chars == 0`.
  - Giữ bản ghi xuất hiện đầu tiên: `df.drop_duplicates(subset=["paper_id"], keep="first")`.

#### 2.4. Tính toán độ tươi (`age_days`)
* **Tại sao cần làm?** Đảm bảo phục vụ module Data Observability (Người 5) theo dõi độ tươi của dữ liệu tri thức trong RAG system.
* **Cách xử lý**: Chuyển ngày phát hành `published` về dạng `datetime` và tính `age_days = (run_date - published_date).days`.

---

### 3. Đoạn Code Quan Trọng (`src/ingestion/cleaning.py`)

Dưới đây là phần code đã được triển khai hoàn chỉnh trong `src/ingestion/cleaning.py`:

```python
from __future__ import annotations

from datetime import datetime, timezone
import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records thành DataFrame chuẩn bị sẵn sàng cho Embedding."""
    if not records:
        return pd.DataFrame(columns=[
            "paper_id", "title", "summary", "authors", "categories",
            "primary_category", "published", "updated", "abs_url", "pdf_url",
            "comment", "authors_joined", "categories_joined", "summary_chars",
            "age_days", "text_for_embedding"
        ])

    # Chuẩn hóa timezone của run_date
    if run_date.tzinfo is not None:
        ref_date = run_date.astimezone(timezone.utc).replace(tzinfo=None)
    else:
        ref_date = run_date

    rows = []
    for rec in records:
        # 1. Làm sạch khoảng trắng rác
        title = normalize_whitespace(rec.title)
        summary = normalize_whitespace(rec.summary)

        # 2. Làm sạch danh sách tác giả và thể loại
        authors_clean = [normalize_whitespace(a) for a in rec.authors if normalize_whitespace(a)]
        categories_clean = [normalize_whitespace(c) for c in rec.categories if normalize_whitespace(c)]

        authors_joined = compact_join(authors_clean, ", ")
        categories_joined = compact_join(categories_clean, ", ")
        summary_chars = len(summary)

        # 3. Parse ngày phát hành & tính độ tươi age_days
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

        # 4. Gom nhóm văn bản tối ưu ngữ nghĩa cho Vector DB Embedding
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

    # 5. Lọc bỏ bản ghi rác (Tiêu đề rỗng hoặc Summary rỗng)
    df = df[df["title"].str.len() > 0]
    df = df[df["summary_chars"] > 0]

    # 6. Loại bỏ bản ghi trùng lặp paper_id
    df = df.drop_duplicates(subset=["paper_id"], keep="first")

    # 7. Sắp xếp theo ngày xuất bản giảm dần
    df = df.sort_values(by="published", ascending=False).reset_index(drop=True)

    return df
```

---

## 💥 PART 2: CHECKPOINT 5 — GIẢ LẬP LỖI DỮ LIỆU (DATA CORRUPTION)

### 4. Ý Nghĩa Của Bước Data Corruption
Trong thực tế sản xuất (Production Data Engineering), các sự cố dữ liệu (Data Outages / Bugs / Degradation) thường xuyên xảy ra:
- Nguồn upstream bị đứt khiến thiếu mất dữ liệu bài báo mới.
- Bug pipeline làm rỗng abstract hoặc cắt xẻn tiêu đề.
- Dữ liệu bị nhiễu rác (Noise tokens).
- Hệ thống bị nhân bản trùng lặp bản ghi.

👉 **Ý nghĩa cốt lõi của bước Corruption**: Khởi tạo dữ liệu lỗi có kiểm soát để minh chứng rằng **khi dữ liệu hỏng, các chỉ số Retrieval Hit Rate, F1 Score và LLM Judge Score của Agent sẽ bị suy giảm thảm hại**, đồng thời kích hoạt hệ thống cảnh báo **Data Quality & Freshness Observability Gates**.

---

### 5. Kịch Bản Data Corruption Chi Tiết

1. **Drop Latest Records**: Xóa 3 bản ghi bài báo mới nhất để tạo lỗi thiếu thông tin thời sự.
2. **Blank Summary**: Xóa rỗng summary của 2 bài báo để tạo lỗi thiếu Metadata.
3. **Inject Noise**: Chèn ký tự rác `[NOISE_CORRUPTED_TEXT_XYZ_12345_GARBAGE]` vào summary.
4. **Truncate Title**: Cắt ngắn tiêu đề bài báo xuống còn 5 ký tự.
5. **Stale Published Date**: Lùi ngày xuất bản về năm 2024 để kích hoạt cảnh báo Freshness Gate (bài báo cũ > 180 ngày).
6. **Add Duplicate Rows**: Nhân bản 2 dòng dữ liệu để tạo lỗi trùng lặp `paper_id`.
7. **Rebuild Embedding Text**: Tạo lại chuỗi `text_for_embedding` bị lỗi tương ứng.
8. **Logging**: Ghi nhật ký đầy đủ các hành động hỏng hóc vào file `data/results/corruption_log.json`.

---

### 6. Đoạn Code Quan Trọng (`src/ingestion/corruption.py`)

Dưới đây là phần code đã được triển khai hoàn chỉnh trong `src/ingestion/corruption.py`:

```python
from __future__ import annotations

from pathlib import Path
import pandas as pd

from core.utils import compact_join, write_json


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: Path | str) -> pd.DataFrame:
    """Simulate nhiều dạng data corruption trên cleaned DataFrame."""
    if df.empty:
        write_json(Path(output_log_path), {"initial_records_count": 0, "final_corrupted_records_count": 0, "actions_executed": []})
        return df.copy()

    corrupted_df = df.copy().reset_index(drop=True)
    logs = []

    total_initial = len(corrupted_df)

    # 1. Drop 3 bài mới nhất
    corrupted_df = corrupted_df.sort_values(by="published", ascending=False).reset_index(drop=True)
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

    # 2. Blank summary
    if n > 0:
        blanked_ids = []
        for idx in set([0, min(1, n - 1)]):
            corrupted_df.at[idx, "summary"] = ""
            blanked_ids.append(corrupted_df.at[idx, "paper_id"])
        logs.append({
            "type": "blank_summary",
            "count": len(blanked_ids),
            "paper_ids": blanked_ids,
            "description": "Erased summary text to simulate missing metadata"
        })

    # 3. Inject noise
    if n > 2:
        idx = 2
        paper_id = corrupted_df.at[idx, "paper_id"]
        original = str(corrupted_df.at[idx, "summary"])
        corrupted_df.at[idx, "summary"] = original + " [NOISE_CORRUPTED_TEXT_XYZ_12345_GARBAGE]"
        logs.append({
            "type": "inject_noise",
            "count": 1,
            "paper_ids": [paper_id],
            "description": "Injected synthetic noise tokens into summary"
        })

    # 4. Truncate title
    if n > 3:
        idx = 3
        paper_id = corrupted_df.at[idx, "paper_id"]
        corrupted_df.at[idx, "title"] = str(corrupted_df.at[idx, "title"])[:5]
        logs.append({
            "type": "truncate_title",
            "count": 1,
            "paper_ids": [paper_id],
            "description": "Truncated title to 5 characters"
        })

    # 5. Stale published date
    if n > 4:
        idx = 4
        paper_id = corrupted_df.at[idx, "paper_id"]
        corrupted_df.at[idx, "published"] = "2024-01-01"
        corrupted_df.at[idx, "age_days"] = int(corrupted_df.at[idx, "age_days"]) + 365
        logs.append({
            "type": "stale_published_date",
            "count": 1,
            "paper_ids": [paper_id],
            "description": "Shifted publication date to 2024-01-01 (stale data)"
        })

    # 6. Add duplicate rows
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

    # 7. Rebuild text_for_embedding & summary_chars
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

    # 8. Ghi corruption log
    log_payload = {
        "initial_records_count": total_initial,
        "final_corrupted_records_count": len(corrupted_df),
        "actions_executed": logs
    }
    write_json(Path(output_log_path), log_payload)

    return corrupted_df
```

---

## 🧪 PART 3: KẾT QUẢ KIỂM THỬ TỰ ĐỘNG (PYTEST)

Toàn bộ các unit test cho cả 2 phần Cleaning và Corruption đã được viết và chạy thành công 100%:

```bash
./uv run pytest -v
```

**Kết quả Pytest**:
- `tests/test_crossref.py`: ✅ **PASSED**
- `tests/test_cleaning.py`: ✅ **PASSED**
- `tests/test_corruption.py`: ✅ **PASSED**

---

✅ **Người 3 đã hoàn thành xuất sắc 100% nhiệm vụ của Checkpoint 1 (Cleaning) và Checkpoint 5 (Data Corruption)!**
