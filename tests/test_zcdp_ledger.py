import json

import pytest

from lawfirm_os_intake.privacy import (
    SYNTHETIC_RESET_POLICY_PLACEHOLDER,
    SyntheticPrivacyScope,
    ZCDPBudgetExceeded,
    ZCDPLedger,
    zcdp_to_epsilon_delta,
)


def test_sequential_composition_and_bun_steinke_group_accounting(tmp_path):
    ledger = ZCDPLedger(
        tmp_path / "synthetic-ledger.jsonl", rho_cap=2.0, scope=SyntheticPrivacyScope()
    )
    ledger.append(release_id="one", rho=0.2)
    group_entry = ledger.append(release_id="group", rho=0.1, group_size=3)

    assert group_entry["effective_rho"] == pytest.approx(0.9)
    assert group_entry["group_privacy"] == "bun_steinke_k_squared_rho"
    assert ledger.consumed_rho == pytest.approx(1.1)
    assert ledger.remaining_rho == pytest.approx(0.9)
    assert ledger.reset_policy == SYNTHETIC_RESET_POLICY_PLACEHOLDER


def test_zcdp_to_epsilon_delta_conversion():
    report = zcdp_to_epsilon_delta(0.5, 1e-6)

    assert report.epsilon > report.rho
    assert report.delta == 1e-6
    assert report.formal_production_privacy_claimed is False


def test_cap_exhaustion_fails_before_write(tmp_path):
    path = tmp_path / "synthetic-ledger.jsonl"
    ledger = ZCDPLedger(path, rho_cap=0.5, scope=SyntheticPrivacyScope())
    ledger.append(release_id="fits", rho=0.4)
    before = path.read_text(encoding="utf-8")

    with pytest.raises(ZCDPBudgetExceeded, match="before ledger write"):
        ledger.append(release_id="blocked", rho=0.2)

    assert path.read_text(encoding="utf-8") == before


def test_reload_validation_and_tamper_detection(tmp_path):
    path = tmp_path / "synthetic-ledger.jsonl"
    ledger = ZCDPLedger(path, rho_cap=1.0, scope=SyntheticPrivacyScope())
    ledger.append(release_id="original", rho=0.1)

    reloaded = ZCDPLedger(path, rho_cap=1.0, scope=SyntheticPrivacyScope())
    assert reloaded.consumed_rho == pytest.approx(0.1)

    entry = json.loads(path.read_text(encoding="utf-8"))
    entry["rho"] = 0.9
    path.write_text(json.dumps(entry) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="hash validation"):
        ZCDPLedger(path, rho_cap=1.0, scope=SyntheticPrivacyScope())


def test_reload_rejects_policy_cap_drift(tmp_path):
    path = tmp_path / "synthetic-ledger.jsonl"
    ledger = ZCDPLedger(path, rho_cap=1.0, scope=SyntheticPrivacyScope())
    ledger.append(release_id="original", rho=0.1)

    with pytest.raises(ValueError, match="policy digest|rho cap"):
        ZCDPLedger(path, rho_cap=2.0, scope=SyntheticPrivacyScope())


def test_duplicate_release_id_is_rejected_without_second_write(tmp_path):
    path = tmp_path / "synthetic-ledger.jsonl"
    ledger = ZCDPLedger(path, rho_cap=1.0, scope=SyntheticPrivacyScope())
    ledger.append(release_id="same-release", rho=0.1)
    before = path.read_text(encoding="utf-8")

    with pytest.raises(ValueError, match="already contains"):
        ledger.append(release_id="same-release", rho=0.1)

    assert path.read_text(encoding="utf-8") == before


def test_ledger_rejects_non_synthetic_scope(tmp_path):
    with pytest.raises(ValueError):
        SyntheticPrivacyScope(contains_privileged_data=True)
