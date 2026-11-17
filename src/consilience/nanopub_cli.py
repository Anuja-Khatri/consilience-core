"""The nanopublication commands of ``consilience`` (optional part).

    consilience export --nanopub <record.json> [--dry-run] [--unsigned] [--out FILE]
    consilience agent keygen | introduce [--dry-run]
    consilience templates publish [--dry-run] [--only KEY ...]

These need the ``nanopub`` extra (``pip install "consilience[nanopub]"``) and are run
from a source checkout of consilience-core, which holds the agent configuration,
templates and pilot records. Only the Knowledge Pixels test registry is supported;
there is no production option. Moved here unchanged from ``cli.py`` so that the core
commands do not need the nanopub dependencies.
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
PUBLICATIONS = REPO_ROOT / "pilot" / "publications.json"


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(p: Path, default):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def _write_json(p: Path, data) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _record_publication(logical: str, uri: str, file: Path, signer: str, note: str = "") -> None:
    pubs = _read_json(PUBLICATIONS, {})
    if logical in pubs:
        raise SystemExit(f"refusing: {logical} is already recorded as published ({pubs[logical]['nanopub']})")
    pubs[logical] = {
        "nanopub": uri,
        "registry": "test",
        "resolves_at": X.test_server_url(uri),
        "published": _now(),
        "supersedes": None,
        "signer": signer,
        "file": str(file.relative_to(REPO_ROOT)) if file.is_absolute() else str(file),
        "note": note,
    }
    _write_json(PUBLICATIONS, pubs)


def _sign_publish_check(ds, profile, out: Path, logical: str, dry_run: bool, note: str) -> str:
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
    _record_publication(logical, uri, out, signer, note)
    print(f"published to TEST registry: {uri}\n  resolves at {X.test_server_url(uri)}\n  wrote {out}")
    return uri


def cmd_export(args) -> int:
    cfg = AgentConfig.load(args.config)
    templates = _read_json(Path(args.templates), {})
    env = load_envelope(args.nanopub)
    agent_iri = cfg.agent_iri
    if not agent_iri:
        if not args.dry_run:
            raise SystemExit("the agent is not introduced yet: run `consilience agent introduce` first")
        agent_iri = "https://example.org/unintroduced-agent"  # dry run only, never signed
        args.unsigned = True
    ds = X.record_nanopub(env, agent_iri, templates, created=args.created)
    stem = Path(args.nanopub).stem
    default_dir = REPO_ROOT / ("tmp" if args.dry_run else "pilot/trig")
    out = Path(args.out) if args.out else default_dir / f"{stem}.trig"
    if args.dry_run and (args.unsigned or not _have_keys()):
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(X.to_trig(ds), encoding="utf-8")
        print(f"dry run: unsigned TriG written to {out}")
        return 0
    profile = profile_for(agent_iri, cfg.name)
    _sign_publish_check(ds, profile, out, f"record:{stem}", args.dry_run,
                        note=f"{env.record_type}; receipt {env.receipt_url}")
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
    if cfg.agent_iri and not args.dry_run:
        raise SystemExit(f"already introduced: {cfg.agent_iri}")
    _, pub = load_keys()
    ds = X.introduction_nanopub(cfg.name, cfg.local_name, pub, cfg.responsible_name,
                                cfg.responsible_orcid, created=args.created)
    temp_agent = str(S.TEMP_NS[cfg.local_name])
    profile = profile_for(temp_agent, cfg.name)
    out = REPO_ROOT / ("tmp" if args.dry_run else "agent") / "introduction.trig"
    uri = _sign_publish_check(ds, profile, out, "agent:introduction", args.dry_run,
                              note="self-signed introduction of the engine as a software agent")
    if not args.dry_run:
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
    profile = profile_for(cfg.agent_iri, cfg.name)
    published = _read_json(Path(args.templates), {})
    keys = args.only or list(S.ALL_SPECS)
    for key in keys:
        spec = S.ALL_SPECS[key]
        if key in published and not args.dry_run:
            print(f"skip {key}: already published ({published[key]})")
            continue
        ds = X.template_nanopub(spec, cfg.agent_iri, created=args.created)
        out = REPO_ROOT / ("tmp" if args.dry_run else "templates") / f"{key}.trig"
        uri = _sign_publish_check(ds, profile, out, f"template:{key}", args.dry_run,
                                  note=spec.label)
        if not args.dry_run:
            published[key] = f"{uri}/templateVersion"
            _write_json(Path(args.templates), published)
    return 0
