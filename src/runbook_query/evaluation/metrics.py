"""Metrics calculation for search evaluation."""

import math
from typing import List, Dict, Any

def calculate_precision_at_k(actual: List[str], expected: List[str], k: int) -> float:
    """
    Calculate Precision@K.

    Args:
        actual (List[str]): List of retrieved document IDs.
        expected (List[str]): List of relevant document IDs.
        k (int): Cutoff rank.

    Returns:
        float: Precision at rank k.
    """
    if not actual:
        return 0.0
    
    actual_k = actual[:k]
    relevant_retrieved = sum(1 for doc_id in actual_k if doc_id in expected)
    
    return relevant_retrieved / len(actual_k)

def calculate_recall_at_k(actual: List[str], expected: List[str], k: int) -> float:
    """
    Calculate Recall@K.

    Args:
        actual (List[str]): List of retrieved document IDs.
        expected (List[str]): List of relevant document IDs.
        k (int): Cutoff rank.

    Returns:
        float: Recall at rank k.
    """
    if not expected:
        return 0.0
        
    actual_k = set(actual[:k])
    expected_set = set(expected)
    relevant_retrieved = len(actual_k.intersection(expected_set))
    
    return relevant_retrieved / len(expected_set)

def calculate_mrr(actual: List[str], expected: List[str]) -> float:
    """
    Calculate Mean Reciprocal Rank (MRR) for a single query.
    
    Args:
        actual (List[str]): List of retrieved document IDs.
        expected (List[str]): List of relevant document IDs.
        
    Returns:
        float: Reciprocal rank (1/rank of first relevant item).
    """
    for i, doc_id in enumerate(actual):
        if doc_id in expected:
            return 1.0 / (i + 1)
    return 0.0

def calculate_ndcg_at_k(actual: List[str], expected: List[str], k: int) -> float:
    """
    Calculate Normalized Discounted Cumulative Gain (nDCG@K).
    
    Assuming binary relevance (1 for relevant, 0 for not relevant).
    
    Args:
        actual (List[str]): List of retrieved document IDs.
        expected (List[str]): List of relevant document IDs.
        k (int): Cutoff rank.
        
    Returns:
        float: nDCG at rank k.
    """
    dcg = 0.0
    idcg = 0.0
    
    actual_k = actual[:k]
    
    # Calculate DCG
    for i, doc_id in enumerate(actual_k):
        if doc_id in expected:
            rel = 1.0
            dcg += rel / math.log2(i + 2)
            
    # Calculate IDCG (Ideal DCG)
    # In binary relevance, ideal ranking has all relevant items at the top
    num_relevant = min(len(expected), k)
    for i in range(num_relevant):
        rel = 1.0
        idcg += rel / math.log2(i + 2)
        
    if idcg == 0.0:
        return 0.0
        
    return dcg / idcg
