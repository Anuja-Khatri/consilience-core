"""Fetch the study's ChEMBL records from the public ChEMBL web API, pinned and hashed.

    python studies/pooling-2026/fetch.py            # writes data/ (not committed)

For every target in targets.json: every activity of type IC50, Ki, Kd or EC50 with a
standard_value; then every assay those activities use. The public API fails on deep
offsets (offset 5,000 and beyond times out or returns HTTP 500 for EGFR, 20 Nov 2026), so
each target is fetched in slices by document year (and, if a single year is still large,
by measurement type), each slice small enough to need no deep offset. Completeness is
checked exactly: the slices' counts must add up to the target's total count, and the
union of activity ids must have that size. Each raw
API page is saved as returned, and data/MANIFEST.json lists every file with its SHA-256,
the ChEMBL release the API reported, and the time of the fetch. join.py then builds the
study's input table from these files only.

ChEMBL data: CC BY-SA 3.0 (cite Mendez et al. 2019, NAR 47:D930; keep ChEMBL ids; show
the release number). The raw files stay local; the joined table is released with the
dataset (step 6).
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
API = "https://www.ebi.ac.uk/chembl/api/data"
ACTIVITY_FIELDS = [
    "activity_id", "assay_chembl_id", "molecule_chembl_id", "parent_molecule_chembl_id",
    "target_chembl_id", "target_organism", "target_tax_id", "standard_type",
    "standard_relation", "standard_value", "standard_units", "pchembl_value",
    "data_validity_comment", "potential_duplicate", "assay_type", "bao_format",
    "assay_variant_mutation", "assay_variant_accession", "document_chembl_id",
    "document_year", "assay_description", "canonical_smiles"]
ASSAY_FIELDS = [
    "assay_chembl_id", "confidence_score", "assay_organism", "assay_category",
    "assay_tax_id", "assay_strain", "assay_tissue", "assay_cell_type",
    "assay_subcellular_fraction", "assay_parameters"]
PAGE = 1000
ASSAY_BATCH = 50
WORKERS = 4
MAX_SLICE = 4000


TRIES = 6


def get(url: str, tries: int = 0) -> bytes:
    tries = tries or TRIES
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json",
                                                       "User-Agent": "consilience-study"})
            with urllib.request.urlopen(req, timeout=120) as f:
                return f.read()
        except Exception as exc:  # noqa: BLE001 (retried, then raised)
            if i == tries - 1:
                raise
            wait = min(5 * (i + 1), 60)
            print(f"  retry {i + 1} after {exc!r} (waiting {wait}s)", flush=True)
            time.sleep(wait)
    raise AssertionError


def save(path: Path, data: bytes) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {"file": str(path.relative_to(DATA)), "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data)}


def _query(t: str, types: list, extra: dict, offset: int, limit: int = PAGE) -> dict:
    q = {"target_chembl_id": t, "standard_type__in": ",".join(types),
         "standard_value__isnull": "false", "order_by": "activity_id",
         "limit": limit, "offset": offset, "only": ",".join(ACTIVITY_FIELDS)}
    q.update(extra)
    return q


def _valid(acts: list) -> bool:
    """Every ChEMBL activity has an assay and a target. Under load the API sometimes
    returns whole pages with those joined fields blank (20 Nov 2026: 80 pages); such a
    page is fetched again, never used."""
    return all(a.get("assay_chembl_id") and a.get("target_chembl_id") for a in acts)


def _page(t, types, extra, offset, tag):
    url = f"{API}/activity.json?{urllib.parse.urlencode(_query(t, types, extra, offset))}"
    for attempt in range(8):
        raw = get(url)
        d = json.loads(raw)
        if _valid(d["activities"]):
            break
        print(f"  {t} {tag} offset {offset}: page with blank assay/target fields; "
              f"fetching again ({attempt + 1})", flush=True)
        time.sleep(10 * (attempt + 1))
    else:
        raise RuntimeError(f"{t} {tag} offset {offset}: blank assay/target fields after 8 tries")
    entry = save(DATA / "activity" / t / f"{tag}_{offset:05d}.json", raw)
    return d["page_meta"]["total_count"], d["activities"], entry


def _slices(t: str, types: list, pool) -> list:
    """Adaptive slices: (tag, filters, types). Each slice has at most MAX_SLICE rows."""
    first = [("y1900-1999", {"document_year__range": "1900,1999"}),
             ("y2000-2004", {"document_year__range": "2000,2004"}),
             ("y2005-2009", {"document_year__range": "2005,2009"}),
             ("y2010-2012", {"document_year__range": "2010,2012"}),
             ("y2013-2015", {"document_year__range": "2013,2015"}),
             ("y2016-2018", {"document_year__range": "2016,2018"}),
             ("y2019-2021", {"document_year__range": "2019,2021"}),
             ("y2022-2030", {"document_year__range": "2022,2030"}),
             ("ynull", {"document_year__isnull": "true"})]
    todo = [(tag, f, types) for tag, f in first]
    done = []
    while todo:
        futs = [(tag, f, ty, pool.submit(_page, t, ty, f, 0, tag)) for tag, f, ty in todo]
        todo = []
        for tag, f, ty, fu in futs:
            total, acts, entry = fu.result()
            if total <= MAX_SLICE:
                done.append({"tag": tag, "filters": f, "types": ty, "total": total,
                             "pages": [(0, acts, entry)]})
                continue
            # too large: split by year, then by type
            if "document_year__range" in f:
                a, b = (int(x) for x in f["document_year__range"].split(","))
                if b > a:
                    m = (a + b) // 2
                    todo.append((f"y{a}-{m}" + _tsuffix(ty, types), dict(f, document_year__range=f"{a},{m}"), ty))
                    todo.append((f"y{m + 1}-{b}" + _tsuffix(ty, types), dict(f, document_year__range=f"{m + 1},{b}"), ty))
                    continue
            if len(ty) > 1:
                for x in ty:
                    todo.append((tag.split("_t")[0] + f"_t{x}", f, [x]))
                continue
            raise RuntimeError(f"{t} slice {tag} ({f}, {ty}) has {total} rows and cannot "
                               "be split further")
    return done


def _tsuffix(ty, types):
    return "" if len(ty) == len(types) else f"_t{ty[0]}"


def _assay_page(i: int, batch: list) -> tuple:
    q = urllib.parse.urlencode({"assay_chembl_id__in": ",".join(batch),
                                "limit": ASSAY_BATCH, "only": ",".join(ASSAY_FIELDS)})
    raw = get(f"{API}/assay.json?{q}")
    got = len(json.loads(raw)["assays"])
    return got, save(DATA / "assay" / f"{i:07d}.json", raw)


def main() -> int:
    """``fetch.py`` fetches everything. ``fetch.py --resume`` re-fetches only the targets
    the manifest lists as missing (a retry, never a replacement), then the assays not yet
    fetched, and merges them into the same manifest."""
    from concurrent.futures import ThreadPoolExecutor
    global TRIES
    resume = "--resume" in sys.argv
    spec = json.loads((HERE / "targets.json").read_text(encoding="utf-8"))
    targets = [spec["demonstration"]] + spec["panel"]
    types = spec["standard_types"]
    status = json.loads(get(f"{API}/status.json"))
    if resume:
        TRIES = 12
        manifest = json.loads((DATA / "MANIFEST.json").read_text(encoding="utf-8"))
        if status.get("chembl_db_version") != manifest["chembl_db_version"]:
            raise SystemExit("ChEMBL release changed since the first fetch; start again")
        retry = [m["target"] for m in manifest["missing_targets"]]
        manifest["missing_targets"] = []
        manifest.setdefault("resumed_at", []).append(
            dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"))
        done_assays = set()
        for e in manifest["files"]:
            if e["file"].startswith("assay/"):
                done_assays.update(a["assay_chembl_id"] for a in
                                   json.loads((DATA / e["file"]).read_bytes())["assays"])
        targets_now = [t for t in targets if t in retry]
        print(f"resume: retrying {targets_now}", flush=True)
    else:
        manifest = {"fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                    "chembl_db_version": status.get("chembl_db_version"),
                    "chembl_release_date": status.get("chembl_release_date"),
                    "api": API, "targets": targets, "standard_types": types,
                    "method": "slices by document year (then type), offset < 4000 in each",
                    "files": [], "counts": {}, "slices": {}, "missing_targets": []}
        done_assays = set()
        targets_now = targets
    print(f"ChEMBL {manifest['chembl_db_version']} ({manifest['chembl_release_date']})",
          flush=True)
    assays: set = set()
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for t in targets_now:
            if resume:   # drop any partial files of this target from the first attempt
                manifest["files"] = [e for e in manifest["files"]
                                     if not e["file"].startswith(f"activity/{t}/")]
            try:
                total = json.loads(get(f"{API}/activity.json?" + urllib.parse.urlencode(
                    _query(t, types, {}, 0, limit=1))))["page_meta"]["total_count"]
                slices = _slices(t, types, pool)
                rest = []
                for sl in slices:
                    for off in range(PAGE, sl["total"], PAGE):
                        rest.append((sl, off, pool.submit(_page, t, sl["types"], sl["filters"],
                                                          off, sl["tag"])))
                for sl, off, fu in rest:
                    _, acts, entry = fu.result()
                    sl["pages"].append((off, acts, entry))
            except Exception as exc:  # noqa: BLE001 (reported, never replaced)
                print(f"{t}: FAILED ({exc!r}); reported as missing", flush=True)
                manifest["missing_targets"].append({"target": t, "error": repr(exc)})
                continue
            ids = set()
            for sl in slices:
                for _, acts, entry in sl["pages"]:
                    manifest["files"].append(entry)
                    ids.update(a["activity_id"] for a in acts)
                    assays.update(a["assay_chembl_id"] for a in acts if a.get("assay_chembl_id"))
            ssum = sum(sl["total"] for sl in slices)
            ok = (ssum == total == len(ids))
            manifest["counts"][t] = {"api_total": total, "slice_total": ssum,
                                     "unique_activities": len(ids), "complete": ok}
            manifest["slices"][t] = [{"tag": sl["tag"], "filters": sl["filters"],
                                      "types": sl["types"], "total": sl["total"]}
                                     for sl in slices]
            print(f"{t}: total {total}, slices {ssum}, unique {len(ids)}"
                  + ("" if ok else "  INCOMPLETE"), flush=True)
            if not ok:
                manifest["missing_targets"].append({"target": t, "error": "incomplete"})
        ids = sorted(assays - done_assays)
        print(f"assays: {len(ids)}", flush=True)
        offset0 = 0
        if resume:   # name new assay files after the existing ones
            offset0 = 1 + max((int(Path(e["file"]).stem) for e in manifest["files"]
                               if e["file"].startswith("assay/")), default=-1)
        futs = [(i, pool.submit(_assay_page, offset0 + i, ids[i:i + ASSAY_BATCH]))
                for i in range(0, len(ids), ASSAY_BATCH)]
        for i, f in futs:
            got, entry = f.result()
            if got != len(ids[i:i + ASSAY_BATCH]):
                print(f"  assay batch {i}: {got} of {len(ids[i:i + ASSAY_BATCH])}", flush=True)
            manifest["files"].append(entry)
    manifest["assays_requested"] = manifest.get("assays_requested", 0) + len(ids)
    manifest["files"].sort(key=lambda e: e["file"])
    (DATA / "MANIFEST.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    print("done", flush=True)
    return 0


def _tag_filters(tag: str, types: list) -> tuple:
    """Filters and types of a slice from its file tag (y2010-2012, ynull, y2016-2016_tIC50)."""
    base, _, tpart = tag.partition("_t")
    ty = [tpart] if tpart else list(types)
    if base == "ynull":
        return {"document_year__isnull": "true"}, ty
    a, b = base[1:].split("-")
    return {"document_year__range": f"{a},{b}"}, ty


def _from_disk(t: str, types: list) -> tuple:
    """Rebuild a target's leaf slices from the saved pages. Returns (slices, ids, ok_pages):
    a slice whose first page reports more than MAX_SLICE rows was split, so it is not a
    leaf and is left out."""
    d = DATA / "activity" / t
    by_tag: dict = {}
    for f in sorted(d.glob("*.json")):
        tag, off = f.stem.rsplit("_", 1)
        by_tag.setdefault(tag, {})[int(off)] = f
    slices, ids, ok = [], set(), True
    for tag, pages in sorted(by_tag.items()):
        if 0 not in pages:
            ok = False
            continue
        first = json.loads(pages[0].read_bytes())
        total = first["page_meta"]["total_count"]
        if total > MAX_SLICE:
            continue                       # split into smaller slices: not a leaf
        need = list(range(0, total, PAGE)) or [0]
        if any(o not in pages for o in need):
            ok = False
            continue
        f, ty = _tag_filters(tag, types)
        entries = []
        for o in need:
            raw = pages[o].read_bytes()
            acts = json.loads(raw)["activities"]
            if not _valid(acts):       # a damaged page saved earlier: fetch it again
                _, acts, _e = _page(t, ty, f, o, tag)
                raw = pages[o].read_bytes()
            ids.update(a["activity_id"] for a in acts)
            entries.append((o, acts, {"file": str(pages[o].relative_to(DATA)),
                                      "sha256": hashlib.sha256(raw).hexdigest(),
                                      "bytes": len(raw)}))
        slices.append({"tag": tag, "filters": f, "types": ty, "total": total,
                       "pages": entries})
    return slices, ids, ok


def recover() -> int:
    """``fetch.py --recover``: rebuild the manifest from the pages already saved (each
    target re-checked: leaf slices complete, slice counts = the API's total = unique
    ids), re-fetch whole any target that does not check out, then fetch the assays not
    yet saved, retrying failed batches in rounds instead of stopping."""
    from concurrent.futures import ThreadPoolExecutor
    global TRIES
    TRIES = 8
    spec = json.loads((HERE / "targets.json").read_text(encoding="utf-8"))
    targets = [spec["demonstration"]] + spec["panel"]
    types = spec["standard_types"]
    status = json.loads(get(f"{API}/status.json"))
    manifest = {"fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                "recovered": "manifest rebuilt from the saved pages, each target re-checked",
                "chembl_db_version": status.get("chembl_db_version"),
                "chembl_release_date": status.get("chembl_release_date"),
                "api": API, "targets": targets, "standard_types": types,
                "method": "slices by document year (then type), offset < 4000 in each",
                "files": [], "counts": {}, "slices": {}, "missing_targets": []}
    print(f"ChEMBL {manifest['chembl_db_version']} (recover)", flush=True)
    assays: set = set()
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for t in targets:
            total = json.loads(get(f"{API}/activity.json?" + urllib.parse.urlencode(
                _query(t, types, {}, 0, limit=1))))["page_meta"]["total_count"]
            slices, ids, ok = _from_disk(t, types)
            if not (ok and sum(s["total"] for s in slices) == total == len(ids)):
                print(f"{t}: saved pages incomplete; fetching again", flush=True)
                for f in (DATA / "activity" / t).glob("*.json"):
                    f.unlink()
                try:
                    slices = _slices(t, types, pool)
                    rest = [(sl, off, pool.submit(_page, t, sl["types"], sl["filters"],
                                                  off, sl["tag"]))
                            for sl in slices for off in range(PAGE, sl["total"], PAGE)]
                    for sl, off, fu in rest:
                        _, acts, entry = fu.result()
                        sl["pages"].append((off, acts, entry))
                except Exception as exc:  # noqa: BLE001 (reported, never replaced)
                    print(f"{t}: FAILED ({exc!r}); reported as missing", flush=True)
                    manifest["missing_targets"].append({"target": t, "error": repr(exc)})
                    continue
                ids = {a["activity_id"] for sl in slices for _, acts, _ in sl["pages"]
                       for a in acts}
            for sl in slices:
                for _, acts, entry in sl["pages"]:
                    manifest["files"].append(entry)
                    assays.update(a["assay_chembl_id"] for a in acts if a.get("assay_chembl_id"))
            ssum = sum(sl["total"] for sl in slices)
            good = ssum == total == len(ids)
            manifest["counts"][t] = {"api_total": total, "slice_total": ssum,
                                     "unique_activities": len(ids), "complete": good}
            manifest["slices"][t] = [{"tag": sl["tag"], "filters": sl["filters"],
                                      "types": sl["types"], "total": sl["total"]}
                                     for sl in slices]
            print(f"{t}: total {total}, slices {ssum}, unique {len(ids)}"
                  + ("" if good else "  INCOMPLETE"), flush=True)
            if not good:
                manifest["missing_targets"].append({"target": t, "error": "incomplete"})
        # assays: keep what is saved, fetch the rest in rounds
        have, nxt = set(), 0
        for f in sorted((DATA / "assay").glob("*.json")):
            raw = f.read_bytes()
            got = json.loads(raw)["assays"]
            have.update(a["assay_chembl_id"] for a in got)
            manifest["files"].append({"file": str(f.relative_to(DATA)),
                                      "sha256": hashlib.sha256(raw).hexdigest(),
                                      "bytes": len(raw)})
            nxt = max(nxt, int(f.stem) + 1)
        missing = sorted(assays - have)
        print(f"assays: {len(assays)} needed, {len(have & assays)} saved, {len(missing)} "
              "to fetch", flush=True)
        for rnd in range(6):
            if not missing:
                break
            batches = [missing[i:i + ASSAY_BATCH] for i in range(0, len(missing), ASSAY_BATCH)]
            futs = []
            for b in batches:
                futs.append((b, pool.submit(_assay_page, nxt, b)))
                nxt += 1
            failed = []
            for b, fu in futs:
                try:
                    _, entry = fu.result()
                    manifest["files"].append(entry)
                except Exception:  # noqa: BLE001 (retried next round)
                    failed.extend(b)
            missing = failed
            print(f"  round {rnd + 1}: {len(failed)} assays still to fetch", flush=True)
            if missing:
                time.sleep(60)
        got_all = set()
        for e in manifest["files"]:
            if e["file"].startswith("assay/"):
                got_all.update(a["assay_chembl_id"] for a in
                               json.loads((DATA / e["file"]).read_bytes())["assays"])
        manifest["assays_requested"] = len(assays)
        manifest["assays_returned"] = len(assays & got_all)
        manifest["assays_not_returned"] = sorted(assays - got_all)
    manifest["files"].sort(key=lambda e: e["file"])
    (DATA / "MANIFEST.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    print(f"done (assays returned {manifest['assays_returned']} of {len(assays)})", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(recover() if "--recover" in sys.argv else main())
