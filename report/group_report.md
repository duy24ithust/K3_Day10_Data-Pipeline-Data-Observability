# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
| :--- | :--- |
| **Khóa/Lớp** | **K3** |
| **Tên nhóm** | **Nhóm B4** |
| **Repository** | `https://github.com/duy24ithust/K3_Day10_Data-Pipeline-Data-Observability.git` |
| **Ngày hoàn thành** | `2026-08-06` |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | :--- | :--- | :--- | :--- |
| 1 | **Đậu Quốc Duy** | `2A202601445` | Pipeline Leader (Người 1) | `src/pipelines/phase1.py`, `corruption_flow.py`, `script/` |
| 2 | **Lê Chí Anh Tuấn** | `2A202601149` | Ingestion Owner (Người 2) | `src/ingestion/crossref.py`, `data/raw/` |
| 3 | **Nguyễn Đăng Nam** | `2A202601307` | Cleaning & Corruption Owner (Người 3) | `src/ingestion/cleaning.py`, `corruption.py`, `data/clean/` |
| 4 | **Tống Nguyễn Minh Khang** | `2A202601101` | RAG & Vector DB Owner (Người 4) | `src/retrieval/index.py`, `agent.py`, `data/embeddings/` |
| 5 | **Nguyễn Hữu Tuyên** | `2A202601605` | Eval & Observability Owner (Người 5) | `src/evaluation/`, `src/observability/`, `data/reports/` |

---

## 2. Tóm tắt kết quả

Nhóm B4 đã hoàn thành 100% mục tiêu bài lab xây dựng và vận hành Data Pipeline khép kín cho hệ thống RAG qua 7 Checkpoints (CP0 đến CP6). Ở pha Baseline, pipeline tự động nạp 24 bản ghi thô từ Crossref API, làm sạch và đóng gói trường `text_for_embedding`, lưu trữ vào ChromaDB collection `papers-baseline` và đánh giá trên tập kiểm thử 40 câu hỏi cố định (`test_set.json`). Kết quả Baseline đạt hiệu năng cao: **Retrieval Hit Rate = 100.0%**, **Mean Token F1 = 0.5778**, **LLM Judge Accuracy = 52.5%** với 100% Quality Check PASSED và Freshness Status là FRESH.

Ở pha Data Corruption, nhóm đã giả lập 6 dạng sự cố dữ liệu thực tế (Drop bài mới nhất, Blank summary, Inject noise, Truncate title, Stale date, Add duplicate rows). Sự cố dữ liệu đã gây tác hại nghiêm trọng: **Hit Rate sụt giảm xuống còn 60.0%** (giảm 40%), **LLM Judge Accuracy sụt giảm xuống còn 12.5%** (giảm 40%), đồng thời kích hoạt cảnh báo Data Quality Gate báo ❌ **FAILED** và Freshness Gate báo ⚠️ **STALE**.

Ở pha Repair, hệ thống dựa vào tính truy vết nguồn gốc (Data Provenance) đã nạp lại dữ liệu thô nguyên bản từ `data/raw/crossref_records.json` và thực hiện làm sạch tự động. Kết quả phục hồi hoàn toàn: Hit Rate trở lại **100.0%** và Judge Accuracy khôi phục về **52.5%**, chứng minh sức mạnh của quy trình tự phục hồi (Self-Healing) và Data Observability.

---

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref REST API
    -> raw response/raw records (data/raw/)
    -> cleaning và data modeling (data/clean/)
    -> MiniLM embedding + ChromaDB index (papers-baseline)
    -> evaluation baseline (data/results/baseline_metrics.json)
    -> quality và freshness reports (data/quality/)
    -> corruption simulation (data/results/corruption_log.json)
    -> re-index và re-evaluate (papers-corrupted)
    -> repair từ dữ liệu nguồn thô (papers-repaired)
    -> comparison report (data/reports/corruption_report.md)
