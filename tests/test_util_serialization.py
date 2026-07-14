"""Cross-platform byte invariants for hash-bound JSON artifacts."""

from lawfirm_os_intake.util import append_jsonl, write_json


def test_json_serializers_emit_canonical_lf_bytes(tmp_path):
    json_path = write_json(tmp_path / "artifact.json", {"synthetic": True})
    jsonl_path = append_jsonl(tmp_path / "ledger.jsonl", {"synthetic": True})
    append_jsonl(jsonl_path, {"sequence": 2})

    assert b"\r\n" not in json_path.read_bytes()
    assert b"\r\n" not in jsonl_path.read_bytes()
    assert json_path.read_bytes().endswith(b"\n")
    assert jsonl_path.read_bytes().endswith(b"\n")
