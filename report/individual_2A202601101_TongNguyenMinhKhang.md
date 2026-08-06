# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| :--- | :--- |
| **Họ và tên** | **Tống Nguyễn Minh Khang** |
| **MSSV** | **2A202601101** |
| **Khóa/Lớp** | **K3** |
| **Tên nhóm** | **Nhóm B4** |
| **Vai trò chính** | **RAG & Agent Owner (Người 4 trong Nhóm 5 người)** |
| **Repository** | `https://github.com/duy24ithust/K3_Day10_Data-Pipeline-Data-Observability.git` |
| **Ngày hoàn thành** | `2026-08-06` |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| :--- | :--- | :--- | :--- | :--- |
| **Vector Embedding Generation** | `src/retrieval/embeddings.py`<br>(`MiniLMEmbeddings`) | Normalized text (`text_for_embedding`) từ Clean DataFrame | Vector Embeddings (384 chiều, MiniLM-L6-v2) | **Hoàn thành** |
| **ChromaDB Vector Indexing** | `src/retrieval/index.py`<br>(`LocalEmbeddingIndex`) | Clean, Corrupted & Repaired DataFrames | 3 Chroma Collections:<br>`papers-baseline`, `papers-corrupted`, `papers-repaired`<br>+ Embedding Manifests JSON | **Hoàn thành** |
| **Semantic Search & Exact Lookup** | `src/retrieval/index.py`<br>(`search`, `lookup`) | Query string, `paper_id` hoặc `title` | Trả về danh sách `SearchResult` (score, metadata, content) | **Hoàn thành** |
| **RAG Agent & Tools Integration** | `src/retrieval/agent.py`<br>(`build_agent`, `run_agent_question`) | Chroma Index, LLM Settings, System Prompt | Agent tích hợp 2 tools:<br>`semantic_search_papers`<br>`lookup_paper` | **Hoàn thành** |

---

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| :--- | :--- | :--- |
| **Hỗ trợ Cleaning Contract** | Người 3 (Cleaning Owner) / `src/ingestion/cleaning.py` | Kiểm tra và thống nhất cấu trúc trường `text_for_embedding` gồm `Title`, `Authors`, `Categories`, `Summary` không bị rỗng. |
| **Hỗ trợ Multi-Collection Indexing** | Người 2 (Corruption Owner) / `src/ingestion/corruption.py` | Tạo cơ chế tách biệt 3 không gian lưu trữ Chroma DB độc lập cho 3 pha (Baseline, Corrupted, Repaired). |
| **Hỗ trợ Pipeline Orchestration** | Người 1 (Pipeline Integrator) / `src/pipelines/phase1.py` & `corruption_flow.py` | Tích hợp các bước build vector index và khởi tạo agent vào luồng điều phối end-to-end. |
| **Hỗ trợ Evaluation & Observability** | Người 5 (Evaluation Owner) / `src/evaluation/metrics.py` | Cung cấp đầu ra tìm kiếm ngữ nghĩa chuẩn cho Evaluator đối chiếu `ground_truth_doc_ids`. |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| :--- | :--- | :--- | :--- |
| **Tạo MiniLM Embeddings & Chroma Vector Store** | `src/retrieval/embeddings.py`<br>`src/retrieval/index.py` | Mã hóa 24 bản ghi thành công vào collection `papers-baseline` | `data/embeddings/papers_embeddings.json` |
| **Triển khai Semantic Search & Exact Lookup** | `src/retrieval/index.py` | Trả về độ tương quan ngữ nghĩa chuẩn và tra cứu 100% chính xác theo ID | Script `script/test_cp2_rag.py` |
| **Tạo Agent với System Prompt Grounding** | `src/retrieval/agent.py` | Agent bắt buộc gọi Tool trước khi trả lời và từ chối bịa thông tin ngoài corpus | Script `script/test_cp3_rag.py` |
| **UnitTest cho RAG & Vector Index** | `tests/test_rag.py` | Bộ test suite tự động 3/3 test cases đều PASSED | `python -m unittest tests/test_rag.py` |

