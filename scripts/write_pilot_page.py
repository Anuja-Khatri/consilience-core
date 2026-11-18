"""Write PILOT.md from config/, pilot/ and archive/v1/ (the v2 pilot, test registry only)."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REG = "https://test.registry.knowledgepixels.com/np/"
LEDGER_RECORDS = sorted((ROOT / "pilot" / "records").glob("*.json"))
THEORY = sorted((ROOT / "pilot" / "theories" / "records").glob("*.json"))
EXAMPLES = sorted((ROOT / "pilot" / "examples").glob("example-*.json"))

sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
import build_theory_records as T  # noqa: E402
from consilience.export import nanopub as X  # noqa: E402
from consilience.receipts import load_envelope  # noqa: E402

GH = "https://github.com/Anuja-Khatri/consilience-core/blob/nanopub-v2/"
COGITATE = "2 of 3 after a disclosed re-review, originally 1 of 3, p = 0.075"


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def code(uri):
    return uri.rstrip("/").rsplit("/", 1)[-1]


def link(uri):
    return f"[`{code(uri)[:12]}…`]({REG}{code(uri)})"


def receipt(env):
    rec = env["source"]["path"].rsplit("/", 1)[-1] + "#L" + "-L".join(map(str, env["source"]["lines"]))
    return f"[{rec}]({env['source']['receipt_url']})"


def main():
    agent = load(ROOT / "config" / "agent.json")
    templates = load(ROOT / "config" / "templates.json")
    pubs = load(ROOT / "pilot" / "publications.json")
    v1 = load(ROOT / "archive" / "v1" / "pilot" / "publications.json")
    claims = X.Claims.load(ROOT / "pilot" / "claims.json")
    ex_claims = X.Claims.load(ROOT / "pilot" / "examples" / "claims.json")
    review = load(ROOT / "config" / "review.json")
    out = []
    w = out.append
    w("# Knowledge Pixels pilot, v2: Consilience records as nanopublications (TEST server)")
    w("")
    w("Everything listed here is published on the Knowledge Pixels **test** registry only. "
      "Nothing is on the live nanopublication network. The `https://w3id.org/np/…` "
      "identifiers inside the files resolve only on the live network, so the links below go "
      "to the test registry (`" + REG + "<id>`).")
    w("")
    w("This is **v2**, regenerated on 18 Nov 2026 after Tobias Kuhn (Knowledge Pixels) "
      "reviewed v1. The v1 records stay on the test registry; their files are in "
      "[`archive/v1/`](archive/v1/), and the table [v1 to v2](#v1-to-v2-old-and-new-uris) "
      "lists every old and new URI.")
    w("")
    w("- **Ledger records: test server only, held back from the live network.** The records "
      "in [Records from the claims ledger](#records-from-the-claims-ledger) are derived from "
      "electrocatalysis papers, one of them a Lila Sciences paper. The owner has decided to "
      "hold them back from the live network for now.")
    w("- **Trust on the live network.** The engine's key becomes trusted on the live network "
      "when someone already in the trust network approves its introduction. Tobias Kuhn "
      "offered to approve it, and the owner has accepted: once he is happy with v2, he "
      "approves the engine's introduction (`npx:approvesOf`). Anuja Khatri is not creating a "
      "key of her own for now. The templates are attributed to her ORCID iD and signed by the "
      "engine's key.")
    w("")
    w("The ledger records come from the public [consilience-ledger]"
      "(https://github.com/Anuja-Khatri/consilience-ledger) at commit "
      "`7c1f9235b582666403537dd929c844e4b2dfc8cf` (branch `wp1-public-truth`). The "
      "cross-theory records in [COGITATE](#cogitate-the-cross-theory-comparison-iit-and-gnwt) "
      "come from the public [theconsilience-engine](" + T.REPO + ") at commit "
      "`" + T.ENGINE_COMMIT + "`. Each record's provenance links back to the exact lines of its "
      "source record at its commit (the GitHub receipt) and carries that record's content "
      "hash; `pytest` checks that the hashes reproduce.")
    w("")
    changes(w)
    w("## The publishing agent")
    w("")
    w(f"- **{agent['agent_name']}**, a software agent (`npx:SoftwareAgent`, `npx:SoftwareTool`) "
      f"with its own key. Agent IRI: `{agent['agent_iri']}`.")
    w(f"- Introduction (declares its public key, self-signed, owner "
      f"`frbr:owner <https://orcid.org/{agent['responsible_person_orcid']}>`, "
      f"{agent['responsible_person_name']}): {link(agent['introduction_nanopub'])}. One line: "
      "the engine introduces itself, names its owner by ORCID iD and declares the public key "
      "everything below is signed with.")
    w(f"- The v1 introduction ({link(agent['previous_introductions'][0]['introduction_nanopub'])}) "
      "named the owner by name only. A new introduction gives a new agent IRI, so everything "
      "was regenerated with the new one.")
    w("")
    w("## Templates")
    w("")
    w("All seven are attributed to Anuja Khatri (`dct:creator` and `prov:wasAttributedTo` "
      f"`https://orcid.org/{agent['responsible_person_orcid']}`) and signed by the engine's key.")
    w("")
    w("| Template | What it is for | Test-server link | Records in this pilot |")
    w("|---|---|---|---|")
    counts = {}
    for p in LEDGER_RECORDS + THEORY:
        t = load(p)["record_type"]
        counts[t] = counts.get(t, 0) + 1
    counts["receipt_provenance"] = sum(counts.values())
    rows = [
        ("graded_correspondence", "(a) claim A corresponds to claim B at grade X",
         "a correspondence between two claim IRIs, with its grade and ceiling"),
        ("comparison_refusal", "(b) comparison refused",
         "a refused comparison: which condition is missing from which claim, which condition "
         "differs (both values and the unit), or which axes differ"),
        ("disagreement", "(c) claims A and B disagree on a dimension; testability and reason",
         "replaces v1's \"testable disagreement\": dimension, observables and instruments as "
         "separate fields, and testable now / under a stated assumption / not yet testable, "
         "always with the reason"),
        ("data_quality_finding", "(d) data-quality finding", "a check over a dataset, with counts"),
        ("claim_card", "measured claim (claim card)",
         "introduces a claim IRI for one measured claim: quantity as a QUDT value and unit, "
         "conditions as IRIs with values"),
        ("theory_claim_card", "theory claim (claim card)",
         "introduces a claim IRI for one claim of a theory: theory, dimension and position as IRIs"),
        ("receipt_provenance", "provenance: the receipt",
         "pinned commit, line range, content hash, versions; reviewer and what drafted the "
         "statement where a person reviewed it"),
    ]
    for key, name, what in rows:
        n = counts.get(key, 0)
        if key == "disagreement":
            n = counts.get("disagreement", 0) + counts.get("testable_disagreement", 0)
        w(f"| {name} | {what} | {link(templates[key].rsplit('/', 1)[0])} | {n} |")
    w("")
    w("**Example records.** The nanopub network sets up a type once a nanopublication of that "
      "type exists, and its convention is to bootstrap a new type with one "
      "`npx:ExampleNanopub` labelled \"Example: …\". Templates (a) and (d) have no real record "
      "in this pilot, so each has one example, with made-up data under example.org:")
    w("")
    for p in EXAMPLES:
        env = load_envelope(p)
        b = X.build_assertion(env, ex_claims)
        w(f"- {link(pubs['example:' + p.stem]['nanopub'])}: Example: {b.label}.")
    w("")
    w("The other templates' types are set up by their real records.")
    w("")
    ledger(w, pubs, claims)
    supersession(w, pubs, claims)
    cogitate(w, pubs, claims, review)
    mapping(w, pubs, v1)
    w("## Checking a record yourself")
    w("")
    w("```bash")
    w("consilience verify pilot/records/04-refusal-ref40_peng2023__002--ref40_peng2023__011.json")
    w("curl -H 'Accept: application/trig' " + REG + code(pubs["record:04-refusal-ref40_peng2023__002--ref40_peng2023__011"]["nanopub"]))
    w("```")
    w("")
    w("The first command recomputes the content hash from the record; the nanopub's "
      "provenance carries the same hash and the link to the record at the pinned commit.")
    w("")
    w("**Verified on 18 Nov 2026**, for every one of the "
      f"{len(pubs)} v2 nanopublications fetched back from the test registry: the trusty URI "
      "and the RSA signature verify; each record's assertion is exactly what the exporter "
      "builds from its envelope, and matches its template (our own check, and the "
      "nanopub-skill checkers `check-nanopub-conformance.py`, `check-template-conformance.py`, "
      "`template_links_check.py`, all clean); each content hash in the provenance equals the "
      "hash recomputed from the record, which equals the record at its pinned commit. The "
      "tests in [`tests/test_review_v2.py`](tests/test_review_v2.py), "
      "[`tests/test_trig.py`](tests/test_trig.py) and [`tests/test_theories.py`](tests/test_theories.py) "
      "check all of this.")
    w("")
    (ROOT / "PILOT.md").write_text("\n".join(out), encoding="utf-8")


def changes(w):
    t = GH + "tests/test_review_v2.py"
    w("## Changes from v1 (after review)")
    w("")
    w("Tobias Kuhn's review (18 Nov 2026) found v1 technically clean (valid signatures, "
      "records matching their templates) and asked for four design changes before going live.")
    w("")
    w("1. **Give claims their own identity.** v1 identified a claim by a GitHub line range, "
      "so a corrected card at a new commit would have orphaned every refusal pointing at it. "
      "Now each claim-card nanopub *introduces* its own claim IRI (`npx:introduces "
      "<…/claim>`), refusals and disagreements name claim A and claim B by those IRIs, and the "
      "GitHub receipt (pinned commit, line range, content hash) is in the provenance only. A "
      "corrected card supersedes the old one (`npx:supersedes`) and introduces the *same* "
      "claim IRI, so the links stay intact: see [Correcting a claim card](#correcting-a-claim-card-supersession). "
      "Every claim a refusal names now has a published claim card, so eight supporting claim "
      "cards (records 11 to 18) were added to the ten v1 ledger records. "
      f"Tests: [section 1 of `test_review_v2.py`]({t}).")
    w("2. **People in the provenance.** The agent introduction names Anuja Khatri's ORCID iD "
      "as `frbr:owner` (a new introduction, so the agent IRI changed). The templates are "
      "attributed to her ORCID iD and signed by the engine's key; on the live network, trust "
      "comes from Tobias Kuhn approving the engine's introduction, as he offered and the owner "
      "accepted. Each theory claim card names its reviewer (`cv:reviewedBy` her ORCID iD) and "
      "says it was drafted by a large language model (`cv:draftedBy \"a large language "
      "model\"`). By the owner's decision no model name or version is recorded. "
      f"Tests: `test_published_template_matches_its_spec_and_is_attributed_to_the_owner`, "
      f"`test_introduction_names_the_owner_by_orcid` ([test_trig.py]({GH}tests/test_trig.py)), "
      f"`test_signed_trig_matches_the_envelope` ([test_theories.py]({GH}tests/test_theories.py)).")
    w("3. **IRIs over strings.** Conditions, axes, units, techniques, theories, dimensions, "
      "positions and observables are IRIs. Existing vocabularies are reused where they fit "
      "(QUDT units and quantity kinds, ChEBI for the electrolyte, CHMO for "
      "chronopotentiometry, Wikidata for IIT); the rest are minted under `cv:` with labels, "
      "comments and SKOS mappings ([docs/VOCABULARY.md](docs/VOCABULARY.md)). Conditions are "
      "structured triples (condition IRI, number, unit IRI; or condition IRI and value IRI), "
      "not JSON strings. Refusals say which claim lacks a condition (record 04: only claim B "
      "lacks the electrolyte) and record a condition that differs with its IRI and both values "
      "(record 04: current density, 10 vs 100 mA/cm², rule CR2); the rule id is kept as a "
      f"separate field. Tests: [section 3 of `test_review_v2.py`]({t}).")
    w("4. **Template (c).** The \"testable disagreement\" template is replaced by a general "
      "disagreement template: claim A, claim B, the dimension of disagreement (an IRI), the "
      "observables and the instruments as separate fields, and a testability status from "
      "{testable now, testable under a stated assumption, not yet testable}, always with the "
      "reason. \"Not testable\" is no longer a value anywhere, and observables (such as "
      "regional decoding) are no longer filed as instruments; the theory claim template uses "
      "\"dimension\" and \"position\" instead of \"quantity axis\". One template serves both "
      "measured and theory disagreements (the margin, floor and unit are an optional group), so "
      f"no separate theory variant was needed. Tests: [section 4 of `test_review_v2.py`]({t}).")
    w("")


def ledger(w, pubs, claims):
    w("## Records from the claims ledger")
    w("")
    w("Test server only; held back from the live network by the owner's decision.")
    w("")
    w("| # | Type | What it says | Test-server link | Claim IRI (claim cards) | Source receipt |")
    w("|---|---|---|---|---|---|")
    for p in LEDGER_RECORDS:
        env = load(p)
        pub = pubs[f"record:{p.stem}"]
        b = X.build_assertion(load_envelope(p), claims)
        typ = "claim card" if env["record_type"] == "claim_card" else "refused comparison"
        if int(p.stem[:2]) > 10:
            typ = "supporting claim card"
        iri = f"`…/{code(pub['nanopub'])[:12]}…/claim`" if env["record_type"] == "claim_card" else ""
        w(f"| {p.stem[:2]} | {typ} | {b.label}. | {link(pub['nanopub'])} | {iri} | {receipt(env)} |")
    w("")
    w("Source documents: `2609.30133` is arXiv:2609.30133; `ref40_peng2023` is Peng et al., "
      "National Science Review 10, nwac108 (2023), doi:10.1093/nsr/nwac108. A refused "
      "comparison records what the two claim cards, as extracted from their source "
      "sentences, allow under the ledger's rule set (`comparability-v0.1`); it is not a "
      "judgement of either paper. Records 01 to 10 are the v1 pilot set; 11 to 18 are the "
      "claim cards of the other claims the refusals name, added in v2 so that every claim A "
      "and claim B is a claim IRI.")
    w("")


def supersession(w, pubs, claims):
    p01 = next(p for p in LEDGER_RECORDS if p.name.startswith("01-"))
    e = claims.entries[load(p01)["source"]["receipt_url"]]
    w("## Correcting a claim card (supersession)")
    w("")
    w("Nanopublications cannot be edited or deleted. If a claim card has to be corrected (for "
      "example, the ledger fixes the card at a new commit), the engine publishes a new "
      "claim-card nanopub that")
    w("")
    w(f"- states `npx:supersedes <old nanopub>` in its publication info (and names the "
      "Knowledge Pixels \"Supersedes previous version\" pubinfo template);")
    w("- introduces the **same** claim IRI, written out in full rather than as `sub:claim`, "
      "in the assertion and in `npx:introduces`;")
    w("- carries the new receipt (new commit, line range, content hash) in its provenance.")
    w("")
    w("Refusals and disagreements keep pointing at the claim IRI, so none of them needs "
      "republishing; readers follow the supersedes chain to the current card. It has to be "
      "signed with the same key as the old version, on the same network.")
    w("")
    w(f"A **dry run** (not published) is in [`docs/examples/supersede-claim-card-01.dry-run.trig`]"
      f"(docs/examples/supersede-claim-card-01.dry-run.trig): it supersedes claim card 01 "
      f"({link(e['nanopub'])}) and introduces `{e['claim_iri']}`, the IRI that refusals 04 and "
      "06 point at. Signed locally, it passed the nanopub-skill `supersede_check.py` (\"keeps "
      "every IRI that the superseded version introduces\") and `check-nanopub-conformance.py`. "
      "Command:")
    w("")
    w("```bash")
    w(f"consilience export --nanopub {p01.relative_to(ROOT)} --supersedes {e['nanopub']} --dry-run")
    w("```")
    w("")


def cogitate(w, pubs, claims, review):
    j = json.loads(T.engine_file(T.JUDGE))
    orch = json.loads(T.engine_file("results/demo/files/iitxorch-or_judge.json"))
    cards = [(p, load(p)) for p in THEORY if load(p)["record_type"] == "theory_claim_card"]
    forks = [(p, load(p)) for p in THEORY if load(p)["record_type"] in ("disagreement", "testable_disagreement")]
    no_obs = sum(1 for f in j["forks"] if f["decidability"] == "now"
                 and not (f.get("sketch") or {}).get("shared_observables"))
    not_now = sum(1 for f in j["forks"] if f["decidability"] != "now")
    orch_not_now = sum(1 for f in orch["forks"] if f["decidability"] != "now")
    n_corr = len(j["correspondences"]) + len(orch["correspondences"])
    drafts = sum(1 for c in j["correspondences"] + orch["correspondences"] if c["status"] == "draft")
    base = T.REPO + "/blob/" + T.ENGINE_COMMIT + "/"
    w("## COGITATE: the cross-theory comparison (IIT and GNWT)")
    w("")
    w("The Consilience consciousness-science demo ([consilience-demo.netlify.app]"
      "(https://consilience-demo.netlify.app)) compares theories of consciousness claim by "
      "claim. Its results for IIT against GNWT and IIT against Orch-OR are pinned, with "
      "their SHA-256 hashes, in the public engine repository at commit "
      f"`{T.ENGINE_COMMIT}`: [results/demo/]({base}results/demo/README.md). Every record "
      "below links to exact lines of those files in its provenance and carries its content hash.")
    w("")
    w("**The COGITATE blind test.** The demo was checked blind against the preregistered "
      "predictions of the COGITATE adversarial collaboration (IIT against GNWT): "
      f"**{COGITATE}** against a 1,000-key permutation null. That is suggestive only. Method "
      "and full numbers: [10.5281/zenodo.23672883](https://zenodo.org/records/23672883). "
      "There is no record for this test: none of the templates fits a recovery score, so "
      "it is reported here and in the receipt README, not as a nanopublication.")
    w("")
    w("**What is published.** The demo finds three distinct IIT-against-GNWT disagreements "
      "that it rules testable now: where consciousness is located, its time course, and "
      "connectivity. They involve eight claim pairs. The disagreement template takes exactly "
      "one claim A and one claim B, so there is one record per claim pair (eight), plus one "
      "claim card for each of the eleven claims involved. The demo names the observables each "
      "disagreement bears on; it names no instrument, so no instrument is recorded.")
    w("")
    w("**How to read the claim statements.** Each claim statement is a paraphrase of the "
      f"theory paper, drafted by {review['drafted_by']} and reviewed by "
      f"{review['reviewer_name']} (ORCID [{review['reviewer_orcid']}]"
      f"(https://orcid.org/{review['reviewer_orcid']})), who is named in each card's "
      "provenance. **It is not a quotation.** Each claim card gives the source document and "
      "the page(s) it rests on; a page is the page of the PDF the demo read, which can differ "
      "from the printed page number. Every claim card states `cv:statementForm "
      "cv:ReviewedParaphrase`. A disagreement is a statement about two claims, not a verdict "
      "on either theory.")
    w("")
    w("### The disagreements")
    w("")
    w("| # | Disagreement | Claim pair | What it says | Test-server link | Source receipt |")
    w("|---|---|---|---|---|---|")
    for p, env in forks:
        r = env["record"]
        b = X.build_assertion(load_envelope(p), claims)
        w(f"| T{p.stem[:2]} | {env['context']['disagreement']} | `{r['left_ids'][0]}` vs "
          f"`{r['right_ids'][0]}` | {b.label}. | {link(pubs['record:' + p.stem]['nanopub'])} | "
          f"{receipt(env)} |")
    w("")
    w("### The claim cards")
    w("")
    w("| # | Claim | What it says | Statement (a reviewed paraphrase, not a quotation) | Pages | Test-server link | Source receipt |")
    w("|---|---|---|---|---|---|---|")
    for p, env in cards:
        r = env["record"]
        b = X.build_assertion(load_envelope(p), claims)
        by_doc = {}
        for x in r["prov"]:
            u = env["context"]["documents"][x["id"].rsplit("_", 1)[0]]
            by_doc.setdefault(u, set()).add(x["locator"])
        where = "; ".join(", ".join(sorted(v, key=lambda s: int(s[2:]))) + f" of [{u.split('doi.org/')[1]}]({u})"
                          for u, v in by_doc.items())
        w(f"| T{p.stem[:2]} | `{r['claim_id']}` | {b.label}. | {r['statement']} | {where} | "
          f"{link(pubs['record:' + p.stem]['nanopub'])} | {receipt(env)} |")
    w("")
    w("Source documents: 10.1371/journal.pcbi.1003588 is Oizumi, Albantakis and Tononi "
      "(2014), IIT 3.0; 10.1038/nrn.2016.44 is Tononi, Boly, Massimini and Koch (2016); "
      "10.1016/j.neuron.2011.03.018 is Dehaene and Changeux (2011); "
      "10.1016/j.neuron.2020.01.026 is Mashour, Roelfsema, Changeux and Dehaene (2020); "
      "10.1007/978-3-030-54173-6_4 is the 2021 reprint of Dehaene, Lau and Kouider, \"What "
      "is consciousness, and could machines have it?\" (Science, 2017), which is the version "
      "the demo read.")
    w("")
    w("**Not published, and why.**")
    w("")
    w(f"- {no_obs} further IIT-against-GNWT disagreements that the demo calls decidable now "
      "but for which it names no shared observable (the disagreement is about what to "
      "measure).")
    w(f"- {not_now} IIT-against-GNWT and {orch_not_now} IIT-against-Orch-OR disagreements that "
      "the demo rules not decidable with current instruments. The v2 template could carry "
      "them as \"not yet testable\" with a reason; this pilot keeps to the set v1 published.")
    w(f"- All {n_corr} correspondences: the demo marks "
      + ("every one" if drafts == n_corr else f"{drafts} of them") + " as a draft. Publishing "
      "them would present drafts as verdicts.")
    w("- The demo's other theory pairs, which its run manifest does not cover.")
    w("")
    w("These records report what the demo's comparison found in the published theory papers. "
      "They claim no new finding about consciousness.")
    w("")


def mapping(w, pubs, v1):
    w("## v1 to v2: old and new URIs")
    w("")
    w("The v1 nanopublications stay on the test registry and are **not** superseded or "
      "retracted there. By the nanopub conventions, a supersede must keep every IRI the old "
      "version introduced, and v2 deliberately introduces new ones (a new agent IRI, claim "
      "IRIs); a retraction is for something that should not have been published, and v1 was "
      "a legitimate test. So the mapping is listed here instead. v1's signed files are in "
      "[`archive/v1/`](archive/v1/).")
    w("")
    w("| What | v1 (test) | v2 (test) |")
    w("|---|---|---|")
    pairs = [("agent introduction", "agent:introduction", "agent:introduction")]
    for k in ("graded_correspondence", "comparison_refusal", "data_quality_finding", "claim_card",
              "theory_claim_card", "receipt_provenance"):
        pairs.append((f"template {k.replace('_', ' ')}", f"template:{k}", f"template:{k}"))
    pairs.append(("template testable disagreement → disagreement", "template:testable_disagreement",
                  "template:disagreement"))
    for name in v1:
        if name.startswith("record:"):
            pairs.append((name[len("record:"):], name, name))
    for what, old, new in pairs:
        w(f"| {what} | {link(v1[old]['nanopub'])} | {link(pubs[new]['nanopub'])} |")
    for name in pubs:
        if name.startswith("record:") and name not in v1:
            w(f"| {name[len('record:'):]} (new in v2) | none | {link(pubs[name]['nanopub'])} |")
        if name.startswith("example:"):
            w(f"| {name[len('example:'):]} (new in v2) | none | {link(pubs[name]['nanopub'])} |")
    w("")


if __name__ == "__main__":
    main()
