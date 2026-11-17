"""The Consilience engine as a declared software agent on the nanopublication network.

Keys are generated locally into a directory *outside* the repository (default
``~/.consilience-nanopub/``, override with ``CONSILIENCE_NANOPUB_KEY_DIR``) and are never
committed. The public agent configuration (name, agent IRI, introduction nanopub,
public key, responsible person) lives in ``config/agent.json`` in the repository.

Only the Knowledge Pixels *test* registry is supported. Publishing to the live network
is deliberately not implemented: nanopublications cannot be deleted, and production
publishing waits for the project owner's approval and ORCID iD.
"""

from __future__ import annotations

import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path

from Crypto.PublicKey import RSA

TEST_REGISTRY_URL = "https://test.registry.knowledgepixels.com/np/"
KEY_BASENAME = "consilience-engine_id_rsa"

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "config" / "agent.json"


class AgentError(RuntimeError):
    """The agent configuration or keys are not usable. The message names the reason."""


def key_dir() -> Path:
    env = os.environ.get("CONSILIENCE_NANOPUB_KEY_DIR")
    return Path(env).expanduser() if env else Path.home() / ".consilience-nanopub"


def _inside_repo(p: Path) -> bool:
    """True if ``p`` is inside this repository or inside any git working tree.

    The git check matters when the package is installed without ``-e``: REPO_ROOT then
    points into site-packages, and a key directory inside a clone would not be noticed.
    """
    rp = p.resolve()
    if any((d / ".git").exists() for d in (rp, *rp.parents)):
        return True
    try:
        rp.relative_to(REPO_ROOT)
        return True
    except ValueError:
        return False


def _pem_body(pem: str) -> str:
    return "".join(ln.strip() for ln in pem.splitlines() if ln and not ln.startswith("-----"))


@dataclass
class AgentConfig:
    path: Path
    data: dict

    @classmethod
    def load(cls, path: str | Path = DEFAULT_CONFIG) -> "AgentConfig":
        p = Path(path)
        try:
            return cls(p, json.loads(p.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError) as exc:
            raise AgentError(f"unreadable_agent_config: {p}: {exc}") from None

    def save(self) -> None:
        self.path.write_text(json.dumps(self.data, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    @property
    def name(self) -> str:
        return self.data["agent_name"]

    @property
    def local_name(self) -> str:
        return self.data["agent_local_name"]

    @property
    def agent_iri(self) -> str | None:
        return self.data.get("agent_iri") or None

    @property
    def responsible_name(self) -> str:
        return self.data["responsible_person_name"]

    @property
    def responsible_orcid(self) -> str | None:
        v = (self.data.get("responsible_person_orcid") or "").strip()
        return v or None


def generate_keys(directory: Path | None = None) -> Path:
    """Create a 2048-bit RSA key pair outside the repository. Refuses to overwrite."""
    d = directory or key_dir()
    if _inside_repo(d):
        raise AgentError(f"key_dir_inside_repository: {d}")
    d.mkdir(parents=True, exist_ok=True)
    os.chmod(d, stat.S_IRWXU)
    priv = d / KEY_BASENAME
    pub = d / (KEY_BASENAME + ".pub")
    if priv.exists() or pub.exists():
        raise AgentError(f"keys_already_exist: {priv} (never overwritten; losing a key loses "
                         "the ability to supersede or retract what it signed)")
    key = RSA.generate(2048)
    priv.write_bytes(key.export_key("PEM", pkcs=8))
    os.chmod(priv, stat.S_IRUSR | stat.S_IWUSR)
    pub.write_bytes(key.publickey().export_key("PEM"))
    return priv


def load_keys(directory: Path | None = None) -> tuple[str, str]:
    """Return (private_key_base64_body, public_key_base64_body)."""
    d = directory or key_dir()
    if _inside_repo(d):
        raise AgentError(f"key_dir_inside_repository: {d}")
    priv = d / KEY_BASENAME
    pub = d / (KEY_BASENAME + ".pub")
    if not priv.exists() or not pub.exists():
        raise AgentError(f"keys_not_found: {priv} (run `consilience agent keygen`)")
    return _pem_body(priv.read_text()), _pem_body(pub.read_text())


def profile_for(agent_iri: str, name: str, directory: Path | None = None):
    """A nanopub-py Profile that signs as ``agent_iri`` with the local key."""
    from nanopub import Profile

    private_key, public_key = load_keys(directory)
    try:  # nanopub >= 2.3 names the signer ``agent_id``
        return Profile(name=name, agent_id=agent_iri, private_key=private_key, public_key=public_key)
    except TypeError:  # nanopub 2.2.x calls it ``orcid_id`` but accepts any IRI
        return Profile(orcid_id=agent_iri, name=name, private_key=private_key, public_key=public_key)


def signer_of(profile) -> str:
    return getattr(profile, "agent_id", None) or profile.orcid_id
