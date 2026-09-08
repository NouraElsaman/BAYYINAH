from __future__ import annotations

import re
import uuid
from dataclasses import dataclass


@dataclass
class ContractClauseChunk:
    clause_id: str
    text: str
    order: int


# Common Egyptian Arabic contract clause markers
CLAUSE_MARKERS = re.compile(
    r"(?:^|\n)\s*(?:البند|المادة|بند|الفصل)\s*(?:رقم\s*)?[\d٠-٩]+",
    re.MULTILINE,
)

NUMBERED_MARKERS = re.compile(r"(?:^|\n)\s*[\d٠-٩]{1,3}\s*[-.:]\s+", re.MULTILINE)


def chunk_contract(text: str, min_chunk_chars: int = 60, max_chunk_chars: int = 2000) -> list[ContractClauseChunk]:
    text = text.strip()
    if not text:
        return []

    splits = _split_on_pattern(text, CLAUSE_MARKERS)
    if len(splits) < 2:
        splits = _split_on_pattern(text, NUMBERED_MARKERS)
    if len(splits) < 2:
        splits = _split_on_paragraphs(text)

    chunks: list[ContractClauseChunk] = []
    order = 0
    buffer = ""

    for segment in splits:
        segment = segment.strip()
        if not segment:
            continue
        combined = (buffer + "\n" + segment).strip() if buffer else segment

        if len(combined) < min_chunk_chars:
            buffer = combined
            continue

        if len(combined) > max_chunk_chars:
            # Hard-split overly long segments
            for i in range(0, len(combined), max_chunk_chars):
                part = combined[i : i + max_chunk_chars].strip()
                if part:
                    chunks.append(ContractClauseChunk(clause_id=str(uuid.uuid4())[:8], text=part, order=order))
                    order += 1
            buffer = ""
            continue

        chunks.append(ContractClauseChunk(clause_id=str(uuid.uuid4())[:8], text=combined, order=order))
        order += 1
        buffer = ""

    if buffer:
        chunks.append(ContractClauseChunk(clause_id=str(uuid.uuid4())[:8], text=buffer, order=order))

    return chunks


def _split_on_pattern(text: str, pattern: re.Pattern) -> list[str]:
    matches = list(pattern.finditer(text))
    if not matches:
        return [text]

    segments = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        segments.append(text[start:end])
    # Include any preamble before the first marker
    if matches[0].start() > 0:
        segments.insert(0, text[: matches[0].start()])
    return segments


def _split_on_paragraphs(text: str) -> list[str]:
    return [p for p in re.split(r"\n\s*\n", text) if p.strip()]
