"""Build record envelopes for the cross-theory demo's testable disagreements and the
claim cards they involve, from the receipts pinned in the public engine repository.

The receipts are the demo's result files, committed with a manifest of SHA-256 hashes in
https://github.com/Anuja-Khatri/theconsilience-engine (results/demo/) at ENGINE_COMMIT.
This script reads them at that commit (from a local clone if CONSILIENCE_ENGINE_DIR
points at one, otherwise from raw.githubusercontent.com), checks every file against the
manifest at the same commit, and writes:

    pilot/theories/records/<nn>-theory-claim-card-<claim>.json
    pilot/theories/records/<nn>-disagreement-<a>--<b>.json

Each envelope links to the exact lines of its record at the pinned commit and carries
the record's content hash (json-sha256-v0). The record inside is the object at those
lines, unchanged. Output is deterministic.

    python scripts/build_theory_records.py
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from consilience.export.nanopub import DEMO_FORK, demo_instrument  # noqa: E402
from consilience.receipts import JSON_METHOD, SCHEMA, json_hash  # noqa: E402

REPO = "https://github.com/Anuja-Khatri/theconsilience-engine"
RAW = "https://raw.githubusercontent.com/Anuja-Khatri/theconsilience-engine"
ENGINE_COMMIT = "96ba4e435bd13718d36435cc3436d938d2d1f894"
JUDGE = "results/demo/files/iitxgnwt_judge.json"
MANIFEST = "results/demo/MANIFEST.json"
OUT = ROOT / "pilot" / "theories" / "records"

# Passage-id prefix -> the document the page locators refer to. For gnwt_science_2017 the
# demo read the 2021 reprint, so the reprint is named (its pages are the ones cited).
DOCUMENTS = {
    "iit_3_0": "https://doi.org/10.1371/journal.pcbi.1003588",
    "iit_4_0": "https://doi.org/10.1371/journal.pcbi.1011465",
    "iit_nrn_2016": "https://doi.org/10.1038/nrn.2016.44",
    "gnwt_neuron_2011": "https://doi.org/10.1016/j.neuron.2011.03.018",
    "gnwt_neuron_2020": "https://doi.org/10.1016/j.neuron.2020.01.026",
    "gnwt_science_2017": "https://doi.org/10.1007/978-3-030-54173-6_4",
}

# The three distinct disagreements the eight claim pairs fall into.
GROUPS = {"locus": "location", "temporal_profile": "time course", "connectivity": "connectivity"}

SOURCE_NOTE = (
    "From the Consilience cross-theory demo (consilience-demo.netlify.app); its results are "
    f"pinned in {REPO} at commit {ENGINE_COMMIT}, results/demo/. "
)
CARD_NOTE = SOURCE_NOTE + (
    "The claim statement is a paraphrase of the source paper, drafted by a language model "
    "and reviewed by a person. It is not a quotation. Page locators are pages of the PDF "
    "the demo read, which can differ from printed page numbers."
)
FORK_NOTE = SOURCE_NOTE + (
    "The demo's check rules this disagreement decidable with instruments that exist today "
    "and names the shared observable both claims bear on. This is a statement about the "
    "two claim cards, not a verdict on either theory. The axis is an axis of theoretical "
    "commitment, not a quantity axis, so no margin or floor applies. The claim statements "
    "in the linked claim cards are reviewed paraphrases with page locators, not quotations."
)


def engine_file(path: str) -> str:
    local = os.environ.get("CONSILIENCE_ENGINE_DIR")
    if local:
        r = subprocess.run(["git", "-C", local, "show", f"{ENGINE_COMMIT}:{path}"],
                           capture_output=True, text=True)
        if r.returncode == 0:
            return r.stdout
    with urllib.request.urlopen(f"{RAW}/{ENGINE_COMMIT}/{path}", timeout=60) as r:
        return r.read().decode("utf-8")


def line_range(text: str, obj: dict, indent: int) -> tuple[int, int]:
    """1-based lines of ``obj`` in a json.dumps(indent=2) file, where the object's braces
    sit at ``indent`` spaces. Fails unless exactly one block re-parses to ``obj``."""
    lines = text.split("\n")
    pad = " " * indent
    hits = []
    for i, ln in enumerate(lines):
        if ln != pad + "{":
            continue
        for j in range(i + 1, len(lines)):
            if lines[j] in (pad + "}", pad + "},"):
                if json.loads("\n".join(lines[i:j + 1]).rstrip(",")) == obj:
                    hits.append((i + 1, j + 1))
                break
    if len(hits) != 1:
        raise SystemExit(f"record not found exactly once ({len(hits)}): {str(obj)[:80]}")
    return hits[0]


def envelope(record_type, text, obj, indent, file_sha, context):
    s, e = line_range(text, obj, indent)
    url = f"{REPO}/blob/{ENGINE_COMMIT}/{JUDGE}#L{s}-L{e}"
    return {
        "schema": SCHEMA,
        "record_type": record_type,
        "source": {"repository": REPO, "commit": ENGINE_COMMIT, "path": JUDGE, "lines": [s, e],
                   "receipt_url": url, "file_sha256": file_sha},
        "receipt": {"content_hash": json_hash(obj), "hash_method": JSON_METHOD},
        "context": context,
        "record": obj,
    }


def main() -> int:
    manifest = json.loads(engine_file(MANIFEST))
    want = {f["path"]: f["sha256"] for f in manifest["files"]}
    text = engine_file(JUDGE)
    file_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if want.get(JUDGE) != file_sha:
        raise SystemExit(f"{JUDGE} hashes to {file_sha}, manifest says {want.get(JUDGE)}")
    j = json.loads(text)
    nodes = {n["claim_id"]: n for side in ("left", "right") for n in j[side]["nodes"]}

    forks = []
    for f in j["forks"]:
        if (f["decidability"] == "now" and len(f["left_ids"]) == 1 and len(f["right_ids"]) == 1
                and (f.get("sketch") or {}).get("shared_observables")):
            forks.append(f)
    order = list(GROUPS)
    forks.sort(key=lambda f: (order.index(f["axis"]), f["left_ids"][0], f["right_ids"][0]))
    claims = []
    for f in forks:
        for cid in (f["left_ids"][0], f["right_ids"][0]):
            if cid not in claims:
                claims.append(cid)

    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.json"):
        old.unlink()
    card_url = {}
    n = 0
    for cid in claims:
        n += 1
        env = envelope("theory_claim_card", text, nodes[cid], 6, file_sha,
                       {"documents": {p: DOCUMENTS[p] for p in sorted(DOCUMENTS)
                                      if any(x["id"].startswith(p + "_") for x in nodes[cid]["prov"])},
                        "pubinfo_note": CARD_NOTE})
        card_url[cid] = env["source"]["receipt_url"]
        (OUT / f"{n:02d}-theory-claim-card-{cid}.json").write_text(
            json.dumps(env, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for f in forks:
        n += 1
        a, b = f["left_ids"][0], f["right_ids"][0]
        env = envelope("testable_disagreement", text, f, 4, file_sha, {
            "record_format": DEMO_FORK,
            "disagreement": GROUPS[f["axis"]],
            "claim_a_receipt_url": card_url[a],
            "claim_b_receipt_url": card_url[b],
            "testability": "testable_now",
            "instrument": demo_instrument(f),
            "pubinfo_note": FORK_NOTE + (
                f" The demo marks this pair as a type divergence: the two claims are different "
                f"kinds of claim ({nodes[a]['entity_type']} and {nodes[b]['entity_type']})."
                if f["type_divergence"] else ""),
        })
        (OUT / f"{n:02d}-disagreement-{a}--{b}.json").write_text(
            json.dumps(env, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(claims)} claim cards, {len(forks)} disagreements -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
