# 📘 Hướng Dẫn Vận Hành Dự Án Day 10 - Data Pipeline & Observability
### dành cho Nhóm 5 Người (Chi tiết từng Checkpoint từ CP0 đến CP6)

---

## 📋 1. Quy Định Chung & 5 Quy Tắc Vàng

1. **Chỉ chạy Corruption sau khi Baseline đã hoàn thành**: Không bao giờ giả lập lỗi dữ liệu khi chưa có đầy đủ artifact của dữ liệu sạch.
2. **Khóa Test Set cố định**: Giữ nguyên `test_set.json`, Ground Truth, Evaluator và Tham số Top-K khi so sánh cả 3 trạng thái.
3. **Phân tách không gian lưu trữ**: Dùng đường dẫn và tên Collection ChromaDB riêng biệt (`papers-baseline`, `papers-corrupted`, `papers-repaired`), **tuyệt đối không ghi đè**.
4. **Khôi phục dữ liệu từ Raw (Data Provenance)**: Thực hiện Repair bằng cách chạy lại pipeline từ nguồn `data/raw/`, tuyệt đối không sửa tay kết quả JSON.
5. **Tính trung thực của số liệu**: Báo cáo Markdown phải trỏ tới file artifact thật; không commit `.env` hoặc API Key lên Git.

---

## 👥 2. Sơ Đồ Phân Công Vai Trò (Team Roles Matrix - 5 Người)

| Mã Vai Trò | Tên Vai Trò | Phạm vi Phụ trách | File Code & Artifacts xử lý |
| :---: | :--- | :--- | :--- |
| **[Người 1]** | **Pipeline Integrator (Leader)** | Điều phối pipeline, quản lý config, release & demo. | `src/core/`, `src/pipelines/`, `script/` |
| **[Người 2]** | **Ingestion Owner** | Gọi Crossref API, lưu giữ raw response & raw records. | `src/ingestion/crossref.py`, `data/raw/` |
| **[Người 3]** | **Cleaning & Corruption Owner** | Làm sạch data, chuẩn hóa text, giả lập lỗi & repair. | `src/ingestion/cleaning.py`, `src/ingestion/corruption.py`, `data/clean/` |
| **[Người 4]** | **RAG & Agent Owner** | MiniLM Embeddings, ChromaDB, Search/Lookup, Agent QA. | `src/retrieval/`, `data/embeddings/` |
| **[Người 5]** | **Evaluation & Observability Owner** | Test set, Metrics, Data Quality & Freshness, Report. | `src/evaluation/`, `src/observability/`, `data/reports/` |

---

## ⏱️ 3. Hướng Dẫn Chi Tiết Từng Checkpoint (CP0 ➔ CP6)

### 🚀 Checkpoint 0 (00:00 – 00:30): Khởi Động, Contract & Ingestion Raw
* **Mục tiêu**: Thống nhất Data Contract, chuẩn bị môi trường, fetch dữ liệu từ API Crossref và lưu bản gốc vào `data/raw/`.

#### Nhiệm vụ từng người:
* **[Người 1 - Leader]**: Chốt phân công, branch Git (`main`), kiểm tra file `.env`, vẽ luồng bàn giao dữ liệu `Raw ➔ Clean ➔ Index ➔ Eval ➔ Report`.
* **[Người 2 - Ingestion]**: Hoàn thiện `src/ingestion/crossref.py`, thêm xử lý retry/backoff khi dính rate limit (HTTP 429/503). Lưu 2 file `data/raw/crossref_response.json` và `data/raw/crossref_records.json`.
* **[Người 3 - Cleaning]**: Đọc target clean schema, chốt quy tắc xử lý null, trùng lặp và định dạng ngày tháng.
* **[Người 4 - RAG]**: Đọc module `src/retrieval/index.py`, thống nhất đặt tên collection ChromaDB cho baseline (`papers-baseline`).
* **[Người 5 - Eval & Observe]**: Đọc `src/evaluation/testset.py` & `src/observability/quality.py`, phác thảo khung báo cáo.

👉 **Bàn giao (Handoff)**: **[Người 2]** chuyển file `data/raw/crossref_records.json` cho **[Người 3]**.  
✅ **Tiêu chí xong CP0**: File JSON trong `data/raw/` tồn tại, `paper_id` dạng DOI ổn định.  
💻 **Lệnh kiểm tra**: `ls data/raw`

---

