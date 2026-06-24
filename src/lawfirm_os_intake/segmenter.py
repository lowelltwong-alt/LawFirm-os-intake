from __future__ import annotations

import re

from .models import Segment, SourceBundle, SourceItem
from .util import digest_text, new_id


HEADER_RE = re.compile(r"^(From|To|Cc|Date|Subject):\s*(.*)$", re.IGNORECASE)
ATTACHMENT_RE = re.compile(r"\b(?:attached|attachment|enclosed|exhibit)\b", re.IGNORECASE)
INSTRUCTION_RISK_RE = re.compile(
    r"\b(ignore .*instructions|mark conflicts cleared|open a matter|send this message|docket)\b",
    re.IGNORECASE,
)
QUOTED_BOUNDARY_RE = re.compile(
    r"^(?:>+|On .+ wrote:|From:\s.+|-----Original Message-----)", re.IGNORECASE
)
MESSAGE_START_RE = re.compile(r"(?m)^From:\s.+$")


def _segment(
    source: SourceItem,
    segment_type: str,
    sequence: int,
    start: int,
    end: int,
    text: str,
    *,
    structural_path: str | None = None,
    message_index: int | None = None,
    attachment_ref: str | None = None,
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
        structural_path=structural_path,
        message_index=message_index,
        attachment_ref=attachment_ref,
        source_instruction_risk=bool(INSTRUCTION_RISK_RE.search(text)),
    )


def _email_segments_from_text(
    source: SourceItem,
    text: str,
    *,
    base_offset: int = 0,
    sequence_start: int = 0,
    message_index: int = 0,
) -> list[Segment]:
    lines = text.splitlines(keepends=True)
    segments: list[Segment] = []
    offset = 0
    sequence = sequence_start
    body_start = 0
    in_header_block = True

    for line in lines:
        stripped = line.rstrip("\r\n")
        if in_header_block and HEADER_RE.match(stripped):
            segments.append(
                _segment(
                    source,
                    "email_header",
                    sequence,
                    base_offset + offset,
                    base_offset + offset + len(line),
                    stripped,
                    structural_path=f"{source.source_id}/message[{message_index}]/header[{sequence}]",
                    message_index=message_index,
                )
            )
            sequence += 1
            body_start = offset + len(line)
        elif in_header_block and stripped == "":
            body_start = offset + len(line)
            in_header_block = False
        elif stripped != "":
            in_header_block = False
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
        first_line = next((line.strip() for line in block_text.splitlines() if line.strip()), "")
        if all(line.lstrip().startswith(">") for line in block_text.splitlines() if line.strip()):
            kind = "quoted_email"
        elif QUOTED_BOUNDARY_RE.match(first_line):
            kind = "quoted_email"
        elif block_text.startswith("--") or re.search(r"\bRegards,|\bSincerely,", block_text, re.I):
            kind = "signature"
        elif ATTACHMENT_RE.search(block_text):
            kind = "attachment_reference"
        else:
            kind = "email_body"
        segments.append(
            _segment(
                source,
                kind,
                sequence,
                base_offset + local_start,
                base_offset + local_end,
                block_text,
                structural_path=f"{source.source_id}/message[{message_index}]/{kind}[{sequence}]",
                message_index=message_index,
                attachment_ref=f"{source.source_id}:attachment_ref:{sequence}"
                if kind == "attachment_reference"
                else None,
            )
        )
        sequence += 1
        cursor = local_end
    return segments


def _email_segments(source: SourceItem) -> list[Segment]:
    return _email_segments_from_text(source, source.text)


def _correspondence_fallback_segments(source: SourceItem) -> list[Segment]:
    text = source.text
    segments: list[Segment] = []
    sequence = 0
    pattern = r"\S(?:.*?\S)?(?=\n\s*(?:---+|={3,}|From:|\Z))"
    for match in re.finditer(pattern, text, re.S | re.M):
        value = match.group(0).strip()
        if not value:
            continue
        kind = "attachment_reference" if ATTACHMENT_RE.search(value) else "correspondence_dump_item"
        segments.append(
            _segment(
                source,
                kind,
                sequence,
                match.start(),
                match.end(),
                value,
                structural_path=f"{source.source_id}/{kind}[{sequence}]",
                attachment_ref=f"{source.source_id}:attachment_ref:{sequence}"
                if kind == "attachment_reference"
                else None,
            )
        )
        sequence += 1
    return segments


def _correspondence_dump_segments(source: SourceItem) -> list[Segment]:
    text = source.text
    message_starts = [match.start() for match in MESSAGE_START_RE.finditer(text)]
    if not message_starts:
        return _correspondence_fallback_segments(source)

    segments: list[Segment] = []
    sequence = 0
    if message_starts[0] > 0:
        preamble = text[: message_starts[0]].strip()
        if preamble:
            preamble_start = text.find(preamble)
            segments.append(
                _segment(
                    source,
                    "correspondence_dump_preamble",
                    sequence,
                    preamble_start,
                    preamble_start + len(preamble),
                    preamble,
                    structural_path=f"{source.source_id}/preamble[0]",
                )
            )
            sequence += 1

    for message_index, start in enumerate(message_starts):
        end = (
            message_starts[message_index + 1]
            if message_index + 1 < len(message_starts)
            else len(text)
        )
        raw_message = text[start:end]
        message_text = raw_message.strip("\r\n -")
        if not message_text:
            continue
        message_start = start + raw_message.find(message_text)
        message_segments = _email_segments_from_text(
            source,
            message_text,
            base_offset=message_start,
            sequence_start=sequence,
            message_index=message_index,
        )
        segments.extend(message_segments)
        if message_segments:
            sequence = max(segment.sequence for segment in message_segments) + 1
    return segments


def _paragraph_segments(source: SourceItem) -> list[Segment]:
    if source.source_type == "correspondence_dump":
        return _correspondence_dump_segments(source)

    text = source.text
    segments: list[Segment] = []
    sequence = 0
    pattern = r"\S(?:.*?\S)?(?=\n\s*\n|\Z)"
    for match in re.finditer(pattern, text, re.S | re.M):
        value = match.group(0).strip()
        if not value:
            continue
        kind = {
            "letter": "letter_paragraph",
            "party_list": "party_list_block",
            "public_docket_stub": "public_metadata_block",
            "correspondence_dump": "correspondence_dump_item",
        }.get(source.source_type, "document_paragraph")
        if ATTACHMENT_RE.search(value):
            kind = "attachment_reference"
        segments.append(
            _segment(
                source,
                kind,
                sequence,
                match.start(),
                match.end(),
                value,
                structural_path=f"{source.source_id}/{kind}[{sequence}]",
                attachment_ref=f"{source.source_id}:attachment_ref:{sequence}"
                if kind == "attachment_reference"
                else None,
            )
        )
        sequence += 1
    if not segments and text:
        segments.append(
            _segment(
                source,
                "document_text",
                0,
                0,
                len(text),
                text,
                structural_path=f"{source.source_id}/document_text[0]",
            )
        )
    return segments


def segment_bundle(bundle: SourceBundle) -> list[Segment]:
    segments: list[Segment] = []
    for source in bundle.sources:
        if source.source_type == "email":
            segments.extend(_email_segments(source))
        else:
            segments.extend(_paragraph_segments(source))
    return segments
