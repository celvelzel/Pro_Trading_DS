"""Structure-first deterministic token-window chunker."""

from __future__ import annotations

import hashlib
import re

from .schemas import DocumentChunkData, ParsedSection


def chunk_sections(sections: list[ParsedSection], target_tokens: int = 700, overlap_tokens: int = 100) -> list[DocumentChunkData]:
    if not 100 <= target_tokens <= 1200 or not 0 <= overlap_tokens < target_tokens:
        raise ValueError("Invalid chunk window")
    chunks: list[DocumentChunkData] = []
    for section in sections:
        words = re.findall(r"\S+", section.text)
        if not words:
            continue
        start = 0
        while start < len(words):
            end = min(len(words), start + target_tokens)
            text = " ".join(words[start:end])
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            chunks.append(
                DocumentChunkData(
                    text=text,
                    section=section.section,
                    page=section.page,
                    char_start=section.char_start,
                    char_end=section.char_end,
                    token_count=end - start,
                    content_hash=digest,
                )
            )
            if end == len(words):
                break
            start = end - overlap_tokens
    return chunks