```

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output/artifact | Owner |
| :--- | :--- | :--- | :--- | :--- |
| **Ingestion** | Crossref REST API, `Settings` | Fetch, retry/backoff, parse payload | `data/raw/crossref_response.json`, `crossref_records.json` | Lê Chí Anh Tuấn |
| **Cleaning** | `data/raw/crossref_records.json` | Normalize text, parse `published`, tính `age_days`, ghép `text_for_embedding`, dedupe | `data/clean/papers_clean.csv`, `papers_clean.json` | Nguyễn Đăng Nam |
| **Embedding/index** | Cleaned DataFrame | MiniLM vectorization, lưu trữ ChromaDB collections | `data/embeddings/papers_embeddings.json`, ChromaDB collections | Tống Nguyễn Minh Khang |
| **Evaluation** | Cleaned DataFrame, Vector Index | Sinh 40 test samples, tính Hit Rate, Token F1, LLM Judge Score | `data/eval/test_set.json`, `data/results/*_metrics.json` | Nguyễn Hữu Tuyên |
| **Observability** | Clean/Corrupted/Repaired DataFrames | Data Quality rules, Freshness monitoring, Markdown reporting | `data/quality/*_quality.json`, `data/reports/*.md` | Nguyễn Hữu Tuyên |
| **Corruption/repair** | Cleaned DataFrame, Raw records | Giả lập 6 dạng lỗi, rebuild embed, repair từ raw data | `data/results/corruption_log.json`, `papers_clean_corrupted.csv` | Nguyễn Đăng Nam |
| **Orchestration** | Cấu hình dự án, các modules | Ghép nối luồng end-to-end Phase 1 & Phase 2 | `script/run_phase1.py`, `script/run_corruption_flow.py` | Đậu Quốc Duy |

---

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình | Giá trị sử dụng |
| :--- | :--- |
| `LLM_PROVIDER` | `gemini` (hỗ trợ cả `openai`, `anthropic`, `openrouter`, `ollama`) |
| `LLM_MODEL` | `gemini-2.5-flash` |
| **Embedding model** | `sentence-transformers/all-MiniLM-L6-v2` |
| **Số lượng Crossref records** | `24` bản ghi sạch (456 bản ghi thô tổng cộng) |
| **Retrieval `top_k`** | `3` |
| **Freshness threshold** | `180` ngày |
| **Random seed** | `42` |

### Lệnh cài đặt

Cài đặt môi trường bằng `uv` (khuyến nghị):
```bash
./uv sync
```

Hoặc dùng `pip` với môi trường ảo:
```bash
python -m pip install -e .
```

### Lệnh chạy

**1. Baseline Pipeline (Phase 1):**
```bash
python script/run_phase1.py
```

**2. Corruption & Repair Flow (Phase 2):**
```bash
python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng |
| :--- | :--- | :--- | :--- |
| **Baseline pipeline** | **Thành công 100%** | `2026-08-06 03:37:50 UTC` | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` |
| **Corruption flow** | **Thành công 100%** | `2026-08-06 03:47:14 UTC` | `data/results/corruption_log.json`, `data/reports/corruption_report.md` |

---

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính | Giá trị |
| :--- | :--- |
| **Source** | `https://api.crossref.org/works` |
| **Query/filter** | `query=agentic+retrieval+augmented+generation+large+language+model`, `from-pub-date:2026-02-07` |
| **Thời điểm lấy dữ liệu** | `2026-08-06` |
| **Số record nhận được** | `24` bản ghi lọc chuẩn (từ 456 bài thô) |
| **Cơ chế retry/backoff** | Exponential backoff hỗ trợ các mã HTTP `429`, `500`, `502`, `503`, `504` |

### Raw và clean schema

| Trường | Kiểu dữ liệu | Bắt buộc? | Ý nghĩa | Xử lý khi thiếu/sai |
| :--- | :--- | :---: | :--- | :--- |
| `paper_id` | `str` | **Có** | Mã định danh DOI ổn định duy nhất của bài báo | Loại bỏ bản ghi nếu rỗng hoặc trùng |
| `title` | `str` | **Có** | Tiêu đề bài báo | Normalize whitespace, drop nếu rỗng |
| `summary` | `str` | **Có** | Abstract/Tóm tắt nội dung | Normalize whitespace, drop nếu rỗng |
| `authors` | `list[str]` | Không | Danh sách tên tác giả | Chuyển thành chuỗi `authors_joined` |
| `categories` | `list[str]` | Không | Danh mục thể loại bài báo | Chuyển thành chuỗi `categories_joined` |
| `published` | `str` | **Có** | Ngày xuất bản (YYYY-MM-DD) | Parse datetime, tính `age_days` |
| `text_for_embedding` | `str` | **Có** | Văn bản tổng hợp ghép Title + Authors + Categories + Summary | Rebuild tự động khi cleaning/repair |

### Quy tắc cleaning

| Quy tắc | Quality dimension | Số record bị tác động | Cách xác minh |
| :--- | :--- | --: | :--- |
| Lọc bỏ bản ghi có `title` rỗng | `Completeness` | 0 | `data/quality/baseline_quality.json` |
| Lọc bỏ bản ghi có `summary` rỗng | `Completeness` | 0 | `data/quality/baseline_quality.json` |
| Khử trùng lặp theo `paper_id` | `Uniqueness` | 0 | `data/quality/baseline_quality.json` |
| Chuẩn hóa khoảng trắng & HTML tags | `Validity` | 24 | `data/clean/papers_clean.csv` |

**Cách tạo `text_for_embedding`, `paper_id` và `age_days`**:
- `paper_id`: Lấy nguyên bản từ DOI chuẩn của Crossref (ví dụ: `10.47576/2949-1894.2026.7.7.023`).
- `age_days`: Parse chuỗi ngày `published` thành `datetime` và tính khoảng cách số ngày so với `run_date`.
- `text_for_embedding`: Ghép nối có cấu trúc theo dạng:
  ```text
  Title: {title}
  Authors: {authors_joined}
  Categories: {categories_joined}
  Summary: {summary}
  ```

---

## 6. Evaluation setup

| Thành phần | Cấu hình thực tế |
| :--- | :--- |
| **Số câu hỏi** | `40` samples |
| **Các `question_type`** | `summary`, `authors`, `date`, `categories` |
| **Ground-truth document ID** | Trỏ trực tiếp đến `paper_id` của bài báo chứa thông tin |
| **Embedding model** | `sentence-transformers/all-MiniLM-L6-v2` |
| **Vector store/collection** | ChromaDB collections: `papers-baseline`, `papers-corrupted`, `papers-repaired` |
| **Retrieval `top_k`** | `3` |
| **LLM provider/model** | `gemini` / `gemini-2.5-flash` |
| **Test set dùng chung** | `data/eval/test_set.json` |

**Giải thích lý do giữ nguyên test set**:
Việc giữ nguyên tập `test_set.json` cho cả 3 pha (Baseline, Corrupted, Repaired) là bắt buộc để đảm bảo biến độc lập duy nhất trong thực nghiệm là *chất lượng dữ liệu*. Phép so sánh chỉ số đo lường giữa các pha mới có ý nghĩa khoa học và khách quan.

---

## 7. Kết quả baseline

### Artifact checklist

| Artifact | Đường dẫn thực tế | Trạng thái | Ghi chú |
| :--- | :--- | :---: | :--- |
| **Raw response/records** | `data/raw/` | **Có** | `crossref_response.json`, `crossref_records.json` |
| **Cleaned dataset** | `data/clean/` | **Có** | `papers_clean.csv`, `papers_clean.json` |
| **Embedding index** | `data/embeddings/` | **Có** | `papers_embeddings.json`, ChromaDB collection |
| **Evaluation set** | `data/eval/` | **Có** | `test_set.json` (40 samples) |
| **Baseline metrics** | `data/results/baseline_metrics.json` | **Có** | Hit Rate: 1.0, Token F1: 0.5778 |
| **Quality/freshness** | `data/quality/` | **Có** | `baseline_quality.json`, `freshness_report.json` |
| **Baseline report** | `data/reports/phase1_report.md` | **Có** | Xuất báo cáo Markdown Phase 1 hoàn chỉnh |

### Baseline metrics

| Metric | Giá trị | Diễn giải |
| :--- | --: | :--- |
| `retrieval_hit_rate` | **100.0%** | 100% câu hỏi tìm kiếm đúng tài liệu ngữ cảnh trong Top-3 |
| `mean_token_f1` | **0.5778** | Độ trùng khớp từ vựng giữa câu trả lời Agent và Ground Truth |
| `judge_accuracy` | **52.5%** | Tỷ lệ câu trả lời được LLM Judge chấm đạt yêu cầu đúng đắn |
| `mean_judge_score` | **3.05 / 5.0** | Điểm số chất lượng trung bình của LLM Judge |
| **Ragas** | *Skipped* | Bỏ qua để tối ưu thời gian chạy (chuyển `RUN_RAGAS=1` để bật) |

---

## 8. Data quality và freshness

### Quality checks

| Check | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline | Bằng chứng |
| :--- | :--- | :--- | :--- | :--- |
| **Row Count Gate** | `Completeness` | `count >= 1` | **PASS** (`24` records) | `data/quality/baseline_quality.json` |
| **paper_id Uniqueness** | `Uniqueness` | `nulls == 0, dups == 0` | **PASS** (0 nulls, 0 dups) | `data/quality/baseline_quality.json` |
| **Title Completeness** | `Completeness` | `missing_titles == 0` | **PASS** (0 missing) | `data/quality/baseline_quality.json` |
| **Summary Quality** | `Completeness` | `blank_summaries == 0` | **PASS** (0 blank) | `data/quality/baseline_quality.json` |
| **Embedding Field** | `Validity` | `missing_embed == 0` | **PASS** (0 missing) | `data/quality/baseline_quality.json` |

### Freshness

| Thuộc tính | Giá trị |
| :--- | :--- |
| **Freshness được đo tại** | Cleaned Dataset `data/clean/papers_clean.json` |
| **Timestamp mới nhất** | `2026-08-01` |
| **Ngưỡng freshness** | `180` ngày |
| **Trạng thái baseline** | **✅ FRESH** |
| **Lý do** | 0/24 bài báo bị cũ quá 180 ngày (Tuổi trung bình: 76.6 ngày) |

---

## 9. Corruption scenarios và repair

| Corruption | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair |
| :--- | :--- | --: | :--- | :--- | :--- |
| **Drop Latest Records** | Xóa 3 bài mới nhất | 3 | Row count giảm | Mất thông tin thời sự, Hit Rate sụt giảm | Fetch/load lại từ raw data |
| **Blank Summary** | Xóa rỗng summary | 2 | Summary Quality FAIL | Agent thiếu context, F1 giảm thảm hại | Re-clean lại từ raw records |
| **Inject Noise** | Chèn rác `[NOISE_GARBAGE...]` | 1 | Text Validity suy giảm | Làm sai lệch kết quả Embeddings | Re-clean lại từ raw records |
| **Truncate Title** | Cắt tiêu đề còn 5 ký tự | 1 | Title Completeness suy giảm | Agent không nhận diện được tiêu đề | Re-clean lại từ raw records |
| **Stale Date** | Lùi ngày xuất bản về 2024 | 1 | Freshness Status: **STALE** | Cảnh báo bài cũ > 180 ngày | Re-clean lại từ raw records |
| **Add Duplicates** | Nhân bản 2 dòng dữ liệu | 2 | Uniqueness Check **FAIL** | Xuất hiện `paper_id` trùng lặp | Deduplicate lại trong clean flow |

**Corruption log**:
- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: **Có**
- Nhận xét: Log ghi nhận đầy đủ 6 loại corruption, số lượng bản ghi và danh sách `paper_ids` bị tác động.

**Giải thích cách repair**:
Quy trình Repair không sửa tay kết quả JSON mà thực hiện **Re-ingest & Re-clean** tự động từ file dữ liệu thô nguyên bản `data/raw/crossref_records.json`. Điều này đảm bảo tính truy vết nguồn gốc (Data Provenance) và tính khách quan của phép thử.

---

## 10. So sánh baseline, corrupted và repaired

| Metric/signal | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét |
| :--- | --: | --: | --: | --: | --: | :--- |
| `retrieval_hit_rate` | **100.0%** | **60.0%** | **100.0%** | ⬇️ `-40.0%` | ⬆️ `+40.0%` | Dữ liệu hỏng làm mất thông tin truy vết |
| `mean_token_f1` | **0.5778** | **0.1575** | **0.5778** | ⬇️ `-0.4203` | ⬆️ `+0.4203` | F1 sụt thảm hại khi mất summary & chèn nhiễu |
| `judge_accuracy` | **52.5%** | **12.5%** | **52.5%** | ⬇️ `-40.0%` | ⬆️ `+40.0%` | LLM trả lời sai khi thiếu ngữ cảnh đúng |
| `mean_judge_score` | **3.05** | **1.50** | **3.05** | ⬇️ `-1.55` | ⬆️ `+1.55` | Điểm số đánh giá trung bình giảm một nửa |
| **Quality checks** | ✅ **PASS** | ❌ **FAIL** | ✅ **PASS** | Báo động rác & trùng | Phục hồi PASSED 100% |
| **Freshness status** | ✅ **FRESH** | ⚠️ **STALE** | ✅ **FRESH** | Cảnh báo bài cũ | Phục hồi FRESH 100% |

**Hai kết luận có quan hệ nhân quả**:
1. `Data Corruption` (Xóa bài mới, rỗng summary, chèn nhiễu) ➔ `Quality Gate FAILED & Freshness STALE` ➔ `Retrieval Hit Rate sụt 40%, Judge Accuracy sụt từ 52.5% xuống 12.5%`.
2. `Repair Action` (Re-ingest từ raw records & Re-clean) ➔ `Quality Gate PASSED & Freshness FRESH` ➔ `Retrieval Hit Rate & Judge Accuracy phục hồi 100% về mức Baseline`.

---

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Khi cài đặt gói qua `pip install -e .` trên Python 3.14 bị báo lỗi không tương thích phiên bản (`Requires-Python <3.14`).
- **Nguyên nhân:** File `pyproject.toml` ban đầu giới hạn `requires-python = ">=3.11,<3.14"`.
- **Cách xử lý:** Mở rộng ràng buộc trong `pyproject.toml` thành `requires-python = ">=3.11,<3.15"`, đồng thời chuẩn hóa quản lý venv và cài đặt thư viện cho cả nhóm bằng `uv` (`./uv sync`).
- **Cách xác minh:** Chạy `./uv sync` và `./uv run pytest -v` thành công 100% trên máy tất cả thành viên.

---

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện có thể kiểm chứng |
| :--- | :--- | :--- |
| Quy trình Repair chạy làm sạch lại toàn bộ dataset | Tốn thời gian xử lý khi dataset lớn | Triển khai cơ chế **Partial Incremental Repair** chỉ làm sạch các dòng lỗi |
| Đánh giá LLM Judge phụ thuộc vào API LLM ngoài | Tốn chi phí API và thời gian gọi mạng | Sử dụng Small Local Model (như Ollama/Qwen2.5) cho bước chấm điểm |

---

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm B4 và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế của 5 thành viên.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set (`test_set.json`).
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [x] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng (`individual_<MSSV>.md`).
- [x] Không có `.env`, API key, token hoặc secret trong repository, report hoặc log.