### 🧹 Checkpoint 1 (00:30 – 01:05): Cleaning & Data Quality Gates
* **Mục tiêu**: Làm sạch dữ liệu thô, tạo các cột trợ thủ ngữ nghĩa và thiết lập quy tắc kiểm tra chất lượng ban đầu.

#### Nhiệm vụ từng người:
* **[Người 3 - Cleaning]**: Hoàn thiện `src/ingestion/cleaning.py`:
  - Normalize whitespace trong `title` và `summary`.
  - Parse ngày xuất bản, tính `age_days = (run_date - published_date).days`.
  - Tạo các cột: `authors_joined`, `categories_joined`, `summary_chars`, `text_for_embedding`.
  - Lọc trùng theo `paper_id` và loại bỏ dòng rác. Xuất kết quả vào `data/clean/`.
* **[Người 5 - Eval & Observe]**: Chạy Data Quality check lần 1 trên dữ liệu sạch (check row count, null rate, duplicate `paper_id`).
* **[Người 4 - RAG]**: Đọc kiểm tra mẫu `text_for_embedding`, đảm bảo thông tin ngữ nghĩa đầy đủ.
* **[Người 2 - Ingestion]**: Kiểm tra tính nhất quán số lượng giữa Raw vs Clean bản ghi.
* **[Người 1 - Leader]**: Review logic clean và chốt schema dữ liệu sạch.

👉 **Bàn giao (Handoff)**: **[Người 3]** push code/artifact dữ liệu sạch cho **[Người 4]** và **[Người 5]**.  
✅ **Tiêu chí xong CP1**: File Clean CSV/JSON xuất hiện trong `data/clean/`, `paper_id` unique.  
💻 **Lệnh kiểm tra**: `ls data/clean`

---

### 🔍 Checkpoint 2 (01:05 – 01:35): Test Set, RAG Index & Smoke Test
* **Mục tiêu**: Sinh bộ câu hỏi kiểm thử chuẩn (Ground Truth), nạp dữ liệu sạch vào ChromaDB và chạy thử Agent.

#### Nhiệm vụ từng người:
* **[Người 5 - Eval & Observe]**: Viết hàm `build_test_set` trong `src/evaluation/testset.py`, lưu file cố định `data/eval/test_set.json` (chứa `question`, `ground_truth`, `ground_truth_doc_ids`).
* **[Người 4 - RAG]**: Dùng model `sentence-transformers/all-MiniLM-L6-v2` tạo embeddings từ `text_for_embedding`, lưu vào ChromaDB collection `papers-baseline`. Thử nghiệm Semantic Search & Exact Lookup.
* **[Người 3 - Cleaning]**: Hỗ trợ Người 4/5 nếu phát hiện lỗi schema hoặc text bị rỗng.
* **[Người 2 - Ingestion]**: Kiểm tra đối chiếu `paper_id` xuyên suốt Raw ➔ Clean ➔ Vector Metadata.
* **[Người 1 - Leader]**: Đảm bảo đường dẫn collection `papers-baseline` nằm riêng biệt.

👉 **Bàn giao (Handoff)**: **[Người 5]** chốt file `test_set.json`, **[Người 4]** chốt collection `papers-baseline`.  
✅ **Tiêu chí xong CP2**: `test_set.json` và ChromaDB baseline tồn tại; Agent tìm kiếm trả về đúng văn bản.  
💻 **Lệnh kiểm tra**: `find data -maxdepth 2 -type f | sort`

---

### 📊 Checkpoint 3 (01:35 – 02:00): Baseline End-to-End & Báo Cáo Phase 1
* **Mục tiêu**: Kích hoạt toàn bộ pipeline baseline dữ liệu sạch end-to-end và xuất các chỉ số tiêu chuẩn.

#### Nhiệm vụ từng người:
* **[Người 1 - Leader]**: Hoàn thiện file `src/pipelines/phase1.py` ghép nối toàn bộ luồng. Kích hoạt chạy: `python script/run_phase1.py`.
* **[Người 5 - Eval & Observe]**: Đo các chỉ số baseline (`retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`), lưu file `data/results/baseline_metrics.json` và xuất báo cáo `data/reports/phase1_report.md`.
* **[Người 4 - RAG]**: Đảm bảo Agent sử dụng tool kết quả chính xác.
* **[Người 2 & Người 3]**: Kiểm tra rà soát lại artifacts trong `data/raw/` và `data/clean/`.

