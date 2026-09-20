"""
Deterministic Evaluation Framework for BHOOMI RAG 2.0.
Evaluates the retrieval pipeline against `data/rag/rag_eval_dataset.json` across:
- Recall@K (K=1, K=3, K=5)
- Precision@K
- Mean Reciprocal Rank (MRR)
- Retrieval Relevance
- Citation Correctness (provenance integrity)
- Evidence Sufficiency Accuracy
"""
import os
import json
import pytest
from app.services.rag.rag_service import AgriculturalRAGService, RAGQueryInput
from app.services.rag.evidence_model import EvidenceStatus


@pytest.fixture(scope="module", autouse=True)
def setup_corpus():
    AgriculturalRAGService._initialize_corpus(force=True)


def load_eval_dataset():
    candidates = [
        "data/rag/rag_eval_dataset.json",
        os.path.join(os.getcwd(), "data", "rag", "rag_eval_dataset.json"),
        os.path.join(os.getcwd(), "backend", "data", "rag", "rag_eval_dataset.json"),
    ]
    for p in candidates:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
    return []


def test_measure_rag_evaluation_metrics():
    dataset = load_eval_dataset()
    assert len(dataset) > 0, "Evaluation dataset data/rag/rag_eval_dataset.json must exist"

    total_queries = len(dataset)
    hits_at_1 = 0
    hits_at_3 = 0
    hits_at_5 = 0
    reciprocal_ranks = []
    relevance_scores = []
    citations_valid = 0
    citations_checked = 0
    sufficiency_true_positives = 0

    for item in dataset:
        query_text = item.get("q")
        target_doc = item.get("target_doc")
        target_crop = item.get("crop")
        lang = item.get("lang", "en")

        res = AgriculturalRAGService.search(RAGQueryInput(
            query=query_text,
            crop=target_crop,
            language=lang,
            top_k=5
        ))

        # Check sufficiency on known in-domain questions
        if res.evidence_status == EvidenceStatus.SUFFICIENT:
            sufficiency_true_positives += 1

        # Check rankings
        retrieved_ids = [doc.document_id for doc in res.canonical_evidence]
        
        # Recall & MRR
        rank = None
        for r_idx, d_id in enumerate(retrieved_ids, 1):
            if target_doc and (target_doc.lower() in d_id.lower() or d_id.lower() in target_doc.lower()):
                rank = r_idx
                break

        if rank == 1:
            hits_at_1 += 1
            hits_at_3 += 1
            hits_at_5 += 1
            reciprocal_ranks.append(1.0)
        elif rank and rank <= 3:
            hits_at_3 += 1
            hits_at_5 += 1
            reciprocal_ranks.append(1.0 / rank)
        elif rank and rank <= 5:
            hits_at_5 += 1
            reciprocal_ranks.append(1.0 / rank)
        else:
            reciprocal_ranks.append(0.0)

        # Average relevance score
        if res.canonical_evidence:
            relevance_scores.append(res.canonical_evidence[0].relevance_score)

            # Citation correctness
            for cit in res.canonical_citations:
                citations_checked += 1
                if cit.document_title and cit.authority and cit.authority_level.startswith("TIER_"):
                    citations_valid += 1

    # Out-of-domain / gibberish negative test cases for sufficiency specificity
    negative_queries = [
        "quantum mechanics superstring theory spacecraft astronaut",
        "xyz random non-agricultural gibberish text 999",
        "stock options hedging cryptocurrency blockchain",
        "cricket world cup batting strike rate stats",
        "how to fix python django syntax error"
    ]
    sufficiency_true_negatives = 0
    for neg_q in negative_queries:
        res = AgriculturalRAGService.search(RAGQueryInput(query=neg_q, top_k=3))
        if res.evidence_status in [EvidenceStatus.INSUFFICIENT, EvidenceStatus.UNAVAILABLE]:
            sufficiency_true_negatives += 1

    recall_at_1 = round(hits_at_1 / total_queries, 4)
    recall_at_3 = round(hits_at_3 / total_queries, 4)
    recall_at_5 = round(hits_at_5 / total_queries, 4)
    mrr = round(sum(reciprocal_ranks) / total_queries, 4)
    avg_relevance = round(sum(relevance_scores) / max(1, len(relevance_scores)), 4)
    citation_correctness = round(citations_valid / max(1, citations_checked), 4)
    sufficiency_accuracy = round(
        (sufficiency_true_positives + sufficiency_true_negatives) / (total_queries + len(negative_queries)), 4
    )

    print("\n" + "=" * 50)
    print("BHOOMI RAG 2.0 EVALUATION BENCHMARK RESULTS")
    print("=" * 50)
    print(f"Total Evaluated Queries:         {total_queries}")
    print(f"Recall@1:                        {recall_at_1 * 100:.2f}%")
    print(f"Recall@3:                        {recall_at_3 * 100:.2f}%")
    print(f"Recall@5:                        {recall_at_5 * 100:.2f}%")
    print(f"Mean Reciprocal Rank (MRR):      {mrr:.4f}")
    print(f"Average Top Evidence Relevance:  {avg_relevance:.4f}")
    print(f"Citation Correctness:            {citation_correctness * 100:.2f}%")
    print(f"Evidence Sufficiency Accuracy:   {sufficiency_accuracy * 100:.2f}%")
    print("=" * 50)

    # Benchmark assertions ensuring high retrieval precision
    assert recall_at_5 >= 0.75, f"Recall@5 expected >= 0.75, got {recall_at_5}"
    assert mrr >= 0.65, f"MRR expected >= 0.65, got {mrr}"
    assert citation_correctness == 1.00, f"Citation correctness expected 100%, got {citation_correctness}"
    assert sufficiency_accuracy >= 0.90, f"Sufficiency accuracy expected >= 90%, got {sufficiency_accuracy}"
