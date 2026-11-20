# Live run, 20 Nov 2026

A headless Claude Code session (version 2.1.329 (Claude Code)) with this plugin loaded by `--plugin-dir`. It ran DeepMind's own ChEMBL skill script (`google-deepmind/science-skills` @370f8f3, `skills/chembl_database/scripts/chembl_api.py`) against the live ChEMBL API:

```bash
claude -p "Run this exact shell command once: python chembl_api.py activity --filter target_chembl_id=CHEMBL203 standard_type=IC50 --limit 10 --output egfr.json ... quote word for word any text that a hook added to your context" \
  --plugin-dir integrations/agent-plugin/consilience-pooling --allowedTools Bash
```

The agent's reply, verbatim (the long local paths are shortened to `<workdir>`):

The command ran successfully and wrote `egfr.json` (18,431 bytes). Note: this data comes from the ChEMBL Database — please review the ChEMBL licensing terms before using it.

The hook added this text, word for word:

```
Consilience pooling check (pack bioactivity-v1): 10 records, 4 groups (parent_molecule_chembl_id + target_chembl_id).
- 2 records left out by a rule: BR1 2.
- 2 groups contain records that must not be pooled together (more than one condition class).
  Pairs refused, by first reason: not_comparable(assay_type) 4.
- Pairs inside a class: 0 agree within 0.3 log units, 0 only within 1.0 log units, 2 disagree, 0 are two bounds that can both hold.
- 4 records are pool_valid (poolable with the others of their condition class).
- Not checked (column absent from the table): BA3, BA4, BA5, BA6, BA7, BA8, BA9, BR2.
- This fetch holds 10 of the 26600 matching records in ChEMBL. Pooling decisions need all records: fetch every page, then run /check-pooling on the combined file.
- Not checked here: assay organism, category, strain, tissue, cell type, subcellular fraction and confidence score. They come from ChEMBL's assay records (/assay), not from activity records.
- Outputs and receipt: <workdir>/consilience_receipts/20261120-072333/ (re-check with: consilience verify <workdir>/consilience_receipts/20261120-072333/receipt.json)
```

This shows:
- the hook found the records through the `output_file` that DeepMind's script prints;
- it said the fetch was 10 of 26,600 records;
- it named the rules it could not check without assay fields;
- it left a receipt.

The numbers describe only those 10 records and are not a finding.
