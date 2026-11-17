"""Write PILOT.md from config/, pilot/records/ and pilot/publications.json."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REG = "https://test.registry.knowledgepixels.com/np/"
THEORY = sorted((ROOT / "pilot" / "theories" / "records").glob("*.json"))

sys.path.insert(0, str(ROOT / "scripts"))
import build_theory_records as T  # noqa: E402


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def code(uri):
    return uri.rsplit("/", 1)[-1]


def link(uri):
    return f"[`{code(uri)[:12]}…`]({REG}{code(uri)})"


def describe(env):
    r, t = env["record"], env["record_type"]
    if t == "claim_card":
        q = r["quantity"]
        bound = "" if q["bound"] == "exact" else f" ({q['bound']} bound)"
        return (f"Claim card: {r['subject']}, {r['axis'].replace('_', ' ')} {q['value']:g} {q['unit']}"
                f"{bound}, from `{r['source_document']}`.")
    ds = r["defects"]
    unstated = [d["target"].replace("_", " ") for d in ds if d["defect_type"] == "condition_unstated"]
    differs = [d["target"] for d in ds if d["defect_type"] == "condition_mismatch"]
    rules = env["context"].get("condition_rules", {})
    parts = []
    if r["outcome"] == "axis_mismatch":
        parts.append("the two claims are on different quantity axes ("
                     + ds[0]["target"].replace("_", " ") + ")")
    for rid in differs:
        parts.append(f"{', '.join(f.replace('_', ' ') for f in rules.get(rid, [rid]))} differs (rule {rid})")
    if unstated:
        parts.append("not stated in the claim cards: " + ", ".join(unstated))
    return f"Comparison of `{r['claim_a_id']}` with `{r['claim_b_id']}` refused: " + "; ".join(parts) + "."


def main():
    agent = load(ROOT / "config" / "agent.json")
    templates = load(ROOT / "config" / "templates.json")
    pubs = load(ROOT / "pilot" / "publications.json")
    labels = {
        "graded_correspondence": "(a) claim A corresponds to claim B at grade X",
        "comparison_refusal": "(b) comparison refused: condition C differs or is not stated",
        "testable_disagreement": "(c) this disagreement is testable now with instrument Y",
        "data_quality_finding": "(d) data-quality finding",
        "claim_card": "claim card (used by the pilot's claim cards)",
        "theory_claim_card": "theory claim card (used by the cross-theory claim cards)",
        "receipt_provenance": "provenance: the receipt (used by every record)",
    }
    out = []
    w = out.append
    w("# Knowledge Pixels pilot: Consilience records as nanopublications (TEST server)")
    w("")
    w("Everything listed here is published on the Knowledge Pixels **test** registry only. "
      "Nothing is on the live nanopublication network. The `https://w3id.org/np/…` "
      "identifiers inside the files resolve only on the live network, so the links below go "
      "to the test registry (`" + REG + "<id>`).")
    w("")
    w("The records in the first part come from the public [consilience-ledger]"
      "(https://github.com/Anuja-Khatri/consilience-ledger) at commit "
      "`7c1f9235b582666403537dd929c844e4b2dfc8cf` (branch `wp1-public-truth`). The "
      "cross-theory records in the section [COGITATE](#cogitate-the-cross-theory-comparison-iit-and-gnwt) "
      "come from the public [theconsilience-engine](" + T.REPO + ") at commit "
      "`" + T.ENGINE_COMMIT + "`. Each record links back to the exact lines of its source "
      "record at its commit, and carries that record's content hash; `pytest` checks that "
      "the hashes reproduce.")
    w("")
    w("## The publishing agent")
    w("")
    intro = agent["introduction_nanopub"]
    w(f"- **{agent['agent_name']}**, declared as a software agent (`npx:SoftwareAgent`, "
      f"`npx:SoftwareTool`): agent IRI `{agent['agent_iri']}`.")
    w(f"- Introduction (declares its public key; self-signed): {link(intro)}")
    w(f"- Responsible person: {agent['responsible_person_name']} (name only for now; an ORCID iD "
      "is to be added before any live publication).")
    w("")
    w("## Templates")
    w("")
    w("| Template | Test-server link | Instances in this pilot |")
    w("|---|---|---|")
    counts = {}
    for env_path in sorted((ROOT / "pilot" / "records").glob("*.json")) + THEORY:
        t = load(env_path)["record_type"]
        counts[t] = counts.get(t, 0) + 1
    counts["receipt_provenance"] = sum(counts.values())
    for key in ("graded_correspondence", "comparison_refusal", "testable_disagreement",
                "data_quality_finding", "claim_card", "theory_claim_card", "receipt_provenance"):
        w(f"| {labels[key]} | {link(templates[key].rsplit('/', 1)[0])} | {counts.get(key, 0)} |")
    w("")
    w("Templates (a) and (d) have no instance in this pilot. The public ledger holds no "
      "graded correspondence, the cross-theory demo's correspondences are all drafts, and "
      "data-quality findings are shared with the dataset's maintainers before anything about "
      "them is published. Template (c) is used only by the cross-theory records. The theory "
      "claim card template was added for them: a theory's claim states a commitment, not a "
      "measured quantity, and its statement is a reviewed paraphrase rather than an exact "
      "source sentence, so the measured-quantity claim card does not fit. The exporter "
      "supports every type and the tests check each against its template.")
    w("")
    w("## Records from the claims ledger")
    w("")
    w("| # | Type | What it says | Test-server link | Source receipt |")
    w("|---|---|---|---|---|")
    for env_path in sorted((ROOT / "pilot" / "records").glob("*.json")):
        env = load(env_path)
        p = pubs[f"record:{env_path.stem}"]
        typ = "claim card" if env["record_type"] == "claim_card" else "refused comparison"
        rec = env["source"]["path"].rsplit("/", 1)[-1] + "#L" + "-L".join(map(str, env["source"]["lines"]))
        w(f"| {env_path.stem[:2]} | {typ} | {describe(env)} | {link(p['nanopub'])} | "
          f"[{rec}]({env['source']['receipt_url']}) |")
    w("")
    w("Source documents: `2609.30133` is arXiv:2609.30133; `ref40_peng2023` is Peng et al., "
      "National Science Review 10, nwac108 (2023), doi:10.1093/nsr/nwac108. A refused "
      "comparison records what the two claim cards, as extracted from their source "
      "sentences, allow under the ledger's rule set (`comparability-v0.1`); it is not a "
      "judgement of either paper.")
    w("")
    w("Record 04 refers to the claim cards published as 01 and 02, record 06 to 01, and "
      "records 07 and 08 to 03: a refusal names its two claims by the same links (the claim "
      "cards' lines at the pinned commit) that the claim-card nanopubs describe.")
    w("")
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
    cogitate(w, pubs)
    (ROOT / "PILOT.md").write_text("\n".join(out), encoding="utf-8")


COGITATE = "2 of 3 after a disclosed re-review, originally 1 of 3, p = 0.075"


def words(v):
    return v.replace("_", " ")


def cogitate(w, pubs):
    """The cross-theory section. Counts are computed from the pinned receipt."""
    j = json.loads(T.engine_file(T.JUDGE))
    orch = json.loads(T.engine_file("results/demo/files/iitxorch-or_judge.json"))
    cards = {load(p)["record"]["claim_id"]: (p, load(p)) for p in THEORY
             if load(p)["record_type"] == "theory_claim_card"}
    forks = [(p, load(p)) for p in THEORY if load(p)["record_type"] == "testable_disagreement"]
    no_obs = sum(1 for f in j["forks"] if f["decidability"] == "now"
                 and not (f.get("sketch") or {}).get("shared_observables"))
    not_now = sum(1 for f in j["forks"] if f["decidability"] != "now")
    orch_not_now = sum(1 for f in orch["forks"] if f["decidability"] != "now")
    orch_now = len(orch["forks"]) - orch_not_now
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
      "below links to exact lines of those files and carries its content hash.")
    w("")
    w("**The COGITATE blind test.** The demo was checked blind against the preregistered "
      "predictions of the COGITATE adversarial collaboration (IIT against GNWT): "
      f"**{COGITATE}** against a 1,000-key permutation null. That is suggestive only. Method "
      "and full numbers: [10.5281/zenodo.23672883](https://zenodo.org/records/23672883). "
      "There is no record for this test: none of the templates fits a recovery score, so "
      "it is reported here and in the receipt README, not as a nanopublication.")
    w("")
    w("**What is published.** The demo finds three distinct IIT-against-GNWT disagreements "
      "that it rules testable with instruments that exist today: where consciousness is "
      "located, its time course, and connectivity. They involve eight claim pairs. The "
      "testable-disagreement template takes exactly one claim A and one claim B, so there is "
      "one record per claim pair (eight), grouped below under the three disagreements, plus "
      "one claim card for each of the eleven claims involved.")
    w("")
    w("**How to read the claim statements.** Each claim statement is a paraphrase of the "
      "theory paper, drafted by a language model and reviewed by a person. **It is not a "
      "quotation.** Each claim card gives the source document and the page(s) it rests on; a "
      "page is the page of the PDF the demo read, which can differ from the printed page "
      "number. Every record says this in its publication info, and every claim card states "
      "`cv:statementForm cv:ReviewedParaphrase`. A testable disagreement is a statement about "
      "two claim cards, not a verdict on either theory.")
    w("")
    w("### The three disagreements")
    w("")
    w("| # | Disagreement | Claim pair | What it says | Test-server link | Source receipt |")
    w("|---|---|---|---|---|---|")
    for p, env in forks:
        r = env["record"]
        a, b = r["left_ids"][0], r["right_ids"][0]
        say = (f"IIT's claim ({words(r['left_value'])}) and GNWT's claim "
               f"({words(r['right_value'])}) take different values on {words(r['axis'])}; the "
               f"demo rules this testable now with {env['context']['instrument']}.")
        if r["type_divergence"]:
            say += " The demo notes the two are different kinds of claim."
        rec = "#L" + "-L".join(map(str, env["source"]["lines"]))
        w(f"| T{p.stem[:2]} | {env['context']['disagreement']} | `{a}` vs `{b}` | {say} | "
          f"{link(pubs['record:' + p.stem]['nanopub'])} | [{rec}]({env['source']['receipt_url']}) |")
    w("")
    w("### The claim cards")
    w("")
    w("| # | Claim | Theory | Value on its axis | Statement (a reviewed paraphrase, not a quotation) | Pages | Test-server link | Source receipt |")
    w("|---|---|---|---|---|---|---|---|")
    for cid, (p, env) in cards.items():
        r = env["record"]
        by_doc = {}
        for x in r["prov"]:
            u = env["context"]["documents"][x["id"].rsplit("_", 1)[0]]
            by_doc.setdefault(u, set()).add(x["locator"])
        where = "; ".join(", ".join(sorted(v, key=lambda s: int(s[2:]))) + f" of [{u.split('doi.org/')[1]}]({u})"
                          for u, v in by_doc.items())
        rec = "#L" + "-L".join(map(str, env["source"]["lines"]))
        w(f"| T{p.stem[:2]} | `{cid}` | {r['theory']} | {words(r['axis'])}: {words(r['value'])} | "
          f"{r['statement']} | {where} | {link(pubs['record:' + p.stem]['nanopub'])} | "
          f"[{rec}]({env['source']['receipt_url']}) |")
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
      "measure), so there is no instrument to name.")
    w(f"- {not_now} IIT-against-GNWT and {orch_not_now} IIT-against-Orch-OR disagreements that "
      "the demo rules not decidable with current instruments; the template says \"testable "
      "now\"." + (f" ({orch_now} other IIT-against-Orch-OR forks are not covered.)" if orch_now else ""))
    w(f"- All {n_corr} correspondences: the demo marks "
      + ("every one" if drafts == n_corr else f"{drafts} of them") + " as a draft. Publishing "
      "them would present drafts as verdicts.")
    w("- The demo's other theory pairs, which its run manifest does not cover.")
    w("")
    w("These records report what the demo's comparison found in the published theory papers. "
      "They claim no new finding about consciousness.")
    w("")


if __name__ == "__main__":
    main()
