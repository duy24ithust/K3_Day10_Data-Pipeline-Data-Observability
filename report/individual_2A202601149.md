# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| :--- | :--- |
| **Họ và tên** | **Lê Chí Anh Tuấn** |
| **Mã học viên** | **2A202601149** |
| **Khóa/Lớp** | **K3** |
| **Tên nhóm** | **Nhóm B4** |
| **Vai trò chính** | **Người 2 — Ingestion Owner** |
| **Repository** | `https://github.com/duy24ithust/K3_Day10_Data-Pipeline-Data-Observability` |
| **Ngày hoàn thành** | `2026-08-06` |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| :--- | :--- | :--- | :--- | :--- |
| **Crossref ingestion** | `src/ingestion/crossref.py`<br>`parse_crossref_payload()`<br>`fetch_source_records()`<br>`load_raw_records()` | Crossref REST API và `Settings` | Danh sách `PaperRecord` có schema ổn định | **Hoàn thành** |
| **Raw artifacts và lineage** | `data/raw/crossref_response.json`<br>`data/raw/crossref_records.json` | Phản hồi JSON nguyên bản từ Crossref | Raw response và 24 raw records có thể truy vết theo DOI | **Hoàn thành** |
| **Kiểm thử ingestion** | `tests/test_crossref.py` | Payload mẫu, lỗi schema và HTTP retry | 7 test cases cho parser, retry, persistence và load snapshot | **Hoàn thành** |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| :--- | :--- | :--- |
| Bàn giao raw schema | Người 3 — Cleaning Owner | Cleaning nhận đủ `paper_id`, title, summary, authors, categories và dates mà không phải tự tạo dữ liệu nguồn. |
| Kiểm tra lineage | Người 4 — RAG Owner | Đối chiếu 24/24 `paper_id` từ raw sang clean và embedding manifest. |
| Hỗ trợ baseline | Người 1 — Pipeline Integrator | Xác nhận pipeline dùng snapshot local khi `REFRESH_SOURCE=false`, không fetch lại ngoài ý muốn. |
| Hỗ trợ repair | Người 1 và Người 3 | Xác minh repair đọc lại `data/raw/crossref_records.json`, sau đó clean và index lại thay vì sửa tay corrupted data. |

---

## 3. Kết quả theo vai trò

| Checkpoint | Nhiệm vụ đã thực hiện | Kết quả và bằng chứng |
| :---: | :--- | :--- |
| **CP0** | Parse Crossref payload, fetch/load theo `Settings`, lưu raw trước khi parse, retry/backoff | `crossref_response.json` và `crossref_records.json` tồn tại; parser tạo `PaperRecord`; retry hỗ trợ `429/500/502/503/504`. |
| **CP1** | Đối chiếu raw snapshot, kiểm tra DOI/ID và field bàn giao cho cleaning | 24 records, 24 `paper_id` duy nhất; không thiếu title, summary, authors hoặc categories. |
| **CP2** | Kiểm tra một ID xuyên suốt raw → clean → index | 24/24 raw IDs có trong clean và 24/24 clean IDs có trong embedding manifest. ID mẫu: `10.1007/s10278-026-02086-9`. |
| **CP3** | Xác minh raw artifacts và so sánh raw/clean count | Raw `24` → clean `24`; retained ratio `100%`; baseline không refresh source ngoài ý muốn. |
| **CP5** | Bảo vệ raw source trong corruption flow | Corruption chỉ tác động lên clean dataframe; raw response và raw records vẫn là nguồn đáng tin cậy để repair. |
| **CP6** | Kiểm tra repair từ raw và bằng chứng phục hồi | Flow gọi `load_raw_records()` từ snapshot, tạo lại 24 repaired records; metrics repaired trở về đúng baseline. |

**Output cụ thể:**

Module ingestion đã tải và chuẩn hóa **24 bài báo từ Crossref**, tạo **24 DOI duy nhất**, lưu đồng thời response nguyên bản và records đã parse. Tập raw này được dùng lại để repair sau corruption; Retrieval Hit Rate phục hồi từ **60% lên 100%**, bằng đúng baseline.

