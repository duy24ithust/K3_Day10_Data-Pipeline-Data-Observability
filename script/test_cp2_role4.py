from __future__ import annotations

import pathlib
import sys

# Đảm bảo console Windows hỗ trợ hiển thị UTF-8 không bị lỗi charmap
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Đảm bảo import được module trong thư mục src/
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

import pandas as pd
from core.config import load_settings
from retrieval.agent import build_agent, run_agent_question
from retrieval.index import LocalEmbeddingIndex


def run_cp2_rag_demo():
    print("=" * 60)
    print("CHECKPOINT 2 (CP2) - RAG & AGENT VERIFICATION SCRIPT")
    print("=" * 60)

    # 1. Load Settings và Clean Data
    settings = load_settings()
    clean_csv_path = settings.paths.clean_csv

    if not clean_csv_path.exists():
        print(f"❌ Không tìm thấy file dữ liệu sạch: {clean_csv_path}")
        print("Vui lòng hoàn thành CP1 (Data Cleaning) trước!")
        return

    clean_df = pd.read_csv(clean_csv_path)
    print(f"\n[1/3] Nạp thành công {len(clean_df)} bản ghi từ '{clean_csv_path.name}'")

    # Tạo MiniLM Embeddings & Chroma collection 'papers-baseline'
    print("Đang mã hóa Embeddings và khởi tạo Chroma Collection...")
    index = LocalEmbeddingIndex.build(clean_df, settings)
    print(f"✓ Đã tạo thành công Chroma Collection: '{index.collection_name}'")
    print(f"✓ Manifest lưu tại: {settings.paths.embeddings_json}")

    # 2. Test Semantic Search & Exact Lookup
    print("\n[2/3] Kiểm tra Semantic Search & Exact Lookup...")
    query = "RAG reasoning and retrieval"
    results = index.search(query, top_k=2)

    print(f"  🔍 Truy vấn thử nghiệm: '{query}'")
    print(f"  --> Tìm thấy {len(results)} kết quả tương quan cao nhất:")
    for i, res in enumerate(results, 1):
        print(f"      [{i}] ID: {res.paper_id} (Score: {res.score:.4f})")
        print(f"          Title: {res.title}")

    # Test Exact Lookup
    sample_id = clean_df["paper_id"].iloc[0]
    lookup_res = index.lookup(sample_id)
    print(f"\n  🎯 Exact Lookup thử nghiệm với paper_id='{sample_id}':")
    if lookup_res:
        print(f"      ✓ Tìm thấy: {lookup_res['title']}")
    else:
        print("      ❌ Không tìm thấy bản ghi!")

    # 3. Tạo Agent & Test Tool Execution
    print("\n[3/3] Tạo Agent và kiểm tra gọi Tool...")
    agent = build_agent(settings, index)
    print("✓ Đã tạo Agent thành công với 2 tools: 'semantic_search_papers' & 'lookup_paper'")

    test_question = "RAG kết hợp với LLM mang lại lợi ích gì trong nghiên cứu?"
    print(f"\n  ❓ Đặt câu hỏi thử nghiệm cho Agent: '{test_question}'")
    print("  ⏳ Agent đang thực thi và gọi Tool...")
    
    response = run_agent_question(agent, test_question)
    print("\n  🤖 Phản hồi của Agent (Dựa trên dữ liệu thu thập):")
    print("  " + "-" * 50)
    print(response)
    print("  " + "-" * 50)


if __name__ == "__main__":
    run_cp2_rag_demo()
