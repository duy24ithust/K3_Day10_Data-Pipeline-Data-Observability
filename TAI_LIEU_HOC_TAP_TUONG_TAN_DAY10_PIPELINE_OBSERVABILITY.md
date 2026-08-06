# BẢN NGUYÊN LÝ & HƯỚNG DẪN CHUYÊN SÂU: DATA PIPELINE & DATA OBSERVABILITY CHO RAG AGENTS

> **Tài liệu này được biên soạn dành cho Kỹ sư AI & Data Science.**  
> Giúp bạn hiểu tường tận bản chất kiến trúc, giải mã chi tiết từng dòng code, nguyên lý hoạt động của Data Observability, và cung cấp bộ khung chuẩn (Playbook) để áp dụng vào bất kỳ bài toán RAG/AI Agent nào trong thực tế doanh nghiệp.

---

## 📚 MỤC LỤC
1. [Triết Lý Cốt Lõi: Vì Sao RAG Agent Cần Data Pipeline & Observability?](#1-triết-lý-cốt-lõi)
2. [Sơ Đồ Kiến Trúc Luồng Dữ Liệu End-to-End](#2-sơ-đồ-kiến-trúc)
3. [Giải Mã Chi Tiết 5 Module Kỹ Thuật (Đi Kèm Code & Giải Thích)](#3-giải-mã-5-module)
   - [Module 1: Ingestion & Data Lineage (Thu thập & Lưu vết)](#module-1-ingestion)
   - [Module 2: Cleaning & Data Modeling (Làm sạch & Tạo Embedding Text)](#module-2-cleaning)
   - [Module 3: Vector Indexing & ChromaDB Management (Đánh chỉ mục Vector)](#module-3-vector-index)
   - [Module 4: Evaluation Benchmark Engine (Bộ đo đạc chỉ số Agent)](#module-4-evaluation)
   - [Module 5: Data Observability Gates (Cổng kiểm soát chất lượng & độ tươi)](#module-5-observability)
4. [Cơ Chế Giả Lập Lỗi (Corruption) & Tự Phục Hồi (Automated Repair)](#4-corruption--repair)
5. [Phân Tích Số Liệu Thực Nghiệm & Quan Hệ Nhân Quả](#5-phân-tích-số-liệu)
6. [Bộ Khung Áp Dụng Cho Bài Toán Thực Tế Doanh Nghiệp (Reusable Playbook)](#6-bộ-khung-áp-dụng)

---

<a name="1-triết-lý-cốt-lõi"></a>
## 1. TRIẾT LÝ CỐT LÕI: VÌ SAO RAG AGENT CẦN DATA PIPELINE & OBSERVABILITY?

### 🎯 Nguyên tắc "Garbage In = Garbage Out" trong AI
Trong các hệ thống RAG (Retrieval-Augmented Generation), mô hình LLM (như Gemini, GPT-4) không tự sáng tạo ra tri thức mới mà dựa vào **ngữ cảnh (Context)** được tìm kiếm từ Vector Database để trả lời.
- **Nếu dữ liệu đầu vào sạch**: RAG Agent tìm đúng tài liệu ➔ LLM trả lời chính xác, trôi chảy.
- **Nếu dữ liệu đầu vào bị hỏng** (rác text, rỗng abstract, trùng lặp ID, dữ liệu quá cũ): RAG Agent lấy nhầm ngữ cảnh rác ➔ LLM trả lời bịa đặt (Hallucination) hoặc từ chối trả lời.

### 🛡️ 3 Trụ Cột Kỹ Thuật Trong Bài Lab
1. **Data Lineage / Provenance (Tính truy vết nguồn gốc)**:  
   Mọi bản ghi dữ liệu phải luôn lưu giữ bản chụp nguyên bản (Raw JSON) ban đầu từ API. Nếu khâu đằng sau bị hỏng, ta luôn có thể quay lại "Nguồn sự thật" (`data/raw/`) để khôi phục.
2. **Data Observability Gates (Cổng giám sát chất lượng)**:  
   Giống như bộ lọc nước trước khi đưa vào bể chứa, Data Observability chủ động kiểm tra tính toàn vẹn (Quality Checks) và độ tươi (Freshness Check) của dữ liệu **ngay tại Pipeline** để báo động FAILED trước khi dữ liệu xấu chui vào Vector DB.
3. **Automated Self-Healing (Tự động phục hồi)**:  
   Khi phát hiện sự cố dữ liệu, hệ thống tự động kích hoạt luồng Re-ingest & Re-clean từ dữ liệu thô mà **không cần con người phải sửa thủ công từng dòng CSV**.

---

<a name="2-sơ-đồ-kiến-trúc"></a>
## 2. SƠ ĐỒ KIẾN TRÚC LUỒNG DỮ LIỆU END-TO-END

```text
┌────────────────┐      ┌─────────────────────────┐      ┌─────────────────────────┐
│ Crossref REST  │ ───> │   data/raw/             │ ───> │  src/ingestion/         │
│ API (Nguồn)    │      │  (Raw JSON Lineage)     │      │  cleaning.py            │
└────────────────┘      └─────────────────────────┘      └─────────────────────────┘
                                                                      │
                                                                      ▼
┌────────────────┐      ┌─────────────────────────┐      ┌─────────────────────────┐
│ Evaluation     │ <─── │   ChromaDB Collection   │ <─── │  data/clean/            │
│ Test Set (40Q) │      │  (papers-baseline)      │      │  papers_clean.csv       │
└────────────────┘      └─────────────────────────┘      └─────────────────────────┘
        │                                                             │
        ▼                                                             ▼
┌────────────────┐                                       ┌─────────────────────────┐
│ Metrics Output │                                       │ Data Observability      │
│ (Hit Rate 100%)│                                       │ (Quality & Freshness)   │
└────────────────┘                                       └─────────────────────────┘
```

---

<a name="3-giải-mã-5-module"></a>
## 3. GIẢI MÃ CHI TIẾT 5 MODULE KỸ THUẬT (ĐI KÈM CODE & GIẢI THÍCH)

<a name="module-1-ingestion"></a>
### 🟢 Module 1: Ingestion & Data Lineage (`src/ingestion/crossref.py`)

#### **Mục tiêu**: 
Thu thập dữ liệu bài báo khoa học từ Crossref REST API, xử lý trôi chảy các sự cố mạng/rate limit và lưu trữ bản chụp thô (Raw Artifacts) nguyên bản.

#### **Đoạn Code Cốt Lõi**:
```python
def fetch_source_records(
    query: str,
    from_pub_date: str = "2026-02-07",
    rows: int = 50,
    max_retries: int = 3,
) -> list[PaperRecord]:
    """Fetch dữ liệu từ Crossref API có cơ chế Retry Exponential Backoff"""
    url = "https://api.crossref.org/works"
    params = {
        "query": query,
        "filter": f"from-pub-date:{from_pub_date}",
        "rows": rows,
    }

    # 1. Cơ chế Exponential Backoff cho API resilience
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            payload = response.json()
            break
        except requests.RequestException as e:
            if attempt == max_retries - 1:
                raise RuntimeError(f"Crossref API call failed: {e}")
            time.sleep(2 ** attempt)  # Chờ 1s, 2s, 4s...

    # 2. Lưu vết Raw Response (Data Lineage)
    raw_response_path = get_path("data/raw/crossref_response.json")
    write_json(raw_response_path, payload)

    # 3. Parse JSON thành danh sách Dataclass PaperRecord
    records = parse_crossref_payload(payload)
    return records
```

#### **Giải thích kỹ thuật chuyên sâu**:
- **Exponential Backoff (`time.sleep(2 ** attempt)`)**: Khi gọi API bên thứ ba, server có thể trả về lỗi `429 Too Many Requests` hoặc `503 Service Unavailable`. Việc tăng thời gian chờ gấp đôi sau mỗi lần thử lại giúp tránh làm sập server và tăng tỷ lệ thành công của request.
- **Lưu file `crossref_response.json`**: Đây chính là việc thiết lập **Data Lineage**. Nếu sau này logic parse bị lỗi, ta không cần gọi lại API (tốn tài nguyên) mà chỉ cần load lại file JSON thô này.

---

<a name="module-2-cleaning"></a>
### 🟢 Module 2: Cleaning & Data Modeling (`src/ingestion/cleaning.py`)

#### **Mục tiêu**: 
Chuyển đổi dữ liệu thô nhiều rác thành `pd.DataFrame` chuẩn mực, khử trùng lặp, tính tuổi bài báo (`age_days`) và gom nhóm thông tin thành cột `text_for_embedding`.

#### **Đoạn Code Cốt Lõi**:
```python
def build_clean_dataframe(
    records: list[PaperRecord],
    run_date: datetime | None = None,
) -> pd.DataFrame:
    """Làm sạch dữ liệu và tạo feature text_for_embedding cho Vector Search"""
    if run_date is None:
        run_date = datetime.now(timezone.utc)

    cleaned_rows = []
    for r in records:
        # 1. Làm sạch khoảng trắng rác & thẻ HTML
        title_clean = normalize_whitespace(r.title)
        summary_clean = normalize_whitespace(r.summary)

        # Lọc bỏ bài thiếu thông tin cốt lõi
        if not r.paper_id or not title_clean or not summary_clean:
            continue

        # 2. Parse ngày xuất bản & Tính độ tươi (age_days)
        pub_dt = parse_iso_date(r.published)
        age_days = (run_date - pub_dt).days if pub_dt else 0

        # 3. Ghép nối có cấu trúc để làm đầu vào cho Vector Embeddings
        text_for_embedding = (
            f"Title: {title_clean}\n"
            f"Authors: {', '.join(r.authors)}\n"
            f"Categories: {', '.join(r.categories)}\n"
            f"Summary: {summary_clean}"
        )

        cleaned_rows.append({
            "paper_id": r.paper_id,
            "title": title_clean,
            "summary": summary_clean,
            "authors": r.authors,
            "categories": r.categories,
            "published": r.published,
            "age_days": age_days,
            "text_for_embedding": text_for_embedding,
        })

    df = pd.DataFrame(cleaned_rows)
    # 4. Khử trùng lặp theo paper_id (Uniqueness constraint)
    df = df.drop_duplicates(subset=["paper_id"], keep="first").reset_index(drop=True)
    return df
```

#### **Giải thích kỹ thuật chuyên sâu**:
- **Kỹ thuật đóng gói `text_for_embedding`**:  
  Thay vì chỉ embed phần `summary`, việc thêm prefix có cấu trúc `Title: ... \n Authors: ... \n Summary: ...` giúp mô hình Embedding (như MiniLM) bắt được mối liên hệ ngữ nghĩa giữa tác giả, tiêu đề và tóm tắt bài báo. Khi người dùng hỏi "Bài báo của tác giả X về chủ đề Y", RAG Agent sẽ định vị chính xác bài báo đó.
- **Tính cột `age_days`**:  
  Là căn cứ số hóa để làm đầu vào cho **Freshness Gate** ở Module 5 (ví dụ: phát hiện bài báo cũ quá 180 ngày).

---

<a name="module-3-vector-index"></a>
### 🟢 Module 3: Vector Indexing & ChromaDB Management (`src/retrieval/index.py`)

#### **Mục tiêu**: 
Chuyển đổi văn bản `text_for_embedding` thành vector chiều cao (384-dimension qua MiniLM) và quản lý độc lập các Collections trong Vector DB ChromaDB.

#### **Đoạn Code Cốt Lõi**:
```python
class LocalEmbeddingIndex:
    def __init__(self, collection_name: str = "papers-baseline"):
        # 1. Khởi tạo model Embedding nhúng nhỏ nhẹ & nhanh (all-MiniLM-L6-v2)
        self.encoder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        # 2. Khởi tạo Persistent Client của ChromaDB
        self.chroma_client = chromadb.PersistentClient(path="./chroma_db")
        self.collection = self.chroma_client.get_or_create_collection(name=collection_name)

    def build_from_dataframe(self, df: pd.DataFrame) -> None:
        """Đưa toàn bộ DataFrame đã sạch vào Vector Database"""
        documents = df["text_for_embedding"].tolist()
        metadatas = df[["paper_id", "title", "published", "age_days"]].to_dict("records")
        ids = df["paper_id"].tolist()

        # Mã hóa văn bản thành Vector Embeddings
        embeddings = self.encoder.encode(documents, show_progress_bar=False).tolist()

        # Nạp vào ChromaDB
        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )

    def query(self, query_text: str, top_k: int = 3) -> list[dict]:
        """Truy vấn Top-K tài liệu tương đồng nhất"""
        query_vec = self.encoder.encode([query_text]).tolist()
        results = self.collection.query(query_embeddings=query_vec, n_results=top_k)
        return results
```

#### **Giải thích kỹ thuật chuyên sâu**:
- **Tách biệt 3 Collections (`papers-baseline`, `papers-corrupted`, `papers-repaired`)**:  
  Đây là bí quyết thiết kế để so sánh độc lập. Bằng cách lưu dữ liệu của pha sạch, pha lỗi và pha phục hồi vào 3 không gian lưu trữ riêng biệt trong ChromaDB, ta không bao giờ lo dữ liệu pha này làm ô nhiễm (pollute) dữ liệu pha kia.

---

<a name="module-4-evaluation"></a>
### 🟢 Module 4: Evaluation Benchmark Engine (`src/evaluation/metrics.py`)

#### **Mục tiêu**: 
Cung cấp thước đo định lượng độc lập để đánh giá năng lực của RAG Agent trên 3 tiêu chí: Truy vết (Retrieval), Khớp từ vựng (Token F1) và Khớp ngữ nghĩa bởi LLM Judge (Accuracy).

#### **Các Chỉ Số Cốt Lõi**:
1. **Retrieval Hit Rate**: Tỷ lệ câu hỏi mà Top-K tài liệu RAG lấy về có chứa đúng bài báo gốc (`ground_truth_doc_id`).
2. **Mean Token F1**: Độ tương đồng từ vựng giữa câu trả lời của Agent và đáp án chuẩn.
3. **LLM Judge Accuracy**: Dùng 1 LLM độc lập (Gemini 2.5 Flash) đóng vai "Giám khảo" chấm câu trả lời của Agent theo thang điểm 1 - 5.

#### **Đoạn Code Cốt Lõi (LLM Judge & Evaluator)**:
```python
def evaluate_pipeline(
    retriever_index: LocalEmbeddingIndex,
    test_set: list[dict],
    llm_agent: RAGAgent,
) -> dict:
    """Đánh giá toàn bộ RAG Agent trên tập Test Set cố định"""
    hit_count = 0
    token_f1_scores = []
    judge_scores = []

    for sample in test_set:
        question = sample["question"]
        gt_doc_ids = sample["ground_truth_doc_ids"]
        ground_truth = sample["ground_truth"]

        # 1. Đo Retrieval Hit Rate
        retrieved_docs = retriever_index.query(question, top_k=3)
        retrieved_ids = [doc["id"] for doc in retrieved_docs]
        if any(gt_id in retrieved_ids for gt_id in gt_doc_ids):
            hit_count += 1

        # 2. Sinh câu trả lời từ RAG Agent & Tính Token F1
        answer = llm_agent.answer(question, context=retrieved_docs)
        f1 = compute_token_f1(prediction=answer, reference=ground_truth)
        token_f1_scores.append(f1)

        # 3. Gọi LLM Judge chấm điểm chất lượng câu trả lời
        judge_result = llm_judge_eval(question, answer, ground_truth)
        judge_scores.append(judge_result["score"])

    hit_rate = hit_count / len(test_set)
    mean_f1 = sum(token_f1_scores) / len(token_f1_scores)
    mean_judge = sum(judge_scores) / len(judge_scores)
    judge_acc = sum(1 for s in judge_scores if s >= 3.0) / len(judge_scores)

    return {
        "retrieval_hit_rate": hit_rate,
        "mean_token_f1": mean_f1,
        "mean_judge_score": mean_judge,
        "judge_accuracy": judge_acc,
    }
```

#### **Giải thích kỹ thuật chuyên sâu**:
- **Nguyên tắc "Frozen Test Set"**:  
  Tập 40 câu hỏi kiểm thử (`data/eval/test_set.json`) được tạo ra 1 lần ở Baseline và **giữ nguyên 100% không đổi** cho cả pha Corrupted và Repaired. Giống như thi đại học, đề thi phải giữ nguyên thì mới so sánh được trình độ của học sinh khi khỏe mạnh và khi bị ốm.

---

<a name="module-5-observability"></a>
### 🟢 Module 5: Data Observability Gates (`src/observability/quality.py`)

#### **Mục tiêu**: 
Thiết lập "Rào chắn kiểm soát" tự động kiểm tra chất lượng dữ liệu tĩnh (Data Quality) và độ tươi động (Freshness Monitoring) trước khi cho phép dữ liệu đi tiếp.

#### **Đoạn Code Cốt Lõi**:
```python
def run_data_quality_checks(df: pd.DataFrame) -> dict:
    """Thực thi 5 quy tắc Data Quality Check"""
    checks = {}

    # 1. Row Count Gate (Completeness)
    checks["row_count_pass"] = len(df) >= 10

    # 2. Uniqueness Gate (Integrity)
    checks["paper_id_unique"] = df["paper_id"].is_unique

    # 3. Missing Title Check
    checks["no_missing_titles"] = df["title"].str.strip().ne("").all()

    # 4. Blank Summary Check
    checks["no_blank_summaries"] = df["summary"].str.strip().ne("").all()

    # 5. Embedding Field Check
    checks["has_embedding_text"] = "text_for_embedding" in df.columns

    overall_pass = all(checks.values())
    return {"status": "PASSED" if overall_pass else "FAILED", "details": checks}


def build_freshness_report(df: pd.DataFrame, max_age_days: int = 180) -> dict:
    """Kiểm tra độ tươi của dữ liệu bài báo khoa học"""
    stale_records = df[df["age_days"] > max_age_days]
    is_fresh = len(stale_records) == 0

    return {
        "status": "FRESH" if is_fresh else "STALE",
        "stale_count": len(stale_records),
        "max_age_threshold": max_age_days,
    }
```

---

<a name="4-corruption--repair"></a>
## 4. CƠ CHẾ GIẢ LẬP LỖI (CORRUPTION) & TỰ PHỤC HỒI (REPAIR)

### 🔴 6 Kịch Bản Giả Lập Lỗi Dữ Liệu (`corruption.py`)
Để thử thách khả năng chịu lỗi của hệ thống, ta chủ động tiêm 6 loại lỗi thực tế vào DataFrame sạch:
1. **Drop Latest Records**: Xóa 3 bài báo mới nhất ➔ *Làm mất thông tin thời sự.*
2. **Blank Summary**: Xóa rỗng Abstract của 2 bài báo ➔ *Làm mất ngữ cảnh tìm kiếm.*
3. **Inject Noise**: Chèn chuỗi rác `[NOISE_GARBAGE_XYZ_123]` vào summary ➔ *Làm sai lệch Vector Embedding.*
4. **Truncate Title**: Cắt tiêu đề còn 5 ký tự ➔ *Làm hỏng metadata.*
5. **Stale Date**: Lùi ngày xuất bản về năm 2024 (tuổi > 180 ngày) ➔ *Kích hoạt báo động Freshness STALE.*
6. **Add Duplicates**: Nhân bản 2 dòng trùng `paper_id` ➔ *Kích hoạt báo động Uniqueness FAILED.*

### 🔵 Nguyên Lý Tự Phục Hồi (Automated Self-Healing Repair)
Khi phát hiện Data Quality Gate báo ❌ **FAILED**, hệ thống không sửa thủ công file hỏng mà thực thi lệnh:
```text
Raw JSON Artifacts (data/raw/crossref_records.json)
        │
        ▼ (Tự động Re-Ingest & Re-Clean)
build_clean_dataframe()  ===> Dữ liệu sạch 100%
        │
        ▼ (Tự động Re-Index)
ChromaDB Collection ('papers-repaired')  ===> Hit Rate Phục Hồi 100%!
```
👉 **Tại sao lại làm như vậy?** Vì trong thực tế doanh nghiệp với hàng triệu bản ghi, việc sửa lỗi thủ công là vô vọng. **Khôi phục từ nguồn dữ liệu thô nguyên bản (Data Provenance)** là giải pháp duy nhất đảm bảo tính chuẩn xác 100%.

---

<a name="5-phân-tích-số-liệu"></a>
## 5. PHÂN TÍCH SỐ LIỆU THỰC NGHIỆM & QUAN HỆ NHÂN QUẢ

### 📊 Bảng Đối Chiếu Chỉ Số Qua 3 Trạng Thái (Thực Nghiệm 40 Câu Hỏi)

| Metric / Signal | 🟢 Baseline (Sạch) | 🔴 Corrupted (Gây Lỗi) | 🔵 Repaired (Phục Hồi) | Biến động khi Corrupted | Mức độ Phục hồi |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Retrieval Hit Rate** | **100.0%** | **60.0%** | **100.0%** | ⬇️ **-40.0%** | ⬆️ **+40.0%** |
| **Mean Token F1** | **0.5778** | **0.1575** | **0.5778** | ⬇️ **-0.4203** | ⬆️ **+0.4203** |
| **LLM Judge Accuracy** | **52.5%** | **12.5%** | **52.5%** | ⬇️ **-40.0%** | ⬆️ **+40.0%** |
| **Mean Judge Score** | **3.05 / 5.0** | **1.50 / 5.0** | **3.05 / 5.0** | ⬇️ **-1.55** | ⬆️ **+1.55** |
| **Data Quality Gate** | ✅ **PASSED** | ❌ **FAILED** | ✅ **PASSED** | Phát hiện rác & trùng | Khôi phục 100% |
| **Data Freshness Gate**| ✅ **FRESH** | ⚠️ **STALE** | ✅ **FRESH** | Cảnh báo bài cũ | Khôi phục 100% |

### 🔬 Phân Tích Quan Hệ Nhân Quả (Cause-Effect Analysis)

1. **Chuỗi 1: Tác hại của dữ liệu rác**  
   `Dữ liệu bị Corrupted (xóa abstract, chèn nhiễu, lùi ngày)` ➔ `Data Quality Gate lập tức báo FAILED & Freshness báo STALE` ➔ `Retrieval Hit Rate sụt 40% (từ 100% xuống 60%), khiến LLM Judge Accuracy tụt thảm hại từ 52.5% xuống 12.5%`.
   
2. **Chuỗi 2: Hiệu quả của cơ chế Tự Phục Hồi**  
   `Kích hoạt Repair Re-clean từ Raw Artifacts` ➔ `Data Quality Gate khôi phục về PASSED & Freshness khôi phục về FRESH` ➔ `Retrieval Hit Rate và LLM Judge Accuracy lập tức phục hồi 100% về mức Baseline ban đầu`.

---

<a name="6-bộ-khung-áp-dụng"></a>
## 6. BỘ KHUNG ÁP DỤNG CHO BÀI TOÁN THỰC TẾ DOANH NGHIỆP (PLAYBOOK)

Bạn có thể mang nguyên lý từ bài lab này để áp dụng cho bất kỳ dự án RAG/AI thực tế nào trong doanh nghiệp (ví dụ: Chatbot tra cứu văn bản pháp lý, Hệ thống hỏi đáp tài chính, CSKH nội bộ):

### 📋 Checklist 5 Bước Triển Khai Trong Dự Án Mới:

1. **Bước 1: Thiết lập Data Lineage (Luồng lưu vết thô)**
   - Mọi dữ liệu crawl từ Web, PDF, Database hay API phải luôn được lưu bản sao dạng Raw JSON/S3 Bucket trước khi biến đổi.

2. **Bước 2: Chuẩn hóa `text_for_embedding` có cấu trúc**
   - Đừng chỉ embed văn bản thô. Hãy thêm Metadata có nhãn như `[Phân loại: ... | Ngày: ... | Tiêu đề: ... | Nội dung: ...]` để mô hình Vector hóa bắt đúng ngữ cảnh.

3. **Bước 3: Đặt các cổng Data Observability Gates trước Vector DB**
   - Cài đặt các hàm kiểm tra tự động (Null Rate, Uniqueness, Max Age, Vector Dimension) trong Pipeline CI/CD. Nếu Quality Gate báo `FAILED`, chặn ngay không cho đưa dữ liệu vào Production Vector DB.

4. **Bước 4: Thiết lập Frozen Test Set để đánh giá định kỳ**
   - Xây dựng sẵn bộ 50 - 100 câu hỏi chuẩn kèm đáp án Ground Truth. Mỗi tuần chạy script tự động tính Hit Rate & F1 Score để phát hiện sớm sự suy giảm chất lượng AI.

5. **Bước 5: Xây dựng cơ chế Re-indexing tự động (Self-Healing)**
   - Viết sẵn script khôi phục 1-click từ Raw Data để khi hệ thống gặp sự cố ô nhiễm dữ liệu, chỉ cần 1 câu lệnh là toàn bộ Vector Index được làm sạch và nạp lại chuẩn xác.

---

### 💡 LỜI KHUYÊN NGHỀ NGHIỆP:
Một Kỹ sư AI giỏi không chỉ biết gọi API của OpenAI/Gemini để viết Chatbot đơn giản, mà là người biết **xây dựng hệ thống Data Pipeline vững chắc, có giám sát Observability chặt chẽ và tự phục hồi khi có sự cố**. Đó chính là sự khác biệt giữa sản phẩm Demo và sản phẩm cấp độ Production!
