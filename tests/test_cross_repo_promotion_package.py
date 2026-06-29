from pathlib import Path

from lawfirm_os_intake.models import CrossRepoPromotionPackage
from lawfirm_os_intake.util import load_json


REQUIRED_TARGET_REPOS = {
    "LawFirm-os-semantic-substrate",
    "LawFirm-os-orchestrator",
    "LawFirm-os-exceptions-lake-runtime",
    "LawFirm-os-skills-registry",
    "LawFirm-os-legal-knowledge-runtime",
}

REQUIRED_PROPOSAL_TYPES = {
    "schema_contract",
    "event_label_mapping",
    "workflow_interface",
    "lake_evidence_mapping",
    "skill_metadata",
    "context_bundle_interface",
}

REQUIRED_PROPOSAL_IDS = {
    "substrate.intake-source-and-evidence-refs.v0_1",
    "substrate.human-confirmation-and-candidates.v0_1",
    "substrate.budget-and-event-labels.v0_1",
    "orchestrator.workflow-human-pauses-evidence-packet.v0_1",
    "orchestrator.carrier-rejection-capture-appeal.v0_1",
    "lake.intake-budget-evidence-mapping.v0_1",
    "lake.carrier-rejection-admission.v0_1",
    "skills.intake-specialist-metadata.v0_1",
    "lkr.context-bundle-source-passage-claim-refs.v0_1",
}


def test_cross_repo_promotion_package_is_candidate_only_and_complete(repo_root):
    package_path = repo_root / "promotion/cross_repo_promotion_package.json"
    package = CrossRepoPromotionPackage.model_validate(load_json(package_path))

    assert package.status == "candidate_only"
    assert package.reviewed_lock_status == "reviewed_seed_lock"
    assert set(package.target_repos) == REQUIRED_TARGET_REPOS
    assert {proposal.proposal_type for proposal in package.proposals} >= REQUIRED_PROPOSAL_TYPES
    assert {proposal.proposal_id for proposal in package.proposals} == REQUIRED_PROPOSAL_IDS
    assert package.no_canonical_mutation is True
    assert package.no_sibling_repo_writes is True
    assert package.no_external_writes_performed is True
    assert package.non_authoritative is True

    for proposal in package.proposals:
        assert proposal.non_authoritative is True
        assert proposal.direct_promotion_performed is False
        assert proposal.external_writes_performed is False
        assert proposal.candidate_artifact_refs
        assert proposal.proposed_contract_refs
        assert proposal.required_governance_actions
        assert proposal.promotion_blockers
        for artifact_ref in proposal.candidate_artifact_refs:
            assert (repo_root / artifact_ref).exists(), artifact_ref


def test_cross_repo_promotion_package_keeps_authority_boundaries_visible(repo_root):
    package = load_json(repo_root / "promotion/cross_repo_promotion_package.json")
    docs_text = (repo_root / "docs/cross-repo-promotion-package.md").read_text(encoding="utf-8")

    assert "not a direct promotion" in docs_text
    assert "does not mutate sibling repo authority" in docs_text
    assert "Stable components graduate through the owning sibling repo only" in docs_text
    assert package["promotion_rule"].startswith("Stable components graduate only")
    assert all(proposal["direct_promotion_performed"] is False for proposal in package["proposals"])
    assert all(proposal["external_writes_performed"] is False for proposal in package["proposals"])


def test_cross_repo_promotion_package_references_exported_schema(repo_root):
    schema_path = repo_root / "schemas/cross-repo-promotion-package.schema.json"
    proposal_schema_path = repo_root / "schemas/cross-repo-promotion-proposal.schema.json"

    assert isinstance(repo_root, Path)
    assert schema_path.exists()
    assert proposal_schema_path.exists()
