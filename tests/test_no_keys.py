"""No signing key is in the tree or in git history, and nothing can publish to production."""

import inspect
import re
import subprocess

import pytest

from consilience import agent, cli
from consilience.export import nanopub as X
from conftest import ROOT

PRIVATE_MARKERS = re.compile(
    r"-----BEGIN (RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----|"
    r"\bMII[EJ][A-Za-z0-9+/]{1000,}")  # a bare base64 RSA private key body (PKCS#1/#8, 2048+ bit)


def _git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)


def _in_git_repo():
    r = _git("rev-parse", "--is-inside-work-tree")
    return r.returncode == 0 and r.stdout.strip() == "true"


def test_no_private_key_in_working_tree():
    offenders = []
    for p in ROOT.rglob("*"):
        if not p.is_file() or ".git" in p.parts or ".venv" in p.parts or "__pycache__" in p.parts:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if PRIVATE_MARKERS.search(text):
            offenders.append(str(p.relative_to(ROOT)))
    assert offenders == []


@pytest.mark.skipif(not _in_git_repo(), reason="not a git checkout")
def test_no_private_key_in_git_history():
    revs = _git("rev-list", "--all").stdout.split()
    assert revs, "no commits"
    for rev in revs:
        r = _git("grep", "-I", "-l", "-E", "BEGIN (RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY", rev)
        assert r.stdout.strip() == "", f"private key marker in {rev}: {r.stdout}"
    names = _git("log", "--all", "--name-only", "--pretty=format:").stdout.split()
    assert not [n for n in names if re.search(r"id_rsa(?!\.pub)|\.pem$|\.key$|private", n)], names


def test_local_key_body_is_not_in_the_tree():
    """If the engine's key exists on this machine, no tracked file contains any of it."""
    try:
        private_body, _ = agent.load_keys()
    except agent.AgentError:
        pytest.skip("no local key on this machine")
    probe = private_body[60:120]
    for p in ROOT.rglob("*"):
        if p.is_file() and ".git" not in p.parts:
            try:
                assert probe not in p.read_text(encoding="utf-8"), p
            except UnicodeDecodeError:
                pass


def test_gitignore_blocks_key_files():
    gi = (ROOT / ".gitignore").read_text()
    for pattern in ("*id_rsa*", "*.pem", "*.key", ".consilience-nanopub/", "profile.yml"):
        assert pattern in gi


def test_key_directory_must_be_outside_the_repository(tmp_path, monkeypatch):
    monkeypatch.setenv("CONSILIENCE_NANOPUB_KEY_DIR", str(ROOT / "keys"))
    with pytest.raises(agent.AgentError, match="key_dir_inside_repository"):
        agent.generate_keys()
    with pytest.raises(agent.AgentError, match="key_dir_inside_repository"):
        agent.load_keys()


def test_only_the_test_registry_exists_in_code():
    assert agent.TEST_REGISTRY_URL == "https://test.registry.knowledgepixels.com/np/"
    for mod in (agent, cli, X):
        src = inspect.getsource(mod)
        for live in ("https://registry.knowledgepixels.com", "registry.petapico.org",
                     "registry.np.trustyuri.net"):
            assert live not in src, (mod.__name__, live)


def test_publish_refuses_unsigned_input():
    with pytest.raises(Exception):
        X.publish_to_test_server("@prefix x: <http://example.org/> .")
