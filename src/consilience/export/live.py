"""Publish the agreed set of records to a Knowledge Pixels registry, safely.

    python scripts/publish_live.py keygen                       # once, on the publishing machine
    python scripts/publish_live.py plan                         # sign everything, publish nothing
    python scripts/publish_live.py publish --confirm-permanent  # publish to the LIVE network

Nanopublications on the live network cannot be edited or deleted, so this command is
deliberately narrow:

* It publishes exactly what ``live/MANIFEST.json`` lists: the engine's introduction, the
  templates, and the COGITATE (IIT against GNWT) records, each envelope pinned by its
  SHA-256. Anything else is refused, and so is any envelope that mentions the claims
  ledger (the electrocatalysis records, held back by the owner), INTREPID or its theories.
* Publishing to the live network needs ``--confirm-permanent``. Without it, ``publish``
  refuses and ``plan`` only signs into a scratch folder.
* It keeps its own state (``agent.json``, ``templates.json``, ``claims.json``,
  ``publications.json``, the signed files and ``LIVE.md``) in a state folder that records
  which registry it belongs to, so test and live identities never mix.
* The key lives outside the repository (default ``~/.consilience-nanopub-live``). Losing it
  loses the ability to supersede what it signed, so back it up.
* Every nanopub is fetched back from the registry after publishing and must verify and
  match. A run that stops part-way can be resumed: what is already recorded is skipped.

``--registry test --state <dir>`` runs the same steps on the test registry, as a rehearsal.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import sys
import time
from pathlib import Path

import requests

from ..agent import AgentConfig, AgentError, REPO_ROOT, generate_keys, load_keys, profile_for, \
    signer_of
from ..receipts import ReceiptError, load_envelope, verify
from . import nanopub as X
from . import spec as S

REGISTRIES = {
    "test": "https://test.registry.knowledgepixels.com/np/",
    "live": "https://registry.knowledgepixels.com/np/",
}
MANIFEST = REPO_ROOT / "live" / "MANIFEST.json"
DEFAULT_LIVE_STATE = REPO_ROOT / "live"
DEFAULT_LIVE_KEY_DIR = Path.home() / ".consilience-nanopub-live"
SOURCE_AGENT_CONFIG = REPO_ROOT / "config" / "agent.json"
ALLOWED_DIR = "pilot/theories/records"
ALLOWED_TYPES = {"theory_claim_card", "disagreement"}
FORBIDDEN_TEXT = ("consilience-ledger", "intrepid", "neurorepresentation", "active inference",
                  "active_inference", "nrep")


class LiveError(RuntimeError):
    """The live publication was refused. The message names the reason."""


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(p: Path, default):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def _write(p: Path, data) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ------------------------------------------------------------------------------ manifest

def load_manifest(path: Path = MANIFEST) -> dict:
    m = _read(path, None)
    if not m:
        raise LiveError(f"no_manifest: {path}")
    return m


def check_manifest(m: dict) -> list:
    """Every listed envelope must exist, match its hash, sit in the allowed folder, be of an
    allowed type, verify, and mention nothing held back. Returns the envelope paths in order."""
    paths = []
    for item in m["records"]:
        rel = item["path"]
        if not rel.startswith(ALLOWED_DIR + "/"):
            raise LiveError(f"not_in_allowed_folder: {rel}")
        p = REPO_ROOT / rel
        if not p.exists():
            raise LiveError(f"missing_envelope: {rel}")
        if _sha256(p) != item["sha256"]:
            raise LiveError(f"envelope_changed_since_manifest: {rel}")
        text = p.read_text(encoding="utf-8").lower()
        for bad in FORBIDDEN_TEXT:
            if bad in text:
                raise LiveError(f"held_back_content ({bad!r}) in {rel}")
        env = load_envelope(p)
        if env.record_type not in ALLOWED_TYPES:
            raise LiveError(f"record_type_not_allowed_live: {env.record_type} in {rel}")
        verify(env)
        paths.append(p)
    templates = m["templates"]
    unknown = [k for k in templates if k not in S.ALL_SPECS]
    if unknown:
        raise LiveError(f"unknown_templates_in_manifest: {unknown}")
    if m.get("examples"):
        raise LiveError("examples_not_allowed_live")
    return paths


# ------------------------------------------------------------------------------ registry

def publish(trig: str, registry: str, timeout: float = 60) -> str:
    uri = X.check_signed(trig)
    r = requests.post(REGISTRIES[registry], data=trig.encode("utf-8"),
                      headers={"Content-Type": "application/trig"}, timeout=timeout)
    if r.status_code >= 300:
        raise LiveError(f"{registry}_registry_rejected: HTTP {r.status_code}: {r.text[:300]}")
    return uri


def fetch(uri: str, registry: str, tries: int = 6, wait: float = 5.0) -> str:
    url = REGISTRIES[registry] + X.artifact_code(uri)
    last = None
    for _ in range(tries):
        r = requests.get(url, headers={"Accept": "application/trig"}, timeout=60)
        if r.status_code == 200:
            return r.text
        last = r.status_code
        time.sleep(wait)
    raise LiveError(f"not_resolvable_on_{registry}_registry: HTTP {last}: {uri}")


# ------------------------------------------------------------------------------ state

class State:
    def __init__(self, folder: Path, registry: str):
        self.dir = folder
        self.registry = registry
        self.agent_path = folder / "agent.json"
        self.templates_path = folder / "templates.json"
        self.claims_path = folder / "claims.json"
        self.pubs_path = folder / "publications.json"
        self.trig_dir = folder / "trig"

    def init(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        cfg = _read(self.agent_path, None)
        if cfg is None:
            src = _read(SOURCE_AGENT_CONFIG, None)
            if not src:
                raise LiveError(f"no_source_agent_config: {SOURCE_AGENT_CONFIG}")
            cfg = {k: src[k] for k in ("agent_name", "agent_local_name", "responsible_person_name",
                                        "responsible_person_orcid")}
            cfg.update(registry=self.registry, registry_url=REGISTRIES[self.registry],
                       agent_iri=None, introduction_nanopub=None, public_key=None)
            _write(self.agent_path, cfg)
        if cfg.get("registry") != self.registry:
            raise LiveError(f"state_folder_belongs_to_{cfg.get('registry')}_registry: {self.dir}")

    def agent(self) -> AgentConfig:
        return AgentConfig.load(self.agent_path)

    def pubs(self) -> dict:
        return _read(self.pubs_path, {})

    def record(self, logical: str, uri: str, out: Path, signer: str, note: str) -> None:
        pubs = self.pubs()
        pubs[logical] = {"nanopub": uri, "registry": self.registry,
                         "resolves_at": REGISTRIES[self.registry] + X.artifact_code(uri),
                         "published": _now(), "signer": signer,
                         "file": str(out.relative_to(self.dir)), "note": note}
        _write(self.pubs_path, pubs)


# ------------------------------------------------------------------------------ steps

def _sign(ds, profile, out: Path) -> tuple[str, str]:
    uri, trig = X.sign(ds, profile)
    X.check_signed(trig)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(trig, encoding="utf-8")
    return uri, trig


def _publish_one(st: State, ds, profile, out: Path, logical: str, note: str, really: bool) -> str:
    uri, trig = _sign(ds, profile, out)
    if not really:
        print(f"  signed, not published: {logical} -> {uri}")
        return uri
    publish(trig, st.registry)
    back = fetch(uri, st.registry)
    if X.check_signed(back) != uri:
        raise LiveError(f"fetched_nanopub_does_not_match: {uri}")
    signer = signer_of(profile)
    if signer.startswith(str(S.TEMP_NS)):
        signer = uri + "/" + signer[len(str(S.TEMP_NS)):]
    st.record(logical, uri, out, signer, note)
    print(f"  published to {st.registry.upper()}: {logical} -> {uri}")
    return uri


def run(st: State, manifest: dict, key_dir: Path, really: bool, created: str | None = None) -> None:
    paths = check_manifest(manifest)
    _, pub = load_keys(key_dir)
    st.init()
    cfg = st.agent()
    if not cfg.responsible_orcid:
        raise LiveError("the owner's ORCID iD is missing")
    done = st.pubs()
    out_root = st.trig_dir if really else st.dir / "plan-tmp"

    # 1. introduction
    if "agent:introduction" in done:
        if cfg.data.get("public_key") != pub:
            raise LiveError("the key in the key folder is not the key this identity was introduced with")
        agent_iri = cfg.agent_iri
        print(f"skip introduction: {cfg.data['introduction_nanopub']}")
    else:
        ds = X.introduction_nanopub(cfg.name, cfg.local_name, pub, cfg.responsible_name,
                                    cfg.responsible_orcid, created=created)
        temp = str(S.TEMP_NS[cfg.local_name])
        uri = _publish_one(st, ds, profile_for(temp, cfg.name, key_dir), out_root / "introduction.trig",
                           "agent:introduction", "self-signed introduction of the engine, owned by "
                           "its responsible person (frbr:owner, ORCID iD)", really)
        agent_iri = f"{uri}/{cfg.local_name}"
        if really:
            cfg.data.update(agent_iri=agent_iri, introduction_nanopub=uri, public_key=pub)
            cfg.save()
    profile = profile_for(agent_iri, cfg.name, key_dir)

    # 2. templates
    creator = f"https://orcid.org/{cfg.responsible_orcid}"
    templates = _read(st.templates_path, {})
    for key in manifest["templates"]:
        if key in templates:
            print(f"skip template {key}: {templates[key]}")
            continue
        spec = S.ALL_SPECS[key]
        ds = X.template_nanopub(spec, agent_iri, creator, cfg.responsible_name, created=created)
        uri = _publish_one(st, ds, profile, out_root / "templates" / f"{key}.trig",
                           f"template:{key}", spec.label, really)
        templates[key] = f"{uri}/templateVersion"
        if really:
            _write(st.templates_path, templates)

    # 3. records, claim cards first (the manifest order)
    from ..nanopub_cli import review_config
    review = review_config()
    claims = _read(st.claims_path, {})
    for p in paths:
        stem = p.stem
        logical = f"record:{stem}"
        if logical in done:
            print(f"skip {logical}: {done[logical]['nanopub']}")
            continue
        env = load_envelope(p)
        ds = X.record_nanopub(env, agent_iri, templates, created=created,
                              claims=X.Claims(claims, REPO_ROOT),
                              review=review if env.record_type == "theory_claim_card" else None)
        uri = _publish_one(st, ds, profile, out_root / "records" / f"{stem}.trig", logical,
                           f"{env.record_type}; receipt {env.receipt_url}", really)
        if env.record_type == "theory_claim_card":
            claims[env.receipt_url] = {"claim_id": env.record["claim_id"], "claim_iri": f"{uri}/claim",
                                       "nanopub": uri, "envelope": str(p.relative_to(REPO_ROOT))}
            if really:
                _write(st.claims_path, claims)
    if really:
        write_page(st)


def write_page(st: State) -> None:
    pubs = st.pubs()
    cfg = _read(st.agent_path, {})
    lines = [f"# Consilience on the Knowledge Pixels {st.registry} network", "",
             f"Registry: {REGISTRIES[st.registry]}", "",
             f"Agent: {cfg.get('agent_name')} — `{cfg.get('agent_iri')}`, owned by "
             f"https://orcid.org/{cfg.get('responsible_person_orcid')}", "",
             "Published by `scripts/publish_live.py` from `live/MANIFEST.json`. Nanopublications on "
             "the live network cannot be edited or deleted; corrections are new nanopubs that "
             "supersede old ones, signed with the same key.", "",
             "| What | Nanopub | Link |", "|---|---|---|"]
    for logical, e in pubs.items():
        lines.append(f"| {logical} | `{e['nanopub']}` | [{X.artifact_code(e['nanopub'])[:14]}…]({e['resolves_at']}) |")
    (st.dir / ("LIVE.md" if st.registry == "live" else "REHEARSAL.md")).write_text(
        "\n".join(lines) + "\n", encoding="utf-8")


# ------------------------------------------------------------------------------ CLI

def build_manifest() -> dict:
    """The agreed live set: all templates, the 11 COGITATE theory claim cards, then the 8
    IIT-vs-GNWT disagreements. Used to (re)write live/MANIFEST.json."""
    recs = sorted((REPO_ROOT / ALLOWED_DIR).glob("*.json"))
    cards = [p for p in recs if "-theory-claim-card-" in p.name]
    dis = [p for p in recs if "-disagreement-" in p.name]
    return {
        "what": "The live set agreed by the owner on 18 Nov 2026: the engine's introduction, all "
                "templates, and the COGITATE (IIT vs GNWT) theory claim cards and disagreements. "
                "Not included: the claims-ledger (electrocatalysis) records, INTREPID, example records.",
        "templates": list(S.ALL_SPECS),
        "examples": [],
        "records": [{"path": str(p.relative_to(REPO_ROOT)), "sha256": _sha256(p)} for p in cards + dis],
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="publish_live", description=__doc__.split("\n\n")[0])
    ap.add_argument("action", choices=["keygen", "plan", "publish", "write-manifest"])
    ap.add_argument("--registry", choices=["live", "test"], default="live")
    ap.add_argument("--state", help="state folder (default: live/ for the live registry; required for test)")
    ap.add_argument("--key-dir", help=f"key folder (default for live: {DEFAULT_LIVE_KEY_DIR})")
    ap.add_argument("--confirm-permanent", action="store_true",
                    help="required to publish to the live network (cannot be undone)")
    ap.add_argument("--created", help="override dct:created")
    a = ap.parse_args(argv)
    key_dir = Path(a.key_dir).expanduser() if a.key_dir else DEFAULT_LIVE_KEY_DIR
    try:
        if a.action == "write-manifest":
            _write(MANIFEST, build_manifest())
            print(f"wrote {MANIFEST}")
            return 0
        if a.action == "keygen":
            p = generate_keys(key_dir)
            print(f"key written outside the repository: {p} (and {p}.pub). BACK IT UP: without it "
                  "nothing published with it can be corrected by the same agent.")
            return 0
        if a.registry == "live":
            state_dir = Path(a.state) if a.state else DEFAULT_LIVE_STATE
        else:
            if not a.state:
                raise LiveError("--state is required with --registry test (keep rehearsals out of live/)")
            state_dir = Path(a.state)
            if state_dir.resolve() == DEFAULT_LIVE_STATE.resolve():
                raise LiveError("the live/ folder is for the live registry only")
        st = State(state_dir, a.registry)
        manifest = load_manifest()
        if a.action == "plan":
            run(st, manifest, key_dir, really=False, created=a.created)
            print(f"plan only: nothing was published. Signed files are in {st.dir / 'plan-tmp'}")
            return 0
        if a.registry == "live" and not a.confirm_permanent:
            raise LiveError("publishing to the LIVE network cannot be undone: add --confirm-permanent")
        run(st, manifest, key_dir, really=True, created=a.created)
        print(f"done. See {st.dir}")
        return 0
    except (LiveError, AgentError, X.ExportError, ReceiptError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
