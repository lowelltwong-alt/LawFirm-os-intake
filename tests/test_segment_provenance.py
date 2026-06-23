from lawfirm_os_intake.models import SourceBundle
from lawfirm_os_intake.segmenter import segment_bundle
from lawfirm_os_intake.util import digest_text, load_json


def test_segments_preserve_offsets_and_hashes(repo_root):
    bundle = SourceBundle.model_validate(
        load_json(repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json")
    )
    segments = segment_bundle(bundle)
    assert segments
    for segment in segments:
        assert segment.end_offset >= segment.start_offset
        assert segment.sha256 == digest_text(segment.text)
        assert segment.source_id
