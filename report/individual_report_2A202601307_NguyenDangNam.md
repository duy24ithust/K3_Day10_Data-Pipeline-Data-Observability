# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| :--- | :--- |
| **Họ và tên** | **Nguyễn Đăng Nam** |
| **MSSV** | **2A202601307** |
| **Khóa/Lớp** | **K3** |
| **Tên nhóm** | **B4** |
| **Vai trò chính** | **Người 3 — Cleaning & Data Corruption Owner** |
| **Repository** | `https://github.com/duy24ithust/K3_Day10_Data-Pipeline-Data-Observability` |
| **Ngày hoàn thành** | `2026-08-06` |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| :--- | :--- | :--- | :--- | :--- |
| **Data Cleaning Pipeline** | `src/ingestion/cleaning.py`<br>(`build_clean_dataframe`) | Raw records từ Crossref<br>`data/raw/crossref_records.json` | Cleaned Dataset<br>`data/clean/papers_clean.csv`, `.json` | **Hoàn thành** |
| **Data Corruption Simulation** | `src/ingestion/corruption.py`<br>(`corrupt_clean_dataframe`) | Cleaned DataFrame | Corrupted Dataset & Log<br>`data/results/corruption_log.json` | **Hoàn thành** |
| **Unit Testing & Documentation** | `tests/test_cleaning.py`<br>`tests/test_corruption.py`<br>`Guide_Nguoi3_Cleaning.md` | Code implementations | Unit test suite (100% PASSED)<br>Báo cáo kỹ thuật Người 3 | **Hoàn thành** |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| :--- | :--- | :--- |
| **Hỗ trợ định dạng Embedding Text** | Người 4 (RAG Owner / `src/retrieval/`) | Đảm bảo cột `text_for_embedding` chứa đủ Title, Authors, Categories, Summary để nạp vào ChromaDB. |
| **Hỗ trợ Data Observability Checks** | Người 5 (Eval Owner / `src/observability/`) | Phối hợp đối chiếu các lỗi giả lập (`corruption_log.json`) với tín hiệu Quality/Freshness Gates. |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| :--- | :--- | :--- | :--- |
| **Xây dựng Data Cleaning Pipeline** | `src/ingestion/cleaning.py`<br>`build_clean_dataframe()` | 24/24 bản ghi thô được làm sạch 100%, tạo cột `text_for_embedding` và `age_days`. | `./uv run pytest tests/test_cleaning.py` |
| **Giả lập 6 kịch bản Data Corruption** | `src/ingestion/corruption.py`<br>`corrupt_clean_dataframe()` | Tạo dataset lỗi và file nhật ký `data/results/corruption_log.json`. | `./uv run pytest tests/test_corruption.py` |

**Nêu một output cụ thể mà phần việc của bạn tạo ra**:
Hàm `build_clean_dataframe` đã chuẩn hóa thành công 456 bản ghi thô từ Crossref API, tạo ra cột `text_for_embedding` có cấu trúc giúp RAG Agent đạt **100% Retrieval Hit Rate** ở pha Baseline. Hàm `corrupt_clean_dataframe` đã giả lập thành công 6 dạng lỗi khiến Hit Rate sụt giảm còn **60%**, minh chứng tác hại của dữ liệu xấu.

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Dữ liệu thô từ Crossref API chứa nhiều ký tự rác (HTML tags, whitespace thừa), chưa có thông tin độ tuổi (`age_days`) và các trường dữ liệu bị phân tán. Nhiệm vụ của tôi là làm sạch, chuẩn hóa và đóng gói thành `text_for_embedding` tối ưu ngữ nghĩa cho Vector DB; đồng thời viết module gây hỏng dữ liệu có kiểm soát để phục vụ thực nghiệm Data Observability.

### Cách triển khai
1. **Cleaning**:
   - Dùng `normalize_whitespace()` làm sạch tiêu đề và summary.
   - Parse chuỗi ngày `published` thành `datetime` và tính `age_days = (run_date - published_date).days`.
   - Gom nhóm Title + Authors + Categories + Summary thành cột `text_for_embedding`.
   - Lọc trùng lặp `paper_id` bằng `df.drop_duplicates(subset=["paper_id"], keep="first")` và loại bỏ dòng rỗng.
