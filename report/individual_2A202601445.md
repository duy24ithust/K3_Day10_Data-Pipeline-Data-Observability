# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| :--- | :--- |
| **Họ và tên** | **Đậu Quốc Duy** |
| **MSSV** | **2A202601445** |
| **Khóa/Lớp** | **K3** |
| **Tên nhóm** | **Nhóm B4** |
| **Vai trò chính** | **Pipeline Integrator & Leader (Người 1)** |
| **Repository** | `https://github.com/duy24ithust/K3_Day10_Data-Pipeline-Data-Observability.git` |
| **Ngày hoàn thành** | `2026-08-06` |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| :--- | :--- | :--- | :--- | :--- |
| **Baseline Pipeline Orchestration** | `src/pipelines/phase1.py` (`main`)<br>`script/run_phase1.py` | Project Settings, Raw Crossref Records | `data/results/baseline_metrics.json`<br>`data/reports/phase1_report.md` | **Hoàn thành** |
| **Corruption & Repair Flow Orchestration** | `src/pipelines/corruption_flow.py` (`main`)<br>`script/run_corruption_flow.py` | Baseline clean data, Corrupted data, Raw records | `data/results/corrupted_metrics.json`<br>`repaired_metrics.json`<br>`data/reports/corruption_report.md` | **Hoàn thành** |
| **Core Architecture & Settings Config** | `src/core/config.py`<br>`src/core/utils.py` | Environment variables, `.env` file | `Settings` dataclass, core utilities (`read_json`, `write_json`, `write_csv`) | **Hoàn thành** |
| **Release Management & Git Coordination** | Project repository | Multi-member branches & PRs | Clean codebase, full reproduction scripts, zero secret committed | **Hoàn thành** |

---

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| :--- | :--- | :--- |
| **Hỗ trợ Ingestion & Raw Lineage** | Người 2 (Ingestion Owner) / `src/ingestion/crossref.py` | Xác minh cơ chế retry/backoff khi dính rate limit và cấu hình lưu trữ raw responses nguyên bản. |
| **Hỗ trợ Cleaning & Corruption Integration** | Người 3 (Cleaning Owner) / `src/ingestion/cleaning.py` & `corruption.py` | Tích hợp hàm `build_clean_dataframe()` và `corrupt_clean_dataframe()` vào luồng pipeline điều phối chung. |
| **Hỗ trợ Vector Database Management** | Người 4 (RAG Owner) / `src/retrieval/index.py` | Đảm bảo 3 ChromaDB collections (`papers-baseline`, `papers-corrupted`, `papers-repaired`) được đặt tên và lưu vết riêng biệt. |
| **Hỗ trợ Data Observability Reporting** | Người 5 (Eval Owner) / `src/observability/reporting.py` | Tích hợp các bước sinh test set, đánh giá metrics, chạy quality checks và tự động xuất các báo cáo Markdown. |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| :--- | :--- | :--- | :--- |
| **Xây dựng luồng Baseline Pipeline End-to-End** | `src/pipelines/phase1.py`<br>`script/run_phase1.py` | Chạy tự động luồng Raw ➔ Clean ➔ Index ➔ Eval ➔ Report | `python script/run_phase1.py` |
| **Xây dựng luồng Corruption, Repair & Comparison** | `src/pipelines/corruption_flow.py`<br>`script/run_corruption_flow.py` | Chạy tự động luồng Corrupt ➔ Eval ➔ Repair ➔ Compare | `python script/run_corruption_flow.py` |
| **Quản lý cấu hình & Cấu trúc dự án** | `src/core/config.py`<br>`pyproject.toml` | Khung kiến trúc nhất quán, tự động hóa môi trường với `uv` | `./uv sync` & `./uv run pytest -v` |
| **Điều phối nhóm & Quản lý Release** | Repository Git | Đạt 100% tiêu chí 7 Checkpoints từ CP0 đến CP6 | Kiểm tra artifacts trong `data/` |

**Output cụ thể:**
Hệ thống điều phối pipeline tự động hóa toàn bộ luồng dữ liệu 2 pha. File `script/run_phase1.py` khởi tạo baseline đạt **100% Retrieval Hit Rate**. File `script/run_corruption_flow.py` chứng minh tác hại của dữ liệu xấu khiến Hit Rate giảm về **60.0%** và tự động kích hoạt cơ chế Repair phục hồi về **100.0%**, xuất báo cáo đối chiếu `data/reports/corruption_report.md`.

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Ghép nối các module độc lập (Ingestion, Cleaning, Indexing, Evaluation, Observability) thành một quy trình tự động hóa khép kín (End-to-End Pipeline Automation). Đảm bảo tính tái lập (reproducibility), quản lý tiến trình thử nghiệm qua các pha mà không làm ghi đè dữ liệu hay rò rỉ secret/API Key.

