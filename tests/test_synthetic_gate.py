import json
import pytest

from lawfirm_os_intake.models import SourceBundle
from lawfirm_os_intake.workflow import _gate_bundle


def test_real_data_is_rejected(repo_root):
    data = json.loads((repo_root / "examples/synthetic/inbound/help-email.json").read_text())
    data["data_origin"] = "production"
    data["contains_real_client_data"] = True
    bundle = SourceBundle.model_validate(data)
    with pytest.raises(ValueError):
        _gate_bundle(bundle)