Commit bàn giao CP0–CP1: `5b2cc5b` — `role 2: cp0 & 1`.

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Crossref trả về JSON có nhiều cấu trúc không đồng nhất: title/container thường nằm trong list, abstract chứa JATS/XML, author có thể dùng `given/family` hoặc `name`, ngày xuất bản có nhiều trường khác nhau và một số paper không có `subject` hoặc PDF. Pipeline cần chuyển dữ liệu này thành schema ổn định mà vẫn giữ được khả năng truy vết về nguồn.

### Cách triển khai

1. Gọi endpoint `https://api.crossref.org/works` với query, filter và `rows` lấy từ `Settings`.
2. Thực hiện tối đa 4 lần gọi khi gặp lỗi tạm thời; ưu tiên `Retry-After`, nếu không có thì backoff theo cấp số nhân.
3. Lưu toàn bộ response vào `data/raw/crossref_response.json` trước khi parse.
4. Chuẩn hóa DOI thành chữ thường và sử dụng làm `paper_id` ổn định.
5. Loại item thiếu DOI/title và bỏ DOI trùng ngay tại bước parse.
6. Loại JATS/XML khỏi abstract, giải mã HTML entities và chuẩn hóa whitespace.
7. Chuẩn hóa authors, subject/category, published/updated dates và URL.
8. Nếu Crossref không có `subject`, dùng `subtype` hoặc `type` do chính nguồn cung cấp làm category dự phòng.
9. Lưu danh sách `PaperRecord` vào `data/raw/crossref_records.json`; khi load lại phải kiểm tra đủ field, ID không rỗng và không trùng.

### Input, output và contract

| Thành phần | Mô tả |
| :--- | :--- |
| **Input** | Crossref JSON payload; `Settings.source_query`, `source_filter`, `max_results` |
| **Output** | `list[PaperRecord]` và hai raw JSON artifacts |
| **Document identity** | DOI đã `strip()` và chuyển lowercase |
| **Field bắt buộc để giữ record** | `paper_id` và `title` |
| **Field có thể rỗng** | `pdf_url`, vì không phải publisher nào cũng cung cấp PDF công khai |
| **Module dùng output** | `cleaning.py`, `phase1.py`, `corruption_flow.py`, test-set/index pipeline |

### Cách xác minh

```powershell
$env:PYTHONPATH="src"
python -m unittest -v tests.test_crossref
```

- **Kết quả thực tế:** `7/7` test cases passed.
- **Artifact:** `data/raw/crossref_response.json`, `data/raw/crossref_records.json`.
- **Dữ liệu thực tế:** 24 records, 24 unique IDs, 0 record thiếu summary/authors/categories.

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Pipeline cần một ID ổn định để nối cùng paper qua raw, clean, Chroma metadata, evaluation và repaired data.
- **Các phương án cân nhắc:**
  1. Dùng vị trí của item trong response.
  2. Hash title và tên tác giả.
  3. Dùng DOI chuẩn hóa.
- **Phương án chọn:** Dùng DOI sau khi loại whitespace và chuyển lowercase.
- **Lý do:** DOI là persistent identifier do nguồn cung cấp; không phụ thuộc thứ tự API, cách viết hoa hay thay đổi nhỏ của title. Hash title có thể đổi khi publisher cập nhật metadata, còn index của item không ổn định giữa các lần fetch.
- **Bằng chứng:** 24/24 `paper_id` được giữ nguyên qua raw → clean → index; ground-truth document IDs và repaired data tiếp tục dùng cùng ID.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** 24 records Crossref đều không có trường `subject`, khiến `categories` ban đầu rỗng và không đủ dữ liệu cho câu hỏi loại `categories` trong evaluation set.
- **Nguyên nhân:** `subject` là metadata tùy chọn; Crossref không đảm bảo mọi publisher đều cung cấp.
- **Cách xử lý:** Ưu tiên `subject`; nếu rỗng thì dùng `subtype`, sau đó đến `type` từ chính Crossref. Không tự bịa category.
- **Cách xác minh:** Sau parse, `missing_categories=0`; test `test_parse_uses_source_type_when_subject_is_missing` passed.
- **Điều học được:** Field tùy chọn cần có fallback truy vết được về nguồn. Fallback không nên dựa trên suy đoán nội dung nếu chưa có bước phân loại riêng.

---

## 7. Hiểu biết về luồng end-to-end

