def test_repo_contains_no_production_connector_modules(repo_root):
    source_files = list((repo_root / "src").rglob("*.py"))
    names = {path.name for path in source_files}
    forbidden = {"imanage.py", "gmail.py", "outlook.py", "conflicts_system.py", "carrier_portal.py"}
    assert not names.intersection(forbidden)


def test_prohibited_transitions_are_declared(repo_root):
    text = (repo_root / "workflow/prohibited-transitions.yaml").read_text()
    for phrase in [
        "matter_opened",
        "external_message_sent",
        "conflicts_cleared",
        "deadline_docketed",
        "budget_submitted",
        "imanage_workspace_created",
    ]:
        assert phrase in text
