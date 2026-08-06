# Báo Cáo & Hướng Dẫn Kỹ Thuật Checkpoint 1: Cleaning Data Pipeline (Người 3)

---

## 🎯 1. Ý Nghĩa & Mục Tiêu Của Bước Làm Sạch Dữ Liệu (Cleaning)

Trong hệ thống **Retrieval-Augmented Generation (RAG)** và **Data Pipeline**, dữ liệu thô (raw data) thu thập từ các nguồn bên ngoài (như Crossref API) thường chứa nhiều rác:
- Tiêu đề hoặc Abstract chứa các ký tự khoảng trắng thừa, thẻ HTML (`<i>`, `<b>`, `<jats:p>`).
- Dữ liệu bị trùng lặp bản ghi do API trả về nhiều lần.
- Một số bài báo thiếu Abstract/Summary hoặc tiêu đề rỗng.
- Ngày tháng chưa được chuẩn hóa dẫn đến việc không tính được độ tươi dữ liệu (**Freshness**).

👉 **Ý nghĩa cốt lõi của bước Cleaning**: Chuyển đổi dữ liệu thô từ `data/raw/crossref_records.json` thành cấu trúc dữ liệu sạch, đồng nhất và tối ưu ngữ nghĩa (`data/clean/`), giúp Vector Database (ChromaDB) index đúng thông tin và RAG Agent tra cứu chính xác nhất.

---

## 💡 2. Phân Tích Thiết Kế Kỹ Thuật (Why & Design Decisions)

### 2.1. Chuẩn hóa chuỗi (Text Normalization)
* **Tại sao cần làm?** Chuỗi chứa ký tự xuống dòng (`\n`), tab (`\t`), hoặc nhiều dấu cách thừa sẽ làm tăng số lượng token vô ích và giảm điểm tương đồng cosine (Cosine Similarity) khi tạo Vector Embedding.
* **Cách xử lý**: Dùng hàm `normalize_whitespace()` để quy đổi tất cả chuỗi trắng thành 1 dấu cách đơn và `strip()` hai đầu.

### 2.2. Xây dựng cột `text_for_embedding` (Tối ưu Ngữ nghĩa cho Vector DB)
* **Tại sao cần làm?** Nếu chỉ embed mỗi `summary`, Vector DB sẽ thiếu ngữ cảnh về tác giả và chủ đề bài báo. Nếu embed từng trường riêng lẻ, ta sẽ mất nhiều lượt query.
* **Cách xử lý**: Tổng hợp các trường dữ liệu quan trọng nhất thành một văn bản theo định dạng:
  ```text
  Title: {title}
  Authors: {authors_joined}
  Categories: {categories_joined}
  Summary: {summary}
  ```

### 2.3. Khử trùng lặp (`paper_id`) & Lọc bản ghi hỏng
* **Tại sao cần làm?** Trùng lặp `paper_id` khiến Vector DB lưu trùng vector, gây lãng phí bộ nhớ và trả về các kết quả trùng lặp khi Retrieve.
* **Cách xử lý**: 
  - Lọc bỏ bản ghi có `title` rỗng hoặc `summary_chars == 0`.
  - Giữ bản ghi xuất hiện đầu tiên: `df.drop_duplicates(subset=["paper_id"], keep="first")`.

### 2.4. Tính toán độ tươi (`age_days`)
* **Tại sao cần làm?** Đám bảo phục vụ module Data Observability (Người 5) theo dõi độ tươi của dữ liệu tri thức trong RAG system.
* **Cách xử lý**: Chuyển ngày phát hành `published` về dạng `datetime` và tính `age_days = (run_date - published_date).days`.

---

## 💻 3. Đoạn Code Quan Trọng (`src/ingestion/cleaning.py`)

Dưới đây là phần code đã được triển khai hoàn chỉnh trong [src/ingestion/cleaning.py](file:///run/media/monsterct2k3/Storages/Documents/Workspace/vinai/LABS/K3_Day10_Data-Pipeline-Data-Observability/src/ingestion/cleaning.py):

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

## 🧪 4. Kết Quả Kiểm Thử & Kiểm Chứng Trên Dữ Liệu Thật

### 4.1. Unit Test tự động
Đã tạo file kiểm thử [tests/test_cleaning.py](file:///run/media/monsterct2k3/Storages/Documents/Workspace/vinai/LABS/K3_Day10_Data-Pipeline-Data-Observability/tests/test_cleaning.py) kiểm tra đầy đủ các trường hợp:
- Chuẩn hóa khoảng trắng.
- Lọc bỏ bài báo có summary rỗng.
- Khử trùng lặp `paper_id`.
- Tính đúng `age_days`.

**Kết quả chạy `pytest`**:
```bash
./uv run pytest -v
# Kết quả: 100% PASSED (test_crossref.py & test_cleaning.py)
```

### 4.2. Chạy thử nghiệm trên 456 bản ghi dữ liệu thật từ Người 2 (`crossref_records.json`)
```text
Cleaned 456 raw records into 456 clean rows!
                             paper_id                                              title  age_days  summary_chars
0  10.47576/2949-1894.2026.7.7.023  Снижение рисков применения LLM...                       52            1721
1  10.36227/techrxiv.177272838...  A Survey of (Deep RAG) Deep Retrieval...               154            1443
2  10.63646/kpqm1958                The Age of Autonomous Agents: A Bibliometric...         37            1840
```

✅ **Dữ liệu sạch đã sẵn sàng 100% để bàn giao cho Người 4 (RAG Owner) và Người 5 (Evaluation & Observability Owner)!**
