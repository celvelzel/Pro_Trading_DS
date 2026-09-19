"""Markdown heading/line parser; content remains untrusted text."""

from __future__ import annotations

import re

from ..schemas import ParsedSection, text_quality


def parse_markdown(content: bytes) -> list[ParsedSection]:
    text = content.decode("utf-8", errors="replace")
    text_quality(text)
    sections: list[ParsedSection] = []
    matches = list(re.finditer(r"^#{1,6}\s+(.+?)\s*$", text, flags=re.MULTILINE))
    if not matches:
        return [ParsedSection(text.strip(), None, None, 0, len(text))]
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        value = text[match.end() : end].strip()
        if value:
            sections.append(ParsedSection(value, match.group(1).strip(), None, match.end(), end))
    return sections
