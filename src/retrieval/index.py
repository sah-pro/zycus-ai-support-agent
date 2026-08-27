"""Lightweight lexical (BM25) retrieval over knowledge-base chunks.

Deliberately dependency-light: 8 markdown files / ~150 chunks does not
justify an embeddings model or vector database, and a lexical index is
100% deterministic, which matters given the reproducibility requirement
in Task 2 and the "no LLM judge where a deterministic check will do"
requirement in Task 3. Error codes and product/module names -- the
highest-signal terms in this domain -- are also exact-match tokens, which
lexical retrieval handles very well.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache

from src.config.settings import settings
from src.retrieval.chunker import Chunk, load_and_chunk_knowledge_base

_TOKEN_RE = re.compile(r"[a-z0-9_]+")

# Common English function words. Left unfiltered, a long, generic ticket
# body can accumulate a deceptively high BM25 score purely from words like
# "with", "any", "document" matching *something* in a 150-chunk corpus --
# which would let a nonsense or off-topic ticket look like a real KB match.
# Stripping stopwords before scoring means real relevance requires overlap
# on actual content words (product names, error codes, domain terms).
_STOPWORDS = frozenset(
    """
    a an the this that these those is are was were be been being
    of in on at to for from with without within about above below
    and or but if then than so as it its it's i you he she we they
    my your his her our their not no nor do does did doing have has had
    having will would shall should can could may might must
    there here when where why how what which who whom
    all any both each few more most other some such only own same
    just also very too more most much many
    """.split()
)


def _tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS]


@dataclass(frozen=True)
class RetrievalResult:
    chunk: Chunk
    score: float
    reason: str


class BM25Index:
    """Minimal, dependency-free BM25 implementation."""

    K1 = 1.5
    B = 0.75
    # Raw-score value at which normalized relevance crosses 0.5. Calibrated
    # against this KB: strong matches (error codes, product-specific terms)
    # produce raw scores in roughly the 8-20 range after stopword removal;
    # incidental overlap on an off-topic ticket stays in the low single
    # digits. See `search()` for how this is used.
    SCORE_SATURATION = 6.0

    def __init__(self, chunks: list[Chunk]):
        self.chunks = chunks
        self._doc_tokens = [_tokenize(c.text) for c in chunks]
        self._doc_len = [len(toks) for toks in self._doc_tokens]
        self._avg_len = (sum(self._doc_len) / len(self._doc_len)) if self._doc_len else 0.0
        self._doc_freq: Counter[str] = Counter()
        self._term_freqs: list[Counter[str]] = []
        for toks in self._doc_tokens:
            tf = Counter(toks)
            self._term_freqs.append(tf)
            for term in tf:
                self._doc_freq[term] += 1
        self._n_docs = len(chunks)

    def _idf(self, term: str) -> float:
        df = self._doc_freq.get(term, 0)
        return math.log(1 + (self._n_docs - df + 0.5) / (df + 0.5))

    def search(self, query: str, top_k: int = 3) -> list[RetrievalResult]:
        query_terms = _tokenize(query)
        if not query_terms or not self.chunks:
            return []

        scores = [0.0] * self._n_docs
        for term in query_terms:
            idf = self._idf(term)
            if idf <= 0:
                continue
            for i, tf in enumerate(self._term_freqs):
                f = tf.get(term, 0)
                if f == 0:
                    continue
                denom = f + self.K1 * (1 - self.B + self.B * self._doc_len[i] / (self._avg_len or 1))
                scores[i] += idf * (f * (self.K1 + 1)) / denom

        # Boost exact error-code / product-area matches -- these are the
        # deterministic "known issue" signals a support engineer would
        # trust most.
        query_lower = query.lower()
        for i, chunk in enumerate(self.chunks):
            if chunk.is_error_code_row and any(t in chunk.text.lower() for t in query_terms):
                scores[i] *= 1.5
            if chunk.product and chunk.product.lower() in query_lower:
                scores[i] *= 1.2

        ranked = sorted(range(self._n_docs), key=lambda i: scores[i], reverse=True)
        results = []
        for i in ranked[:top_k]:
            if scores[i] <= 0:
                continue
            # Saturating normalization into (0, 1) based on the *absolute*
            # raw BM25 score, not the max score within this query's own
            # result set. Per-query max-normalization would force the top
            # hit to 1.0 regardless of whether it's a strong or a purely
            # incidental match, which defeats any downstream relevance
            # threshold (see guard_known_issue). SCORE_SATURATION is a
            # fixed constant calibrated against this corpus: exact
            # error-code / product-name hits score well above it, while
            # generic multi-stopword-free overlap on an off-topic ticket
            # scores well below it.
            normalized = scores[i] / (scores[i] + self.SCORE_SATURATION)
            results.append(
                RetrievalResult(
                    chunk=self.chunks[i],
                    score=round(normalized, 4),
                    reason=_explain_match(query_terms, self.chunks[i]),
                )
            )
        return results


def _explain_match(query_terms: list[str], chunk: Chunk) -> str:
    chunk_terms = set(_tokenize(chunk.text))
    overlap = sorted(set(query_terms) & chunk_terms)[:6]
    if chunk.is_error_code_row:
        return f"Exact error-code reference match ({', '.join(overlap) or 'code'})"
    if overlap:
        return f"Shared terms: {', '.join(overlap)}"
    return "Section heading relevance"


@lru_cache(maxsize=1)
def get_bm25_index() -> BM25Index:
    chunks = load_and_chunk_knowledge_base(settings.knowledge_base_dir)
    return BM25Index(chunks)


def retrieve(query: str, top_k: int | None = None) -> list[RetrievalResult]:
    index = get_bm25_index()
    return index.search(query, top_k=top_k or settings.retrieval_top_k)