2. **Corruption**:
   - Xóa 3 bản ghi bài báo mới nhất (Drop latest).
   - Xóa rỗng summary của 2 bài báo (Blank summary).
   - Chèn ký tự nhiễu rác `[NOISE_CORRUPTED_TEXT...]` vào summary.
   - Cắt ngắn tiêu đề bài báo xuống 5 ký tự (Truncate title).
   - Lùi ngày xuất bản về năm 2024 (Stale date > 180 ngày).
   - Nhân bản dòng trùng lặp `paper_id` (Add duplicates).
   - Ghi nhật ký vào `corruption_log.json`.

### Input, output và contract

| Thành phần | Mô tả |
| :--- | :--- |
| **Input** | `records: list[PaperRecord]`, `run_date: datetime` |
| **Output** | `pd.DataFrame` chứa `text_for_embedding`, `age_days`, `summary_chars`,... |
| **Module phụ thuộc** | `src/ingestion/crossref.py` (`PaperRecord`), `src/core/utils.py` |
| **Module sử dụng output** | `src/retrieval/index.py` (Người 4), `src/observability/quality.py` (Người 5), `src/pipelines/` (Người 1) |
| **Điều kiện lỗi cần xử lý** | Chuỗi ngày hỏng, tiêu đề rỗng, summary bị null hoặc trắng. |

### Cách xác minh

```bash
./uv run pytest tests/test_cleaning.py tests/test_corruption.py -v
```

- **Kết quả mong đợi:** 100% test cases pass, dữ liệu clean không còn rác hoặc trùng lặp, dataset corrupted sinh ra đủ 6 dạng lỗi.
- **Kết quả thực tế:** Tất cả unit tests đều **PASSED**.
- **Artifact/log:** `data/clean/papers_clean.json`, `data/results/corruption_log.json`.

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Quyết định cách tổng hợp các trường thông tin bài báo vào cột `text_for_embedding` để nạp vào ChromaDB.
- **Các phương án đã cân nhắc:**
  1. *Phương án A*: Chỉ embed duy nhất trường `summary` (Abstract).
  2. *Phương án B*: Embed từng trường riêng biệt (`title`, `summary`, `authors`) thành các vector độc lập.
  3. *Phương án C*: Gom nhóm có nhãn cấu trúc: `Title: ... \n Authors: ... \n Categories: ... \n Summary: ...`
- **Phương án đã chọn:** **Phương án C**.
- **Lý do:** Phương án A làm mất thông tin tác giả và thể loại; Phương án B tốn gấp 3 lần chi phí truy vấn Vector DB. Phương án C giữ trọn vẹn ngữ nghĩa bài báo trong 1 vector duy nhất.
- **Bằng chứng quyết định phù hợp:** RAG Agent đạt **100.0% Retrieval Hit Rate** ở pha Baseline.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**  
  `ERROR: Package 'day10-data-observability-lab-student' requires a different Python: 3.14.4 not in '<3.14,>=3.11'`
- **Lệnh hoặc bước tái hiện:** `pip install -e .` trên hệ thống dùng Python 3.14.
- **Nguyên nhân gốc:** File `pyproject.toml` ban đầu đặt ràng buộc cứng `requires-python = ">=3.11,<3.14"`.
- **Cách xử lý:** Cập nhật `pyproject.toml` thành `requires-python = ">=3.11,<3.15"`, đồng thời tải trình quản lý `uv` (`./uv sync`) để quản lý virtual environment ổn định.
- **Cách xác minh sau khi sửa:** Run `./uv sync` và `./uv run pytest -v` thành công 100%.
- **Điều học được:** Cần kiểm tra kỹ ràng buộc phiên bản Python trong `pyproject.toml` và ưu tiên dùng `uv` để đồng bộ môi trường nhất quán.

---

## 7. Hiểu biết về luồng end-to-end