**Output cụ thể:**
Tôi đã xây dựng toàn bộ module Retrieval & Agent (`src/retrieval/`), tích hợp mô hình `sentence-transformers/all-MiniLM-L6-v2` mã hóa văn bản thành vector embeddings 384 chiều, lưu trữ vào ChromaDB. Xây dựng Agent tích hợp 2 Tools (`semantic_search_papers` và `lookup_paper`) giúp trả lời dựa trên dữ liệu có căn cứ (grounded factuality). Ở pha Baseline, hệ thống đạt **100% Retrieval Hit Rate**. Khi dữ liệu bị Corrupted, Hit Rate giảm về **60%**, và phục hồi lại **100%** sau khi dữ liệu được Repaired.

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Xây dựng thành phần Vector Database và RAG Agent đóng vai trò "bộ não truy xuất" thông tin cho hệ thống. Đảm bảo:
1. Mã hóa ngữ nghĩa văn bản học thuật chính xác thành Vector Embeddings.
2. Lưu trữ và phân tách độc lập giữa các trạng thái thử nghiệm (Baseline, Corrupted, Repaired).
3. Đảm bảo Agent luôn gọi Tool tra cứu thông tin từ Vector DB trước khi sinh câu trả lời, không bị hiện tượng "ảo giác" (hallucination) hay vượt ngoài corpus.

### Cách triển khai

1. **Khởi tạo Embedding Model (`src/retrieval/embeddings.py`)**:
   - Sử dụng mô hình `sentence-transformers/all-MiniLM-L6-v2` thông qua class `MiniLMEmbeddings` kế thừa từ `langchain_core.embeddings.Embeddings`.
   - Chuẩn hóa vector đầu ra với tham số `normalize_embeddings=True` để tính khoảng cách Cosine Similarity chuẩn xác.

2. **Xây dựng Local Embedding Index & ChromaDB Manager (`src/retrieval/index.py`)**:
   - Sử dụng `chromadb.PersistentClient` lưu trữ index bền vững tại `data/chroma/`.
   - Xây dựng hàm `build()` tự động bóc tách `text_for_embedding` làm nội dung vector, gán các trường metadata (`paper_id`, `title`, `published`, `authors_joined`, `categories_joined`, `summary`, `abs_url`, `pdf_url`).
   - Tự động gán tên collection linh hoạt (`papers-baseline`, `papers-corrupted`, `papers-repaired`) và xuất manifest JSON.
   - Triển khai `search()` hỗ trợ tìm kiếm Cosine Similarity top_k và `lookup()` hỗ trợ tìm kiếm chính xác theo ID/Title.

3. **Xây dựng RAG Agent & Tool Grounding (`src/retrieval/agent.py`)**:
   - Đăng ký 2 Custom Tools: `@tool semantic_search_papers` và `@tool lookup_paper`.
   - Cài đặt System Prompt chặt chẽ:
     > *"You answer questions about the indexed scholarly paper corpus sourced from Crossref. ALWAYS use tools before answering factual questions. DO NOT make up answers not in the indexed corpus. If the indexed corpus does not support the answer, say so clearly."*
   - Xây dựng hàm `run_agent_question()` điều phối hội thoại và gọi Tool thực thi.

### Input, output và contract

| Thành phần | Mô tả |
| :--- | :--- |
| **Input** | Clean DataFrame (chứa `text_for_embedding`, `paper_id`, `title`, metadata), User Question |
| **Output** | Chroma Collections, Embedding Manifest JSON, `SearchResult` List, Agent Grounded Answer |
| **Module phụ thuộc** | `src/core/config.py`, `src/ingestion/cleaning.py`, `chromadb`, `sentence_transformers`, `langchain` |
| **Module sử dụng output** | `src/evaluation/metrics.py`, `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py` |
| **Điều kiện lỗi cần xử lý** | Dữ liệu rỗng, nhãn `NaN` từ Pandas, trùng khóa Chroma collection, mất file đĩa index |

### Cách xác minh

