# RunbookQuery

> Hybrid search for SRE/on-call knowledge – find the runbook you need, fast.

A search service that helps developers and on-call engineers resolve operational incidents faster by retrieving relevant troubleshooting steps, runbook guidance, and prior issue discussions from a curated public corpus.

## Features

- **Hybrid Search**: Combines BM25 (exact match) + Vector (semantic) retrieval
- **Multi-Source**: Kubernetes, Prometheus, Grafana docs + GitHub Issues
- **Incremental Ingestion**: Content-hash based deduplication
- **Evaluation Harness**: nDCG, MRR, Recall metrics

## Quick Start

```bash
# Install dependencies
pip install -e ".[dev]"

# Ingest sample data
runbook-query ingest --source ./sample_docs

# Start the server
runbook-query serve

# Search via API
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "CrashLoopBackOff readiness probe", "top_k": 5}'
```

## Project Structure

```
src/runbook_query/
├── api/           # FastAPI routes
├── retrieval/     # BM25, vector, hybrid search
├── ingestion/     # Connectors, parsing, chunking
├── indexing/      # Index management
├── models/        # Data models
├── storage/       # SQLite persistence
└── cli.py         # CLI entrypoint
```

## Development

```bash
# Run tests
pytest

# Type check
mypy src/

# Lint
ruff check src/
```

## License

MIT