1. Dữ liệu thô thu thập từ **Crossref API** được lưu thành raw artifacts (`data/raw/`), qua `cleaning.py` làm sạch thành DataFrame, sau đó được **MiniLM** mã hóa thành vector embeddings và lưu vào **ChromaDB collection**.
2. **Evaluation set** (40 câu hỏi) chứa `ground_truth_doc_ids`. Khi Agent truy vấn, Evaluator đối chiếu tài liệu retrieve được xem có chứa ID trong `ground_truth_doc_ids` hay không để tính Hit Rate và F1.
3. **Quality checks** kiểm tra tính toàn vẹn tĩnh của dữ liệu (null rate, duplicate ID, blank text). **Freshness monitoring** kiểm tra tính thời sự động của dữ liệu dựa trên cột `age_days > 180`.
4. Phải dùng **cùng 1 test set cố định** cho 3 pha để đảm bảo biến độc lập duy nhất là *chất lượng dữ liệu*, giúp đo lường chính xác tác động của Data Corruption.
5. **Repair thành công** khi chỉ số Hit Rate phục hồi từ **60.0% ➔ 100.0%**, Judge Accuracy phục hồi từ **12.5% ➔ 52.5%** và Quality Gate chuyển từ `FAILED` về `PASSED`.

---

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| :--- | :---: | :---: | :---: | :--- |
| `retrieval_hit_rate` | **100.0%** | **60.0%** | **100.0%** | Dữ liệu lỗi khiến Hit Rate giảm 40%, repair phục hồi 100%. |
| `mean_token_f1` | **0.5778** | **0.1575** | **0.5778** | F1 giảm thảm hại do nhiễu và mất summary, phục hồi hoàn toàn sau repair. |
| `judge_accuracy` | **52.5%** | **12.5%** | **52.5%** | LLM trả lời sai khi thiếu ngữ cảnh, khôi phục khi data sạch. |
| `mean_judge_score` | **3.05** | **1.50** | **3.05** | Điểm số LLM sụt giảm một nửa ở pha Corrupted. |
| Quality checks | ✅ **PASSED** | ❌ **FAILED** | ✅ **PASSED** | Quality Gate phát hiện chính xác rác text và bài trùng lặp. |
| Freshness status | ✅ **FRESH** | ⚠️ **STALE** | ✅ **FRESH** | Freshness Gate cảnh báo bài báo cũ quá 180 ngày. |

### Kết luận từ số liệu

1. **[Data corruption]** (xóa bài mới, rỗng summary, chèn nhiễu) ➔ **[quality: FAILED & freshness: STALE]** ➔ **[Hit Rate giảm 40%, Judge Accuracy giảm từ 52.5% xuống 12.5%]**.
2. **[Repair action]** (re-ingest từ raw data & re-clean) ➔ **[quality: PASSED & freshness: FRESH]** ➔ **[Agent metrics phục hồi hoàn toàn 100% Hit Rate và 52.5% Accuracy]**.

- **Corruption ảnh hưởng rõ nhất**: **Blank Summary** và **Drop Latest Records** vì làm mất hoàn toàn ngữ nghĩa mà RAG Agent cần để tra cứu.

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất
1. **Garbage In = Garbage Out**: Chất lượng dữ liệu đầu vào quyết định 90% hiệu năng của RAG Agent.
2. **Tầm quan trọng của Observability Gates**: Phát hiện sớm sự cố dữ liệu ngay tại Pipeline trước khi ảnh hưởng người dùng.
3. **Data Provenance**: Lưu trữ dữ liệu thô nguyên bản (`data/raw/`) giúp hệ thống có khả năng tự phục hồi (Self-Healing) cực kỳ mạnh mẽ.

### Nếu có thêm thời gian
Tôi sẽ xây dựng cơ chế **Partial Incremental Repair** (chỉ sửa lại các dòng bị lỗi thay vì re-process toàn bộ dataset) để tối ưu thời gian chạy pipeline.

---

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** **Nguyễn Đăng Nam**  
**Ngày xác nhận:** `2026-08-06`
