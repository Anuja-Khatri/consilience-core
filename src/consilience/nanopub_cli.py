"""The nanopublication commands of ``consilience`` (optional part).

    consilience export --nanopub <record.json> [--dry-run] [--unsigned] [--out FILE]
                       [--example] [--supersedes NANOPUB_URI]
    consilience agent keygen | introduce [--dry-run] [--replace]
    consilience templates publish [--dry-run] [--only KEY ...]

These need the ``nanopub`` extra (``pip install "consilience[nanopub]"``) and are run
from a source checkout of consilience-core, which holds the agent configuration,
templates and pilot records. Only the Knowledge Pixels test registry is supported;
there is no production option.

Claim cards are published before the records that refer to them: publishing a claim card
writes the claim IRI it introduces to ``pilot/claims.json``, and refusals and
disagreements read their claim A and claim B from there.
"""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

from . import __version__  # noqa: F401
from .agent import AgentConfig, AgentError, REPO_ROOT, TEST_REGISTRY_URL, generate_keys, \
    key_dir, load_keys, profile_for, signer_of  # noqa: F401
from .export import nanopub as X
from .export import spec as S
from .receipts import ReceiptError, load_envelope, verify  # noqa: F401

TEMPLATES_CONFIG = REPO_ROOT / "config" / "templates.json"
REVIEW_CONFIG = REPO_ROOT / "config" / "review.json"
PUBLICATIONS = REPO_ROOT / "pilot" / "publications.json"
CLAIMS = REPO_ROOT / "pilot" / "claims.json"
EXAMPLE_CLAIMS = REPO_ROOT / "pilot" / "examples" / "claims.json"


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(p: Path, default):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def _write_json(p: Path, data) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _rel(p: Path) -> str:
    p = Path(p)
    return str(p.resolve().relative_to(REPO_ROOT)) if p.is_absolute() else str(p)


def review_config() -> dict:
    """Who reviewed the theory claim cards, and what drafted them (config/review.json)."""
    r = _read_json(REVIEW_CONFIG, {})
    if not r.get("reviewer_orcid") or not r.get("drafted_by"):
        raise AgentError(f"incomplete_review_config: {REVIEW_CONFIG}")
    return {"reviewer": f"https://orcid.org/{r['reviewer_orcid']}", "drafted_by": r["drafted_by"]}


def _record_publication(logical: str, uri: str, file: Path, signer: str, note: str = "",
                        supersedes: str | None = None) -> None:
    pubs = _read_json(PUBLICATIONS, {})
    if logical in pubs:
        raise SystemExit(f"refusing: {logical} is already recorded as published ({pubs[logical]['nanopub']})")
    pubs[logical] = {
        "nanopub": uri,
        "registry": "test",
        "resolves_at": X.test_server_url(uri),
        "published": _now(),
        "supersedes": supersedes,
        "signer": signer,
        "file": _rel(file),
        "note": note,
    }
    _write_json(PUBLICATIONS, pubs)


def _sign_publish_check(ds, profile, out: Path, logical: str, dry_run: bool, note: str,
                        supersedes: str | None = None) -> str:
    uri, trig = X.sign(ds, profile)
    X.check_signed(trig)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(trig, encoding="utf-8")
    if dry_run:
        print(f"dry run: signed, not published: {uri}\n  wrote {out}")
        return uri
    X.publish_to_test_server(trig)
    back = X.fetch_from_test_server(uri)
    if X.check_signed(back) != uri:
        raise SystemExit(f"fetched nanopub does not match: {uri}")
    signer = signer_of(profile)
    if signer.startswith(str(S.TEMP_NS)):  # a self-signed introduction names its own sub-IRI
        signer = uri + "/" + signer[len(str(S.TEMP_NS)):]
    _record_publication(logical, uri, out, signer, note, supersedes)
    print(f"published to TEST registry: {uri}\n  resolves at {X.test_server_url(uri)}\n  wrote {out}")
    return uri


def _supersedes_entry(old_uri: str) -> dict:
    """What a corrected claim card needs to keep its claim IRI: the old nanopub and the IRI
    it introduced, read from pilot/claims.json."""
    for e in _read_json(CLAIMS, {}).values():
        if e.get("nanopub") == old_uri:
            return {"nanopub": old_uri, "introduces": e["claim_iri"]}
    raise SystemExit(f"{old_uri} is not a published claim card in {CLAIMS}")


