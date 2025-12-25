"""Evaluation runner script."""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path

import structlog

from runbook_query.api.service import SearchService
from runbook_query.evaluation.metrics import (
    calculate_mrr,
    calculate_ndcg_at_k,
    calculate_recall_at_k,
)
from runbook_query.indexing import get_index_manager
from runbook_query.models.search import SearchRequest
from runbook_query.retrieval import get_bm25_retriever, get_query_cache, get_vector_retriever
from runbook_query.storage import init_database

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

DATASET_PATH = Path(__file__).parent / "dataset.json"
RESULTS_DIR = Path(__file__).parent.parent.parent.parent / "evaluation_results"

async def run_evaluation():
    """Run the evaluation suite."""
    logger.info("starting_evaluation")
    
    # Initialize components
    await init_database()
    
    bm25 = get_bm25_retriever()
    vector = get_vector_retriever()
    cache = get_query_cache()
    manager = get_index_manager(bm25, vector)
    
    # Load indexes
    if not manager.load_indexes():
        logger.error("no_indexes_found")
        return

    # Initialize search service
    service = SearchService(bm25, vector, cache)
    
    # Load dataset
    with open(DATASET_PATH, "r") as f:
        dataset = json.load(f)
        
    logger.info("dataset_loaded", count=len(dataset))
    
    results = []
    total_latency = 0
    k = 10
    
    # Run queries
    for item in dataset:
        query = item["query"]
        expected_doc_id = item["expected_doc_id"]
        difficulty = item["difficulty"]
        
        # Perform search
        request = SearchRequest(query=query, top_k=k)
        start_time = time.time()
        response = await service.search(request)
        latency = (time.time() - start_time) * 1000
        total_latency += latency
        
        # Extract retrieved doc IDs (deduplicated, keeping order)
        seen = set()
        retrieved_ids = []
        for r in response.results:
            if r.document_id not in seen:
                retrieved_ids.append(r.document_id)
                seen.add(r.document_id)
                
        expected_ids = [expected_doc_id]  # Only one expected doc per query in this dataset
        
        # Calculate metrics
        mrr = calculate_mrr(retrieved_ids, expected_ids)
        ndcg_10 = calculate_ndcg_at_k(retrieved_ids, expected_ids, k)
        recall_10 = calculate_recall_at_k(retrieved_ids, expected_ids, k)
        
        # Find rank of expected doc
        rank = -1
        try:
            rank = retrieved_ids.index(expected_doc_id) + 1
        except ValueError:
            rank = -1
            
        result = {
            "query": query,
            "expected_doc_id": expected_doc_id,
            "difficulty": difficulty,
            "retrieved_top_3": retrieved_ids[:3],
            "rank": rank,
            "mrr": mrr,
            "ndcg_10": ndcg_10,
            "recall_10": recall_10,
            "latency_ms": latency,
        }
        results.append(result)
        
        logger.info(
            "query_evaluated",
            query=query,
            rank=rank,
            mrr=mrr,
            latency=f"{latency:.1f}ms"
        )

    # Calculate aggregate metrics
    avg_latency = total_latency / len(dataset)
    mean_mrr = sum(r["mrr"] for r in results) / len(results)
    mean_ndcg = sum(r["ndcg_10"] for r in results) / len(results)
    mean_recall = sum(r["recall_10"] for r in results) / len(results)
    
    # Breakdown by difficulty
    by_diff = {}
    for diff in ["easy", "medium", "hard"]:
        subset = [r for r in results if r["difficulty"] == diff]
        if subset:
            by_diff[diff] = {
                "mrr": sum(r["mrr"] for r in subset) / len(subset),
                "ndcg": sum(r["ndcg_10"] for r in subset) / len(subset),
                "recall": sum(r["recall_10"] for r in subset) / len(subset),
                "count": len(subset)
            }

    summary = {
        "timestamp": datetime.now().isoformat(),
        "total_queries": len(dataset),
        "mean_mrr": mean_mrr,
        "mean_ndcg_10": mean_ndcg,
        "mean_recall_10": mean_recall,
        "avg_latency_ms": avg_latency,
        "by_difficulty": by_diff,
        "index_version": manager.get_status().get("current_version", "unknown")
    }
    
    # Save results
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = RESULTS_DIR / f"eval_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    full_report = {
        "summary": summary,
        "results": results
    }
    
    with open(report_path, "w") as f:
        json.dump(full_report, f, indent=2)
        
    logger.info(
        "evaluation_complete",
        report_path=str(report_path),
        mean_mrr=mean_mrr,
        mean_ndcg=mean_ndcg,
        mean_recall=mean_recall
    )
    
    print("\n=== Evaluation Summary ===")
    print(f"Total Queries: {len(dataset)}")
    print(f"Mean MRR:      {mean_mrr:.4f}")
    print(f"Mean nDCG@10:  {mean_ndcg:.4f}")
    print(f"Mean Recall@10:{mean_recall:.4f}")
    print(f"Avg Latency:   {avg_latency:.1f}ms")
    print("\nBy Difficulty:")
    for diff, metrics in by_diff.items():
        print(f"  {diff.title()} (n={metrics['count']}): MRR {metrics['mrr']:.3f}, Recall {metrics['recall']:.3f}")

if __name__ == "__main__":
    asyncio.run(run_evaluation())