1. Crossref API cung cấp metadata; Role 2 lưu response nguyên bản và records đã parse để tạo điểm khôi phục đáng tin cậy.
2. Cleaning chuẩn hóa raw records, tính `age_days` và tạo `text_for_embedding`.
3. MiniLM tạo embeddings; Chroma collection lưu nội dung cùng metadata `paper_id`.
4. Evaluation set có 40 câu hỏi thuộc bốn loại `summary`, `authors`, `date`, `categories`; mỗi loại 10 câu và dùng `ground_truth_doc_ids` lấy từ clean IDs.
5. Baseline được đánh giá trước khi corruption để tạo mốc so sánh.
6. Corruption drop record, xóa summary, chèn noise, truncate title, làm cũ published date và thêm duplicate nhưng không sửa raw snapshot.
7. Repair đọc lại đúng raw records, chạy cleaning/index/evaluation với cùng test set; không chỉnh tay answers hoặc metrics.
8. So sánh chỉ có ý nghĩa khi baseline, corrupted và repaired dùng cùng test set, evaluator và `top_k`.

---

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| :--- | ---: | ---: | ---: | :--- |
| `retrieval_hit_rate` | 100.0% | 60.0% | 100.0% | Mất/noise dữ liệu làm retrieval giảm 40 điểm phần trăm; repair từ raw phục hồi hoàn toàn. |
| `mean_token_f1` | 0.5778 | 0.1575 | 0.5778 | Nội dung trả lời giảm mạnh khi summary bị xóa hoặc nhiễu, sau đó trở lại baseline. |
| `judge_accuracy` | 52.5% | 12.5% | 52.5% | Agent thiếu nguồn đúng nên accuracy giảm; repaired corpus khôi phục kết quả. |
| `mean_judge_score` | 3.05 | 1.50 | 3.05 | Chất lượng câu trả lời giảm 1.55 điểm khi dữ liệu corrupted. |
| Quality gate | PASS | FAIL | PASS | Quality checks phát hiện duplicate, summary rỗng, noise và title bị cắt. |
| Freshness | FRESH | STALE | FRESH | Corruption tạo một record cũ; repair lấy lại ngày từ raw source. |

### Quan hệ nhân quả quan sát được

```text
Raw snapshot đáng tin cậy
    → baseline 24 records, Hit Rate 100%
    → corruption còn 23 rows và có duplicate/blank/noise/stale
    → Hit Rate giảm còn 60%
    → reload 24 raw records và chạy lại cleaning/index
    → Hit Rate trở lại 100%
```

Kết quả repaired trùng baseline trên cả bốn metrics chính. Đây là bằng chứng raw snapshot do Role 2 bàn giao đủ để phục hồi pipeline mà không cần sửa thủ công dữ liệu hoặc kết quả đánh giá.

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Data lineage cần bắt đầu từ ingestion:** nếu không lưu raw response và stable ID, không thể giải thích hoặc repair lỗi downstream.
2. **Retry không thay thế snapshot:** retry giúp lấy dữ liệu ổn định, còn snapshot giúp thí nghiệm baseline/corrupted/repaired công bằng và tái lập được.
3. **Schema contract ảnh hưởng toàn pipeline:** DOI, title, authors, categories và dates được xử lý đúng ngay từ raw giúp cleaning, test set và index không phải đoán dữ liệu.

### Nếu có thêm thời gian

- Bổ sung địa chỉ liên hệ `mailto` cấu hình được cho Crossref polite pool.
- Lưu metadata thời điểm fetch và checksum raw artifacts để audit lineage tự động.
- Thêm thống kê rõ số item bị loại theo từng lý do ngay trong ingestion report.

---

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phạm vi Role 2 — Ingestion Owner.
- [x] Tôi có thể giải thích luồng end-to-end và quan hệ raw → corrupted → repaired.
- [x] Mọi số liệu trong báo cáo có artifact JSON/CSV/Markdown để đối chiếu.
- [x] Tôi không nhận ownership cho cleaning, corruption, evaluation hoặc observability code.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo không sao chép nguyên văn báo cáo của thành viên khác.

**Họ và tên:** **Chưa cung cấp**  
**Mã học viên:** **2A202601149**  
**Ngày xác nhận:** `2026-08-06`
