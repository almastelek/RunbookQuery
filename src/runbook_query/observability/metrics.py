from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

# Search Metrics
SEARCH_REQUESTS = Counter(
    "search_requests_total",
    "Total number of search requests",
    ["status", "mode"]
)

SEARCH_LATENCY = Histogram(
    "search_latency_seconds",
    "Search request latency in seconds",
    ["mode"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

CACHE_HITS = Counter(
    "search_cache_hits_total",
    "Total number of cache hits"
)

CACHE_MISSES = Counter(
    "search_cache_misses_total",
    "Total number of cache misses"
)

# Ingestion Metrics
INGESTION_DOCUMENTS = Counter(
    "ingestion_documents_total",
    "Total number of documents ingested",
    ["source_type", "status"]
)

INGESTION_LATENCY = Histogram(
    "ingestion_latency_seconds",
    "Ingestion pipeline latency in seconds",
    ["source_type"]
)

INDEX_BUILD_TIME = Histogram(
    "index_build_seconds",
    "Time taken to build indexes",
    ["index_type"]
)

def get_metrics():
    """Return latest metrics in Prometheus format."""
    return generate_latest(), CONTENT_TYPE_LATEST
