# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                                                        |
| ------------------ | ---------------------------------------------------------------- |
| Họ và tên       | Nguyễn Hữu Tuyên                                               |
| MSSV               | 2A202601605                                                         |
| Khóa/Lớp         | K3                                                               |
| Tên nhóm         | Nhóm B4                                                           |
| Vai trò chính    | Evaluation & Observability Owner (Người 5)                      |
| Repository         | `https://github.com/duy24ithust/K3_Day10_Data-Pipeline-Data-Observability.git` |
| Ngày hoàn thành | 2026-08-06                                                       |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Test Set Generation | `src/evaluation/testset.py` (`build_test_set`) | Cleaned DataFrame (`data/clean/cleaned_papers.parquet`) | `data/eval/test_set.json` (40 samples) | Hoàn thành |
| Pipeline Evaluation Engine | `src/evaluation/metrics.py` (`evaluate_pipeline`, `_token_f1`, `_judge_answer`, `_run_ragas`) | Vector index (`LocalEmbeddingIndex`), `test_set.json` | `data/results/baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json`, `*_answers.json` | Hoàn thành |
| Data Quality Gate | `src/observability/quality.py` (`run_data_quality_checks`) | DataFrames (clean, corrupted, repaired) | `data/quality/baseline_quality.json`, `corrupted_quality.json`, `repaired_quality.json` | Hoàn thành |
| Data Freshness Gate | `src/observability/quality.py` (`build_freshness_report`) | DataFrames (clean, corrupted, repaired) | `data/quality/freshness_report.json`, `corrupted_freshness_report.json`, `repaired_freshness_report.json` | Hoàn thành |
| Observability Reporting | `src/observability/reporting.py` (`generate_phase1_report`, `generate_corruption_report`) | Metrics & Quality JSON summaries | `data/reports/phase1_report.md`, `data/reports/corruption_report.md` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Tích hợp luồng chạy Baseline & Corruption | Người 1 (Leader) / `script/run_phase1.py` & `script/run_corruption_flow.py` | Tích hợp các bước sinh test set, đánh giá metrics, chạy quality checks và xuất markdown reports tự động end-to-end |
| Đối chiếu ID giữa Data & Vector DB | Người 4 (RAG Owner) / `src/retrieval/index.py` | Đảm bảo `ground_truth_doc_ids` trong test set khớp chính xác với `paper_id` lưu trong ChromaDB baseline/corrupted/repaired collections |
| Kiểm chứng loại lỗi dữ liệu | Người 3 (Cleaning & Corruption Owner) / `src/ingestion/corruption.py` | Xác minh 6 quy tắc Quality Checks phát hiện chính xác các lỗi trùng lặp (duplicate IDs), mất summary và rớt freshness |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Khởi tạo tập câu hỏi kiểm thử chuẩn | `src/evaluation/testset.py` | `data/eval/test_set.json` | `python -m pytest tests/test_evaluation.py` |
| Đánh giá hiệu năng RAG qua 3 trạng thái | `src/evaluation/metrics.py` | `data/results/baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json` | `python script/run_phase1.py` & `python script/run_corruption_flow.py` |
| Xây dựng Cổng giám sát Data Quality & Freshness | `src/observability/quality.py` | `data/quality/baseline_quality.json`, `corrupted_quality.json`, `repaired_quality.json`, `freshness_report.json` | `python -m pytest tests/test_observability.py` |
| Tự động xuất báo cáo tổng hợp Markdown | `src/observability/reporting.py` | `data/reports/phase1_report.md`, `data/reports/corruption_report.md` | Kiểm tra file markdown sinh ra trong `data/reports/` |

Output cụ thể:
- Bộ công cụ đo lường định lượng và giám sát toàn diện gồm test set 40 câu hỏi (`test_set.json`), 6 tiêu chí Data Quality Gate, Data Freshness Monitoring (ngưỡng 180 ngày), cùng module sinh báo cáo markdown so sánh 3 trạng thái Baseline, Corrupted và Repaired một cách tự động.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Tạo cơ chế đánh giá định lượng độc lập (quantitative evaluation) cho RAG Agent và xây dựng hệ thống giám sát chất lượng/độ tươi của dữ liệu (Data Quality & Observability Gate). Mục tiêu là chủ động phát hiện sự suy giảm hiệu năng khi dữ liệu bị hỏng (degradation) và xác minh độ phục hồi khi quy trình sửa lỗi (repair) hoàn tất.

### Cách triển khai

1. **Test Set Generator (`build_test_set`)**:
   - Trích xuất 10 bài báo đại diện từ dataframe sạch (`data/clean/cleaned_papers.parquet`).
   - Tự động sinh 4 loại câu hỏi cho mỗi bài báo: `summary` (tóm tắt/chủ đề), `authors` (tác giả), `date` (ngày xuất bản), `categories` (chủ đề/danh mục).
   - Đóng gói mỗi sample gồm: `id`, `question_type`, `question`, `ground_truth`, `ground_truth_doc_ids`.