```powershell
# 1. Chạy script CP2 (Build Index, Semantic Search, Exact Lookup)
.\.venv\Scripts\python.exe script/run_build_embedding_chroma.py

# 2. Chạy script CP3 (Khớp Manifest, Agent Tool Execution, Anti-Hallucination)
.\.venv\Scripts\python.exe script/test_cp3_rag.py

# 3. Chạy Unit Test suite độc lập
.\.venv\Scripts\python.exe -m unittest tests/test_rag.py
```

- **Kết quả mong đợi:** Tất cả các script chạy mượt mà, Vector Collection khởi tạo chuẩn, Agent gọi Tool thành công, Unit Test báo `OK` (3/3 tests PASSED).
- **Kết quả thực tế:** Tất cả các luồng đều đạt 100% tiêu chí.

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn phương pháp quản lý các Vector Collection trong ChromaDB giữa các pha thử nghiệm khác nhau.
- **Các phương án đã cân nhắc:**
  1. *Phương án A*: Sử dụng 1 Chroma Collection duy nhất, thực hiện xóa (`delete_collection`) và nạp ghi đè lại dữ liệu ở mỗi pha.
  2. *Phương án B*: Tạo 3 Collection riêng biệt với tên phân biệt rõ ràng: `papers-baseline`, `papers-corrupted`, và `papers-repaired`.
- **Phương án đã chọn:** **Phương án B**.
- **Lý do:** Phương án A làm mất dấu vết Vector của pha trước đó, khiến không thể chạy lại đánh giá độc lập hoặc đối chiếu song song. Phương án B giúp phân tách hoàn toàn không gian Vector Store, giữ nguyên dữ liệu thực nghiệm để phục vụ quan sát (observability) và tái lập kết quả bất kỳ lúc nào.
- **Bằng chứng quyết định phù hợp:** Đảm bảo quá trình tính toán chỉ số `retrieval_hit_rate` và `mean_token_f1` của 3 pha trong `corruption_report.md` chính xác tuyệt đối mà không bị xung đột dữ liệu.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**  
  `chromadb.errors.NotFoundError: Collection [papers-baseline] does not exist` khi gọi `LocalEmbeddingIndex.load(settings)` và nhãn `"pdf_url": NaN` xuất hiện trong file manifest JSON.
- **Lệnh hoặc bước tái hiện:** Thực thi script kiểm thử trực tiếp trên đĩa chưa khởi tạo Chroma index, hoặc nạp file CSV bằng Pandas khiến trường rỗng bị đổi thành kiểu float `NaN`.
- **Nguyên nhân gốc:** 
  1. ChromaDB ném exception nếu collection chưa từng được khởi tạo bằng `build()`.
  2. Pandas `to_dict()` giữ nguyên float `NaN`, khi dùng `json.dump()` sẽ xuất ra `NaN` vi phạm chuẩn JSON nghiêm ngặt.
- **Cách xử lý:** 
  1. Bổ sung cơ chế **Auto-Build Fallback** trong `test_cp3_rag.py`: Tự động bắt try-except và gọi `LocalEmbeddingIndex.build()` nếu chưa có index sẵn.
  2. Thêm `df.fillna("")` vào hàm `_build_documents()` trong `src/retrieval/index.py` chuẩn hóa toàn bộ giá trị rỗng thành chuỗi `""`.
