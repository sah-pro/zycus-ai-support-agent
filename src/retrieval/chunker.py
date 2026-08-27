"""Markdown chunking for the knowledge base, per DATA_SCHEMA.md guidance.

Strategy:
  - Split each document on `---` horizontal rules (major section boundaries).
  - Within a section, track the nearest heading (##, ###) as metadata so
    retrieval results can cite a specific section, not just a whole file.
  - Emit table rows that look like error-code lookups as their own atomic
    chunks, since a single row ("`ERR_CONNECTION_TIMEOUT` | ... | ...") is
    often the single most relevant unit for a support ticket.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_TABLE_ROW_RE = re.compile(r"^\|.*\|\s*$")
_ERROR_CODE_RE = re.compile(r"`([A-Z]{2,}(?:_[A-Z0-9]+)+)`")


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    document: str          # relative path, e.g. products/databridge-pro.md
    product: str | None    # inferred from folder/filename where applicable
    section: str           # nearest heading text
    text: str
    is_error_code_row: bool = False


def _infer_product(doc_path: str) -> str | None:
    name = Path(doc_path).stem.lower()
    mapping = {
        "databridge-pro": "DataBridge Pro",
        "cloudsync": "CloudSync",
        "analyticshub": "AnalyticsHub",
        "securevault": "SecureVault",
        "workflowengine": "WorkflowEngine",
    }
    return mapping.get(name)


def chunk_markdown_file(doc_path: str, text: str) -> list[Chunk]:
    """Chunk a single markdown document into retrievable Chunk objects."""
    chunks: list[Chunk] = []
    product = _infer_product(doc_path)
    current_heading = Path(doc_path).stem
    chunk_index = 0

    for block in text.split("\n---\n"):
        lines = block.strip("\n").split("\n")
        buffer: list[str] = []

        def flush(heading: str) -> None:
            nonlocal chunk_index
            body = "\n".join(buffer).strip()
            if body:
                chunks.append(
                    Chunk(
                        chunk_id=f"{doc_path}::{chunk_index}",
                        document=doc_path,
                        product=product,
                        section=heading,
                        text=body,
                    )
                )
                chunk_index += 1
            buffer.clear()

        for line in lines:
            heading_match = _HEADING_RE.match(line)
            if heading_match:
                flush(current_heading)
                current_heading = heading_match.group(2).strip()
                buffer.append(line)
                continue

            if _TABLE_ROW_RE.match(line) and "---" not in line:
                # Emit table rows referencing error codes as their own
                # atomic, highly-specific chunk (per schema guidance).
                if _ERROR_CODE_RE.search(line):
                    chunks.append(
                        Chunk(
                            chunk_id=f"{doc_path}::{chunk_index}",
                            document=doc_path,
                            product=product,
                            section=current_heading,
                            text=line.strip(),
                            is_error_code_row=True,
                        )
                    )
                    chunk_index += 1
                    continue

            buffer.append(line)

        flush(current_heading)

    return chunks


def load_and_chunk_knowledge_base(kb_dir: Path) -> list[Chunk]:
    all_chunks: list[Chunk] = []
    for path in sorted(kb_dir.rglob("*.md")):
        rel_path = str(path.relative_to(kb_dir))
        text = path.read_text(encoding="utf-8")
        all_chunks.extend(chunk_markdown_file(rel_path, text))
    return all_chunks