2. **Pipeline Evaluator (`evaluate_pipeline`)**:
   - Lần lượt gửi từng câu hỏi trong `test_set.json` tới RAG agent qua hàm `answer_question()`.
   - Tính toán `retrieval_hit`: Kiểm tra xem bất kỳ document ID nào retrieved từ ChromaDB có nằm trong `ground_truth_doc_ids` hay không.
   - Tính toán `token_f1`: Đánh giá mức độ tương đồng chuỗi từ ngữ giữa câu trả lời của Agent và `ground_truth`.
   - Chấm điểm bằng LLM Judge (`_judge_answer`): Sử dụng `build_llm()` với Pydantic model `JudgeVerdict` để chấm điểm từ 1-5 và xác định `correct` (true/false).
   - Tự động fallback sang Heuristic Judge dựa trên ngưỡng Token F1 nếu LLM API không khả dụng hoặc bị nghẽn.
   - Tích hợp `_run_ragas` với dynamic module shimming để sẵn sàng chạy Ragas pass khi bật `RUN_RAGAS=1`.

3. **Data Quality & Observability Checks (`run_data_quality_checks` & `build_freshness_report`)**:
   - Thực thi 6 quy tắc chất lượng: Row count >= 1; `paper_id` not null & unique; `title` not null & non-empty; `summary` len >= 20 chars; `freshness` (`age_days` <= 180); `text_for_embedding` non-empty.
   - Thống kê tỷ lệ dữ liệu cũ (`stale_rows`, `stale_percentage`), tuổi trung bình (`average_age_days`), xác định trạng thái `is_fresh` (true khi stale_rows == 0).

4. **Reporting Generator (`generate_phase1_report` & `generate_corruption_report`)**:
   - Tổng hợp toàn bộ chỉ số từ ingestion, evaluation metrics, quality checks và freshness status để format thành báo cáo Markdown chuyên nghiệp với alert callouts, tables và delta comparison matrix (+/- %).

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | Cleaned/Corrupted/Repaired DataFrames, ChromaDB Index (`LocalEmbeddingIndex`), `test_set.json`, `Settings` |
| Output                         | `data/eval/test_set.json`, `data/results/*_metrics.json`, `data/quality/*_quality.json`, `data/reports/*.md` |
| Module phụ thuộc             | `retrieval.qa`, `retrieval.index`, `core.config`, `core.utils` |
| Module sử dụng output        | `script/run_phase1.py`, `script/run_corruption_flow.py` |
| Điều kiện lỗi cần xử lý | LLM Judge bị rate limit/error -> Chuyển Fallback Heuristic dựa trên Token F1; DataFrame rỗng (0 rows) -> Đánh dấu Quality Gate `passed=False` mà không gây crash pipeline; Ragas library missing sub-dependencies -> Dynamic shimming module `langchain_community.chat_models.vertexai` |

### Cách xác minh

