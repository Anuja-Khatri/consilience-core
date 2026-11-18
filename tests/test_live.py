"""Guards on the live publishing command (no network: nothing is published here)."""

import copy

import pytest

pytest.importorskip("nanopub")

from consilience.export import live as L  # noqa: E402


def test_manifest_is_current_and_only_cogitate():
    m = L.load_manifest()
    assert m == L.build_manifest(), "live/MANIFEST.json is stale: rerun write-manifest on purpose"
    paths = [r["path"] for r in m["records"]]
    assert len(paths) == 19
    assert all(p.startswith("pilot/theories/records/") for p in paths)
    assert m["examples"] == []
    assert len(L.check_manifest(m)) == 19


def test_refuses_changed_envelope():
    m = copy.deepcopy(L.load_manifest())
    m["records"][0]["sha256"] = "0" * 64
    with pytest.raises(L.LiveError, match="envelope_changed_since_manifest"):
        L.check_manifest(m)


def test_refuses_ledger_records_outside_allowed_folder():
    m = copy.deepcopy(L.load_manifest())
    m["records"].append({"path": "pilot/records/01-claim-card-ref40_peng2023__002.json", "sha256": "x"})
    with pytest.raises(L.LiveError, match="not_in_allowed_folder"):
        L.check_manifest(m)


def test_refuses_held_back_content(monkeypatch):
    monkeypatch.setattr(L, "ALLOWED_DIR", "pilot/records")
    p = L.REPO_ROOT / "pilot/records/01-claim-card-ref40_peng2023__002.json"
    m = {"templates": [], "examples": [], "records": [
        {"path": "pilot/records/01-claim-card-ref40_peng2023__002.json", "sha256": L._sha256(p)}]}
    with pytest.raises(L.LiveError, match="held_back_content"):
        L.check_manifest(m)


def test_refuses_examples():
    m = copy.deepcopy(L.load_manifest())
    m["examples"] = ["example-data-quality-finding"]
    with pytest.raises(L.LiveError, match="examples_not_allowed_live"):
        L.check_manifest(m)


def test_live_publish_needs_confirmation(tmp_path):
    rc = L.main(["publish", "--state", str(tmp_path / "s"), "--key-dir", str(tmp_path / "k")])
    assert rc == 2


def test_test_registry_cannot_use_live_folder(tmp_path):
    rc = L.main(["publish", "--registry", "test", "--state", str(L.DEFAULT_LIVE_STATE),
                 "--key-dir", str(tmp_path / "k")])
    assert rc == 2


def test_state_folder_cannot_switch_registry(tmp_path):
    st = L.State(tmp_path / "s", "test")
    st.init()
    with pytest.raises(L.LiveError, match="belongs_to_test"):
        L.State(tmp_path / "s", "live").init()
