from __future__ import annotations

import re

from .models import Segment, SourceBundle, SourceItem
from .util import digest_text, new_id


HEADER_RE = re.compile(r"^(From|To|Cc|Date|Subject):\s*(.*)$", re.IGNORECASE)


def _segment(
    source: SourceItem, segment_type: str, sequence: int, start: int, end: int, text: str
) -> Segment:
    return Segment(
        segment_id=new_id("seg"),
        source_id=source.source_id,
        segment_type=segment_type,
        sequence=sequence,
        start_offset=start,
        end_offset=end,
        sha256=digest_text(text),
        text=text,
    )


def _email_segments(source: SourceItem) -> list[Segment]:
    text = source.text
    lines = text.splitlines(keepends=True)
    segments: list[Segment] = []
    offset = 0
    sequence = 0
    body_start = 0

    for line in lines:
        stripped = line.rstrip("\r\n")
        if HEADER_RE.match(stripped):
            segments.append(
                _segment(source, "email_header", sequence, offset, offset + len(line), stripped)
            )
            sequence += 1
            body_start = offset + len(line)
        elif stripped == "" and body_start <= offset:
            body_start = offset + len(line)
        offset += len(line)

    body = text[body_start:]
    cursor = body_start
    blocks = re.split(r"(\n\s*\n)", body)
    for block in blocks:
        if not block.strip():
            cursor += len(block)
            continue
        block_text = block.strip("\r\n")
        local_start = text.find(block_text, cursor)
        if local_start < 0:
            local_start = cursor
        local_end = local_start + len(block_text)
        if all(line.lstrip().startswith(">") for line in block_text.splitlines() if line.strip()):
            kind = "quoted_email"
        elif block_text.startswith("--") or re.search(r"\bRegards,|\bSincerely,", block_text, re.I):
            kind = "signature"
        else:
            kind = "email_body"
        segments.append(_segment(source, kind, sequence, local_start, local_end, block_text))
        sequence += 1
        cursor = local_end
    return segments


def _paragraph_segments(source: SourceItem) -> list[Segment]:
    text = source.text
    segments: list[Segment] = []
    sequence = 0
    for match in re.finditer(r"\S(?:.*?\S)?(?=\n\s*\n|\Z)", text, re.S):
        value = match.group(0).strip()
        if not value:
            continue
        kind = {
            "letter": "letter_paragraph",
            "party_list": "party_list_block",
            "public_docket_stub": "public_metadata_block",
        }.get(source.source_type, "document_paragraph")
        segments.append(_segment(source, kind, sequence, match.start(), match.end(), value))
        sequence += 1
    if not segments and text:
        segments.append(_segment(source, "document_text", 0, 0, len(text), text))
    return segments


def segment_bundle(bundle: SourceBundle) -> list[Segment]:
    segments: list[Segment] = []
    for source in bundle.sources:
        if source.source_type == "email":
            segments.extend(_email_segments(source))
        else:
            segments.extend(_paragraph_segments(source))
    return segments