def cmd_export(args) -> int:
    cfg = AgentConfig.load(args.config)
    templates = _read_json(Path(args.templates), {})
    env = load_envelope(args.nanopub)
    claims = X.Claims.load(EXAMPLE_CLAIMS if getattr(args, "example", False) else CLAIMS)
    agent_iri = cfg.agent_iri
    if not agent_iri:
        if not args.dry_run:
            raise SystemExit("the agent is not introduced yet: run `consilience agent introduce` first")
        agent_iri = "https://example.org/unintroduced-agent"  # dry run only, never signed
        args.unsigned = True
    supersedes = _supersedes_entry(args.supersedes) if getattr(args, "supersedes", None) else None
    review = review_config() if env.record_type == "theory_claim_card" else None
    if getattr(args, "example", False):
        ds = X.example_nanopub(env, agent_iri, templates, created=args.created, claims=claims)
    else:
        ds = X.record_nanopub(env, agent_iri, templates, created=args.created, claims=claims,
                              review=review, supersedes=supersedes)
    stem = Path(args.nanopub).stem
    trig_dir = "pilot/theories/trig" if "theories" in Path(args.nanopub).parts else "pilot/trig"
    if getattr(args, "example", False):
        trig_dir = "pilot/examples/trig"
    default_dir = REPO_ROOT / ("tmp" if args.dry_run else trig_dir)
    out = Path(args.out) if args.out else default_dir / f"{stem}.trig"
    if args.dry_run and (args.unsigned or not _have_keys()):
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(X.to_trig(ds), encoding="utf-8")
        print(f"dry run: unsigned TriG written to {out}")
        return 0
    profile = profile_for(agent_iri, cfg.name)
    logical = ("example:" if getattr(args, "example", False) else "record:") + stem
    uri = _sign_publish_check(ds, profile, out, logical, args.dry_run,
                              note=f"{env.record_type}; receipt {env.receipt_url}",
                              supersedes=supersedes["nanopub"] if supersedes else None)
    if (not args.dry_run and not getattr(args, "example", False)
            and env.record_type in ("claim_card", "theory_claim_card") and not supersedes):
        entries = _read_json(CLAIMS, {})
        entries[env.receipt_url] = {"claim_id": env.record["claim_id"], "claim_iri": f"{uri}/claim",
                                    "nanopub": uri, "envelope": _rel(Path(args.nanopub).resolve())}
        _write_json(CLAIMS, entries)
    return 0


def _have_keys() -> bool:
    try:
        load_keys()
        return True
    except AgentError:
        return False


def cmd_agent(args) -> int:
    cfg = AgentConfig.load(args.config)
    if args.action == "keygen":
        p = generate_keys()
        print(f"key written outside the repository: {p} (and {p}.pub)")
        return 0
    # introduce
    if cfg.agent_iri and not args.dry_run and not getattr(args, "replace", False):
        raise SystemExit(f"already introduced: {cfg.agent_iri} (use --replace for a new introduction)")
    if not cfg.responsible_orcid:
        raise SystemExit("the owner's ORCID iD is not in config/agent.json")
    _, pub = load_keys()
    ds = X.introduction_nanopub(cfg.name, cfg.local_name, pub, cfg.responsible_name,
                                cfg.responsible_orcid, created=args.created)
    temp_agent = str(S.TEMP_NS[cfg.local_name])
    profile = profile_for(temp_agent, cfg.name)
    out = REPO_ROOT / ("tmp" if args.dry_run else "agent") / "introduction.trig"
    uri = _sign_publish_check(ds, profile, out, "agent:introduction", args.dry_run,
                              note="self-signed introduction of the engine as a software agent, "
                                   "owned by its responsible person (frbr:owner, ORCID iD)")
    if not args.dry_run:
        if cfg.agent_iri:
            prev = cfg.data.setdefault("previous_introductions", [])
            prev.append({"agent_iri": cfg.agent_iri, "introduction_nanopub": cfg.data["introduction_nanopub"],
                         "replaced": _now()})
        cfg.data["agent_iri"] = f"{uri}/{cfg.local_name}"
        cfg.data["introduction_nanopub"] = uri
        cfg.data["public_key"] = pub
        cfg.save()
        print(f"agent IRI: {cfg.data['agent_iri']}")
    return 0


def cmd_templates(args) -> int:
    unknown = [k for k in (args.only or []) if k not in S.ALL_SPECS]
    if unknown:
        raise SystemExit(f"unknown template(s) {unknown}; known: {list(S.ALL_SPECS)}")
    cfg = AgentConfig.load(args.config)
    if not cfg.agent_iri:
        raise SystemExit("the agent is not introduced yet: run `consilience agent introduce` first")
    if not cfg.responsible_orcid:
        raise SystemExit("templates are attributed to the responsible person: add her ORCID iD")
    creator = f"https://orcid.org/{cfg.responsible_orcid}"
    profile = profile_for(cfg.agent_iri, cfg.name)
    published = _read_json(Path(args.templates), {})
    keys = args.only or list(S.ALL_SPECS)
    for key in keys:
        spec = S.ALL_SPECS[key]
        if key in published and not args.dry_run:
            print(f"skip {key}: already published ({published[key]})")
            continue
        ds = X.template_nanopub(spec, cfg.agent_iri, creator, cfg.responsible_name, created=args.created)
        out = REPO_ROOT / ("tmp" if args.dry_run else "templates") / f"{key}.trig"
        uri = _sign_publish_check(ds, profile, out, f"template:{key}", args.dry_run,
                                  note=spec.label)
        if not args.dry_run:
            published[key] = f"{uri}/templateVersion"
            _write_json(Path(args.templates), published)
    return 0