### Cách triển khai
1. **Phase 1 Baseline Orchestration (`phase1.py`)**:
   - Nạp cấu hình từ `Settings`.
   - Khởi tạo raw records từ `CrossrefFetcher`.
   - Gọi `build_clean_dataframe()` từ `cleaning.py` và lưu ra CSV/JSON trong `data/clean/`.
   - Nạp dataframe sạch vào ChromaDB collection `papers-baseline`.
   - Gọi `build_test_set()` sinh 40 câu hỏi kiểm thử.
   - Chạy `evaluate_pipeline()` tính toán các chỉ số Hit Rate, F1 Score, LLM Judge Score.
   - Kích hoạt `run_data_quality_checks()` & `build_freshness_report()`.
   - Xuất báo cáo tổng hợp `data/reports/phase1_report.md`.

2. **Phase 2 Corruption & Repair Orchestration (`corruption_flow.py`)**:
   - Nạp baseline clean dataframe.
   - Gọi `corrupt_clean_dataframe()` tạo dataset lỗi và ghi `corruption_log.json`.
   - Nạp dataset lỗi vào collection ChromaDB riêng biệt `papers-corrupted`.
   - Chạy đánh giá lại trên tập test set cũ để ghi nhận sự sụt giảm chỉ số.
   - Thực hiện **Repair** bằng cách load lại raw records từ `data/raw/crossref_records.json` và chạy lại luồng cleaning.
   - Nạp dataset đã repair vào collection `papers-repaired` và đánh giá lại.
   - Xuất báo cáo so sánh 3 trạng thái `data/reports/corruption_report.md`.

### Input, output và contract

| Thành phần | Mô tả |
| :--- | :--- |
| **Input** | `Settings` config, Raw Crossref response/records, Test set parameters |
| **Output** | Metrics JSON files (`baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json`), Markdown Reports |
| **Module phụ thuộc** | `src/ingestion/`, `src/retrieval/`, `src/evaluation/`, `src/observability/` |
| **Module sử dụng output** | Toàn bộ dự án, bộ công cụ demo dashboard, báo cáo nhóm |
| **Điều kiện lỗi cần xử lý** | Mất kết nối API, đứt file raw, lệch tên ChromaDB collection, rò rỉ API key |

### Cách xác minh

