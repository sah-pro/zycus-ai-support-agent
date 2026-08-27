from src.retrieval.chunker import chunk_markdown_file
from src.retrieval.index import BM25Index, retrieve


SAMPLE_MD = """# Product X

## Overview

Product X does things.

---

## Errors

| Code | Meaning |
|------|---------|
| `ERR_FOO` | Something broke |
| `ERR_BAR` | Something else broke |
"""


def test_chunker_splits_on_horizontal_rule():
    chunks = chunk_markdown_file("products/x.md", SAMPLE_MD)
    assert len(chunks) >= 2


def test_chunker_extracts_error_code_rows_as_atomic_chunks():
    chunks = chunk_markdown_file("products/x.md", SAMPLE_MD)
    error_chunks = [c for c in chunks if c.is_error_code_row]
    assert any("ERR_FOO" in c.text for c in error_chunks)
    assert any("ERR_BAR" in c.text for c in error_chunks)


def test_bm25_ranks_exact_term_match_highest():
    chunks = chunk_markdown_file("products/x.md", SAMPLE_MD)
    index = BM25Index(chunks)
    results = index.search("ERR_FOO", top_k=1)
    assert results
    assert "ERR_FOO" in results[0].chunk.text


def test_retrieve_against_real_knowledge_base_returns_results():
    results = retrieve("ERR_CONNECTION_TIMEOUT DataBridge Pro", top_k=3)
    assert len(results) > 0
    assert all(0.0 <= r.score <= 1.0 for r in results)


def test_stopwords_are_excluded_from_tokenization():
    """A query built entirely from stopwords must not match anything --
    guards against a nonsense/off-topic ticket accumulating false relevance
    purely from common English function words."""
    results = retrieve("the a an of to in on with this that", top_k=5)
    assert results == []


def test_score_reflects_absolute_relevance_not_just_relative_rank():
    """A query with zero genuine topical overlap with the knowledge base
    must not receive a high score merely because it's the 'best available'
    match within its own result set -- score must be an absolute measure
    of match strength, calibrated against the corpus, not renormalized to
    1.0 per query."""
    off_topic = retrieve(
        "Unrelated topic. The giraffe rode a bicycle past the lighthouse while "
        "eating a pumpkin and humming a symphony near the glacier.",
        top_k=5,
    )
    assert off_topic == []

    strong_match = retrieve("We keep hitting ERR_CONNECTION_TIMEOUT when syncing DataBridge Pro connectors.", top_k=1)
    assert strong_match
    assert strong_match[0].score > 0.5