✅ **Tiêu chí xong CP3**: File `baseline_metrics.json` và `phase1_report.md` được tạo ra với số liệu thật.  
💻 **Lệnh kiểm tra**: `python script/run_phase1.py`

---

### ☕ Checkpoint 4 (02:00 – 02:15): Nghỉ Giải Lao 15 Phút
* **Mục tiêu**: Cả nhóm nghỉ ngơi 15 phút. Rà soát kết quả Baseline và chốt kịch bản làm hỏng dữ liệu (Corruption Scenario) cho Pha 2.

---

### 💣 Checkpoint 5 (02:15 – 03:15): Corruption Có Kiểm Soát & Đo Impact
* **Mục tiêu**: Chủ động làm hỏng dữ liệu sạch, nạp vào collection riêng và đo lường sự suy giảm chất lượng của RAG Agent.

#### Nhiệm vụ từng người:
* **[Người 3 - Cleaning & Corruption]**: Hoàn thiện `src/ingestion/corruption.py`:
  - Xóa bớt bản ghi mới nhất.
  - Làm rỗng summary một số bài.
  - Chèn ký tự nhiễu rác vào text.
  - Làm cũ ngày xuất bản (`published`).
  - Nhân bản dòng trùng lặp (`duplicate rows`).
  - Rebuild `text_for_embedding` bị hỏng và ghi file `data/results/corruption_log.json`.
* **[Người 4 - RAG]**: Nạp dataset bị lỗi vào collection ChromaDB mới hoàn toàn tên là `papers-corrupted`.
* **[Người 5 - Eval & Observe]**: Chạy lại **bộ `test_set.json` cũ (từ CP2)** trên `papers-corrupted`. Ghi nhận sự sụt giảm chỉ số RAG và kích hoạt cảnh báo Data Quality/Freshness.
* **[Người 1 - Leader]**: Hoàn thiện luồng `src/pipelines/corruption_flow.py`, đảm bảo không ghi đè lên baseline.

✅ **Tiêu chí xong CP5**: Có file `corruption_log.json` và chỉ số RAG bị giảm được ghi nhận.  
💻 **Lệnh kiểm tra**: `python script/run_corruption_flow.py`

---

### 🛠️ Checkpoint 6 (03:15 – 04:00): Repair từ Raw, Comparison, Review & Demo
* **Mục tiêu**: Phục hồi (repair) dữ liệu từ `data/raw/`, đo lường sự phục hồi của Agent, xuất báo cáo đối chiếu 3 trạng thái và demo.

#### Nhiệm vụ từng người:
* **[Người 2 - Ingestion] & [Người 3 - Cleaning]**: Thực hiện **Repair** bằng cách load lại dữ liệu từ `data/raw/crossref_records.json` và chạy lại hàm `build_clean_dataframe()` tạo ra `repaired_dataset`.
* **[Người 4 - RAG]**: Nạp dữ liệu vừa phục hồi vào collection mới `papers-repaired` và chạy thử nghiệm.
* **[Người 5 - Eval & Observe]**: Chạy lại `test_set.json` trên `papers-repaired` -> Số liệu phục hồi trở lại. Xuất báo cáo so sánh `data/reports/corruption_report.md` (chứa bảng đối chiếu Delta: **Baseline ➔ Corrupted ➔ Repaired**).
* **[Người 1 - Leader]**: Rà soát checklist cuối cùng (không lộ API key, code chạy mượt), phân công các thành viên trình bày demo.

✅ **Tiêu chí xong CP6**: Có file `repaired_metrics.json` và `corruption_report.md` khớp số liệu thật; Repo sạch secret.  
💻 **Lệnh kiểm tra**: `ls data/results/repaired_metrics.json data/reports/corruption_report.md`

---

## 🛠️ 4. Bảng Lệnh Terminal Nhanh Cho Cả Nhóm (CLI Reference)

```bash
# 1. Kích hoạt môi trường ảo
source .venv/bin/activate

# 2. Cài đặt lại thư viện nếu cần
./uv sync

# 3. Kiểm tra Unit Test toàn bộ dự án
./uv run pytest -v

# 4. Chạy Baseline Phase 1 (Giai đoạn 1)
./uv run python script/run_phase1.py

# 5. Chạy Corruption Flow Phase 2 (Giai đoạn 2)
./uv run python script/run_corruption_flow.py
```