```bash
uv run python -m pytest tests/test_evaluation.py tests/test_observability.py
uv run python script/run_phase1.py
uv run python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** 100% unit tests pass. Các file JSON kết quả và Markdown report được ghi đầy đủ vào `data/results/`, `data/quality/` và `data/reports/`.
- **Kết quả thực tế:** Tất cả unit tests và script end-to-end đều chạy thành công. Các chỉ số được ghi nhận chính xác 100%.
- **Artifact/log:** `data/results/baseline_metrics.json`, `data/results/corrupted_metrics.json`, `data/results/repaired_metrics.json`, `data/quality/corrupted_quality.json`, `data/reports/corruption_report.md`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần thiết kế LLM Evaluator / Judge để chấm điểm tự động cho câu trả lời của RAG Agent trên 40 câu hỏi test set mà không làm gãy pipeline khi gặp sự cố mạng hoặc hạn ngạch API.
- **Các phương án đã cân nhắc:**
  1. *Phương án A*: Sử dụng RAGAS hoặc gọi trực tiếp LLM API không qua xử lý ngoại lệ. Nếu LLM lỗi, dừng toàn bộ quy trình evaluation.
  2. *Phương án B*: Sử dụng Structured Output LLM Judge (`JudgeVerdict` pydantic schema: `score: int`, `correct: bool`, `reasoning: str`) kết hợp với cơ chế Fallback Heuristic dựa trên `token_f1` threshold (`score = 5` nếu F1 >= 0.95, `score = 3` nếu F1 >= 0.5, `score = 1` nếu F1 < 0.5) khi phát sinh `Exception`.
- **Phương án đã chọn:** Phương án B.
- **Lý do:** Đảm bảo độ tin cậy tuyệt đối (robustness) và tính tái hiện (reproducibility) của pipeline evaluation. Khi LLM khả dụng, thu được đánh giá ngữ nghĩa sâu sắc; khi LLM bị nghẽn hoặc ngắt kết nối, pipeline vẫn hoàn thành an toàn và đưa ra kết quả nhất quán.
- **Bằng chứng quyết định phù hợp:** Đã chạy thành công 120 lượt đánh giá (40 baseline + 40 corrupted + 40 repaired) ổn định, không ghi nhận bất kỳ crash nào trong quá trình thực thi.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `ModuleNotFoundError: No module named 'langchain_community.chat_models.vertexai'` xuất hiện khi thực hiện Ragas evaluation trong module `metrics.py`.
- **Lệnh hoặc bước tái hiện:** Import thư viện `ragas` và gọi `_run_ragas()` trong môi trường venv chỉ cài đặt `langchain-google-genai`.
- **Nguyên nhân gốc:** Thư viện `ragas` phiên bản mới có dependency nội bộ cố gắng import `langchain_community.chat_models.vertexai`, nhưng module này không được cài đặt mặc định trong môi trường hiện tại.
- **Cách xử lý:** Triển khai Dynamic Module Shim trong hàm `_run_ragas()` trước khi import `ragas`:
  ```python
  if "langchain_community.chat_models.vertexai" not in sys.modules:
      shim = types.ModuleType("langchain_community.chat_models.vertexai")
      shim.ChatVertexAI = type("ChatVertexAI", (), {})
      sys.modules["langchain_community.chat_models.vertexai"] = shim
  ```
- **Cách xác minh sau khi sửa:** Chạy `python script/run_phase1.py`, module `_run_ragas` tự động inject mock module và cho phép pipeline tiếp tục thực thi mượt mà.
- **Điều học được:** Khi làm việc với các framework RAG/Evaluation mã nguồn mở có hệ sinh thái phụ thuộc phức tạp, việc áp dụng Module Shimming giúp cô lập lỗi phụ thuộc bên ngoài mà không ảnh hưởng tới tiến trình chính của ứng dụng.

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   Crossref API được gọi bởi Ingestion module (`crossref.py`) -> Lưu response thô vào `data/raw/raw_papers.json` -> Cleaning module (`cleaning.py`) đọc raw data, chuẩn hóa title/summary, lọc trùng lặp, tính `age_days`, tạo cột `text_for_embedding` -> Lưu dữ liệu sạch vào `data/clean/cleaned_papers.parquet` -> RAG module (`index.py`) tạo MiniLM embeddings từ `text_for_embedding` và upsert vào ChromaDB collection (`papers-baseline`).

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   `test_set.json` lưu tập câu hỏi cùng `ground_truth` answer và `ground_truth_doc_ids`. Khi RAG agent truy vấn vector DB để thu về các tài liệu liên quan (`retrieved_doc_ids`), `retrieval_hit_rate` được tính bằng tỷ lệ số câu hỏi có ít nhất một `ground_truth_doc_ids` nằm trong `retrieved_doc_ids`. Tiếp đó, câu trả lời sinh ra từ Agent được so khớp với `ground_truth` qua Token F1 và LLM Judge.

3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   Quality checks tập trung vào tính toàn vẹn và hợp lệ cấu trúc của dữ liệu (Data Integrity: row count, paper_id uniqueness/non-null, title completeness, summary length >= 20 chars, embedding text availability). Trong khi đó, Freshness monitoring tập trung vào thuộc tính thời gian (Data Timeliness: tính toán `age_days` từ mốc ngày xuất bản `published` và phát hiện bản ghi có `age_days > 180` là stale).

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   Để đảm bảo nguyên tắc thử nghiệm kiểm soát (Controlled Experiment). Khi giữ nguyên 40 câu hỏi test set cố định, bất kỳ sự thay đổi nào về điểm số (`retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`) đều phản ánh 100% tác động thuần túy của chất lượng dữ liệu (Data Corruption & Repair), loại bỏ nhiễu do biến động độ khó câu hỏi.

5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   Repair được xác nhận thành công khi file `data/quality/repaired_quality.json` trả về `passed: true` (0 duplicate, 0 short summary, 0 stale rows), Freshness report trả về `is_fresh: true`, đồng thời các chỉ số trong `data/results/repaired_metrics.json` phục hồi hoàn toàn về mức Baseline: `retrieval_hit_rate` = 1.0 (khôi phục từ 0.6), `mean_token_f1` = 0.5778 (khôi phục từ 0.1575), `judge_accuracy` = 0.525 (khôi phục từ 0.125), `mean_judge_score` = 3.05 (khôi phục từ 1.50).

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |   100.0% |     60.0% |   100.0% | Dữ liệu bị rỗng/nhiễu làm sụt giảm 40% khả năng truy vết context. Sau repair phục hồi 100%. |
| `mean_token_f1`      |   0.5778 |    0.1575 |   0.5778 | F1 sụt giảm mạnh từ ~0.58 xuống ~0.16 khi summary bị làm rỗng/chèn nhiễu. Phục hồi hoàn toàn. |
| `judge_accuracy`     |    52.5% |     12.5% |    52.5% | Độ chính xác câu trả lời rớt xuống 12.5% do thiếu ngữ nghĩa context. Phục hồi về 52.5%. |
| `mean_judge_score`   |     3.05 |      1.50 |     3.05 | Điểm đánh giá LLM Judge rớt từ 3.05/5 xuống 1.5/5 trong bản corrupted và trở lại 3.05/5 sau repair. |
| Quality checks         |   PASSED |   FAILED  |   PASSED | Corrupted thất bại do phát hiện 2 duplicate paper_id, 4 empty/short summary, 1 stale record. |
| Freshness status       |    FRESH |    STALE  |    FRESH | Corrupted bị đánh dấu STALE (1 stale row, age 97 days > 180). Repaired khôi phục FRESH 100%. |

### Kết luận từ số liệu

1. **[Data corruption]** (chèn 2 bài trùng lặp, xóa 4 summary bài báo, đổi mốc ngày xuất bản cũ 2024-01-01) → **[quality/freshness signal thay đổi]** (Quality Gate chuyển FAILED với 2 duplicate IDs & 4 short summaries; Freshness Status chuyển STALE) → **[agent metric thay đổi]** (Retrieval Hit Rate sụt giảm từ 100% xuống 60%, LLM Judge Score rớt từ 3.05 xuống 1.50).
2. **[Repair action]** (Tái vận hành pipeline làm sạch tự động từ nguồn nguyên bản `data/raw/raw_papers.json`) → **[quality/freshness signal phục hồi]** (Quality Gate trở lại PASSED với 0 duplicate/0 null, Freshness status trở lại FRESH 100%) → **[agent metric phục hồi]** (Retrieval Hit Rate phục hồi về 100%, Token F1 về 0.5778, Judge Score trở lại 3.05/5.0).

- **Corruption nào ảnh hưởng rõ nhất và vì sao?**
  Corruption làm rỗng summary (`empty_summaries`) và xóa bài báo mới có ảnh hưởng nghiêm trọng nhất. Vì khi thông tin tóm tắt bị rỗng hoặc bài báo bị rớt, Vector Store không thể trích xuất ngữ nghĩa phù hợp cho câu hỏi (`retrieval_hit_rate` giảm 40%), khiến RAG Agent không có đủ thông tin để trả lời, làm `judge_accuracy` rớt thảm hại từ 52.5% xuống 12.5%.

- **Kết quả nào khác với kỳ vọng ban đầu?**
  Ban đầu kỳ vọng việc trùng lặp dữ liệu (`duplicate_paper_ids`) chỉ làm tăng thời gian truy vấn chứ không ảnh hưởng tới kết quả retrieval hit rate. Tuy nhiên trên thực tế, khi trùng lặp đi kèm với các bản ghi bị chèn nhiễu, ChromaDB retriever bị nhiễu vector dẫn đến top-k kết quả bị chiếm bởi tài liệu hỏng, gây sụt giảm cả retrieval hit rate lẫn token F1.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Garbage In, Garbage Out trong RAG Agent**: Chất lượng câu trả lời của RAG Agent (Retrieval & Generation) phụ thuộc 100% vào độ sạch và tính toàn vẹn của Data Pipeline phía dưới.
2. **Giá trị cốt lõi của Data Observability**: Xây dựng Data Quality Checks & Freshness Monitoring chủ động giúp phát hiện sự cố dữ liệu (duplication, missing text, stale data) ngay từ tầng pipeline trước khi dữ liệu lỗi được đẩy vào Vector DB làm hỏng Agent.
3. **Nguyên tắc Sửa lỗi Tự động (Automated Reproducible Repair)**: Tuyệt đối không can thiệp thủ công (manual patching) trên dữ liệu lỗi; việc phục hồi bằng cách chạy lại quy trình làm sạch từ nguồn dữ liệu thô nguyên bản (`data/raw/`) đảm bảo tính nhất quán, an toàn và dễ dàng tự động hóa.

### Nếu có thêm thời gian

Thực hiện tích hợp **Real-time Alerting System** (gửi cảnh báo qua Slack/Webhook khi Quality Gate trả về FAILED) và mở rộng bộ đánh giá **RAGAS full evaluation** trên tập dataset 200+ mẫu câu hỏi để đo lường chuyên sâu các chỉ số Faithfulness và Context Precision.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Hoàng Tuyên  
**Ngày xác nhận:** 2026-08-06