```bash
# 1. Chạy luồng Baseline Phase 1
python script/run_phase1.py

# 2. Chạy luồng Corruption & Repair Phase 2
python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** Cả 2 script chạy mượt mà end-to-end không phát sinh lỗi, sinh đầy đủ các file metrics, JSON quality và báo cáo Markdown.
- **Kết quả thực tế:** Tất cả các luồng đều chạy thành công 100%.
- **Artifact/log:** `data/reports/phase1_report.md`, `data/reports/corruption_report.md`.

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Quyết định cách thức quản lý bộ lưu trữ Vector DB (ChromaDB) giữa các pha thử nghiệm khác nhau.
- **Các phương án đã cân nhắc:**
  1. *Phương án A*: Dùng chung 1 collection duy nhất và xóa đi ghi đè lại sau mỗi pha.
  2. *Phương án B*: Tạo 3 collection riêng biệt được phân tách bằng tên độc lập: `papers-baseline`, `papers-corrupted`, `papers-repaired`.
- **Phương án đã chọn:** **Phương án B**.
- **Lý do:** Phương án A gây mất dấu vết dữ liệu, làm cho việc đối chiếu hoặc chạy lại đánh giá độc lập bị sai lệch. Phương án B đảm bảo tính phân tách không gian lưu trữ, minh bạch dữ liệu và cho phép kiểm thử lại bất kỳ lúc nào mà không sợ ảnh hưởng đến baseline.
- **Bằng chứng quyết định phù hợp:** Kết quả đối chiếu chỉ số giữa 3 pha được ghi nhận chính xác 100% trong `data/reports/corruption_report.md`.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**  
  `ModuleNotFoundError: No module named 'pipelines'` khi thực thi script từ thư mục gốc.
- **Lệnh hoặc bước tái hiện:** `python script/run_phase1.py` khi chưa cài gói `src` ở chế độ editable.
- **Nguyên nhân gốc:** Python interpreter không tự động nhận thư mục `src/` vào `sys.path` khi thực thi script con trong `script/`.
- **Cách xử lý:** Cấu hình `pyproject.toml` định nghĩa gói `src` chuẩn setuptools, bổ sung lệnh `pip install -e .` và hướng dẫn nhóm chạy nhất quán bằng `uv` (`./uv run python script/run_phase1.py`).
- **Cách xác minh sau khi sửa:** Chạy script trực tiếp từ bất kỳ thư mục nào cũng không còn bị dính lỗi thiếu module.
- **Điều học được:** Cần thiết lập đúng quy chuẩn đóng gói package Python (`pyproject.toml`) và quy định nhất quán câu lệnh thực thi cho tất cả các thành viên trong nhóm.

---

## 7. Hiểu biết về luồng end-to-end

1. Dữ liệu từ **Crossref API** được nạp thô vào `data/raw/`, qua `cleaning.py` làm sạch thành `data/clean/`, rồi qua `embeddings.py` và `index.py` chuyển thành các vector embeddings nạp vào **ChromaDB**.
2. **Evaluation set** (40 câu hỏi) giữ cố định `ground_truth_doc_ids`. Khi RAG Agent truy vấn, Evaluator đối chiếu kết quả retrieved với ground truth để đo đạc định lượng Hit Rate, F1 và LLM Judge Score.
3. **Data Quality Checks** kiểm tra tính toàn vẹn của dữ liệu (null, duplicate, blank summary). **Freshness Monitoring** theo dõi độ tươi dữ liệu dựa trên cột `age_days` so với ngưỡng 180 ngày.
4. Bắt buộc phải dùng **cùng 1 test set cố định** cho 3 pha để đảm bảo kết quả đo lường là một phép thử công bằng (controlled experiment), minh chứng biến động chỉ số hoàn toàn do chất lượng dữ liệu thay đổi.
5. **Repair thành công** khi các chỉ số RAG Agent khôi phục hoàn toàn từ trạng thái suy giảm (Hit Rate 60% ➔ 100%, Judge Accuracy 12.5% ➔ 52.5%) và Quality Gate khôi phục về `PASSED`.

---

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| :--- | :---: | :---: | :---: | :--- |
| `retrieval_hit_rate` | **100.0%** | **60.0%** | **100.0%** | Dữ liệu bị lỗi làm sụt giảm 40% khả năng truy vết tài liệu đúng. |
| `mean_token_f1` | **0.5778** | **0.1575** | **0.5778** | Chuỗi trả lời bị sai lệch nghiêm trọng khi dữ liệu chứa nhiễu/mất summary. |
| `judge_accuracy` | **52.5%** | **12.5%** | **52.5%** | LLM Judge đánh giá chất lượng câu trả lời bị tụt thảm hại ở pha Corrupted. |
| `mean_judge_score` | **3.05** | **1.50** | **3.05** | Điểm trung bình của LLM giảm xuống còn một nửa. |
| Quality checks | ✅ **PASSED** | ❌ **FAILED** | ✅ **PASSED** | Phát hiện chính xác các sự cố dữ liệu rác và trùng lặp bản ghi. |
| Freshness status | ✅ **FRESH** | ⚠️ **STALE** | ✅ **FRESH** | Kích hoạt cảnh báo khi xuất hiện bài báo bị lùi ngày quá 180 ngày. |

### Kết luận từ số liệu

1. **[Data corruption]** (xóa bài mới, rỗng summary, chèn nhiễu) ➔ **[quality: FAILED & freshness: STALE]** ➔ **[Retrieval Hit Rate tụt từ 100% xuống 60%, LLM Judge Accuracy tụt từ 52.5% xuống 12.5%]**.
2. **[Repair action]** (re-ingest từ raw records & re-clean) ➔ **[quality: PASSED & freshness: FRESH]** ➔ **[Toàn bộ chỉ số RAG Agent phục hồi hoàn toàn 100% Hit Rate và 52.5% Accuracy]**.

- **Corruption ảnh hưởng rõ nhất**: **Blank Summary** và **Drop Latest Records** vì làm mất hoàn toàn ngữ nghĩa mà RAG Agent cần để tìm kiếm context.

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất
1. **Pipeline Automation**: Việc tự động hóa luồng pipeline giúp tiết kiệm thời gian thử nghiệm và đảm bảo tính tái lập 100%.
2. **Garbage In = Garbage Out**: Hệ thống AI dù tiên tiến đến đâu cũng sẽ cho câu trả lời sai nếu dữ liệu đầu vào bị thoái hóa.
3. **Data Observability**: Cần cài đặt các cổng kiểm tra Data Quality & Freshness ngay trên Pipeline để chủ động phát hiện lỗi trước khi đến tay người dùng.

### Nếu có thêm thời gian
Tôi sẽ tích hợp công cụ theo dõi tự động CI/CD (GitHub Actions) để tự động chạy các bài kiểm tra Data Observability & Evaluation mỗi khi có dữ liệu mới được nạp vào.

---

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** **Đậu Quốc Duy**  
**Ngày xác nhận:** `2026-08-06`
