"""Write PILOT.md from config/, pilot/records/ and pilot/publications.json."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REG = "https://test.registry.knowledgepixels.com/np/"


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
    w("All records come from the public [consilience-ledger]"
      "(https://github.com/Anuja-Khatri/consilience-ledger) at commit "
      "`7c1f9235b582666403537dd929c844e4b2dfc8cf` (branch `wp1-public-truth`). Each one links "
      "back to the exact lines of its source record at that commit, and carries that "
      "record's content hash; `pytest` checks that the hashes reproduce.")
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
    for env_path in sorted((ROOT / "pilot" / "records").glob("*.json")):
        t = load(env_path)["record_type"]
        counts[t] = counts.get(t, 0) + 1
    counts["receipt_provenance"] = sum(counts.values())
    for key in ("graded_correspondence", "comparison_refusal", "testable_disagreement",
                "data_quality_finding", "claim_card", "receipt_provenance"):
        w(f"| {labels[key]} | {link(templates[key].rsplit('/', 1)[0])} | {counts.get(key, 0)} |")
    w("")
    w("Templates (a), (c) and (d) have no instance in this pilot. The public ledger at this "
      "commit holds no graded correspondence and no fork (disagreement), and data-quality "
      "findings are shared with the dataset's maintainers before anything about them is "
      "published. The exporter supports all four types and the tests check each against "
      "its template.")
    w("")
    w("## Records")
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
    (ROOT / "PILOT.md").write_text("\n".join(out), encoding="utf-8")


if __name__ == "__main__":
    main()