- **Cách xác minh sau khi sửa:** Chạy bộ unittest [`tests/test_rag.py`](file:///C:/Users/Admin/K3_Day10_Data-Pipeline-Data-Observability/tests/test_rag.py) thành công `OK` (3/3 tests PASSED).
- **Điều học được:** Luôn chủ động xử lý kiểu dữ liệu `NaN` từ Pandas khi xuất JSON, và thiết kế mã nguồn truy xuất Vector Store theo hướng tự phục hồi (resilient).

---

## 7. Hiểu biết về luồng end-to-end

1. Bài báo từ **Crossref API** được nạp thô vào `data/raw/`, qua `cleaning.py` làm sạch thành `data/clean/papers_clean.csv`.
2. Module `retrieval/index.py` nhận Clean DataFrame, tạo chuỗi composite `text_for_embedding`, mã hóa qua `MiniLMEmbeddings` và lưu vào **ChromaDB**.
3. **RAG Agent** (`agent.py`) khi nhận câu hỏi người dùng sẽ bắt buộc sử dụng 2 Tools (`semantic_search_papers`, `lookup_paper`) để truy xuất ngữ cảnh từ ChromaDB trước khi sinh câu trả lời.
4. **Evaluator** đối chiếu kết quả retrieved từ Vector DB với `ground_truth_doc_ids` trong tập `test_set.json` cố định để đo lường các chỉ số Hit Rate, F1 Score và LLM Judge Score.
5. Khi dữ liệu bị **Corrupted** (xóa bài, rỗng summary, nhiễu câu), chất lượng Vector Embedding bị suy thoái làm Retrieval Hit Rate sụt giảm nghiêm trọng từ **100% ➔ 60%**.
6. Sau khi **Repair** từ dữ liệu gốc Crossref, Vector Collection `papers-repaired` tái lập lại 100% chất lượng ban đầu, giúp RAG Agent phục hồi hoàn toàn độ chính xác.

---

## 8. Phân tích kết quả

### Metrics chính liên quan trực tiếp đến RAG & Index

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét cá nhân về tác động lên RAG |
| :--- | :---: | :---: | :---: | :--- |
| `retrieval_hit_rate` | **100.0%** | **60.0%** | **100.0%** | Dữ liệu lỗi (mất summary/bỏ bài mới) làm rớt 40% khả năng truy xuất đúng document. |
| `mean_token_f1` | **0.5778** | **0.1575** | **0.5778** | Chất lượng văn bản ngữ cảnh bị suy giảm nghiêm trọng do thông tin embedding rác. |
| `judge_accuracy` | **52.5%** | **12.5%** | **52.5%** | Agent không có đủ context đúng từ Vector Search nên trả lời sai logic. |
| `mean_judge_score` | **3.05** | **1.50** | **3.05** | Điểm số đánh giá chất lượng câu trả lời từ Agent bị giảm hơn một nửa. |
| Chroma Vector Count | **24 vectors** | **23 vectors** | **24 vectors** | Collection Corrupted mất 1 bài báo và chứa dữ liệu nhiễu/trùng. |

### Kết luận rút ra từ vai trò RAG Owner

1. **Tầm quan trọng của `text_for_embedding`**: Việc kết hợp `Title`, `Authors`, `Categories` và `Summary` giúp vector biểu diễn đầy đủ ngữ nghĩa bài báo. Khi `summary` bị xóa rỗng ở pha Corrupted, vectorembedding bị méo mó khiến tìm kiếm ngữ nghĩa thất bại.
2. **Chống Hallucination nhờ System Prompt & Tools**: Agent tuân thủ nghiêm ngặt nguyên tắc chỉ trả lời dựa trên Tool result. Với câu hỏi ngoài corpus, Agent từ chối bịa câu trả lời thay vì tự sáng tạo thông tin sai sự thật.
3. **Khả năng phục hồi của Vector Index**: Khi dữ liệu sạch được khôi phục ở pha Repaired, Vector Collection `papers-repaired` lập tức khôi phục lại 100% chỉ số Retrieval Hit Rate.

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất
1. **Embedding Quality depends on Clean Data**: Vector Database chỉ hoạt động hiệu quả khi dữ liệu đầu vào được làm sạch chuẩn (Clean Title, Valid Summary, Structured Metadata).
2. **Strict Tool Grounding**: Cài đặt System Prompt yêu cầu Agent bắt buộc dùng Tool là chìa khóa chống bịa thông tin (hallucination) trong các hệ thống RAG thực tế.
3. **Multi-Collection Isolation**: Việc chia tách các Chroma Collection độc lập là phương pháp chuẩn để thực hiện thực nghiệm so sánh đối chứng (controlled experiment).

### Nếu có thêm thời gian
Tôi sẽ tích hợp thêm kỹ thuật **Hybrid Search** (kết hợp Dense Vector Search của MiniLM với Sparse Search BM25) và **Cross-Encoder Re-ranking** để tiếp tục nâng cao chỉ số `mean_token_f1` và `judge_accuracy` cho RAG Agent.

---

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** **Tống Nguyễn Minh Khang**  
**Ngày xác nhận:** `2026-08-06`