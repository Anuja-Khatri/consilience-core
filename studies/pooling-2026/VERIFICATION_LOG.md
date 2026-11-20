# Verification log

Every headline number is computed twice: by `run_study.py` (the engine) and by `check_independent.py` (pandas only; it does not import consilience). Any mismatch is resolved here before a number is reported. This file also records everything found while checking, including what went wrong.

## 20 Nov 2026, first full run (10:31): not reported; found problems

The first full run (EGFR and 29 targets) gave **32 mismatches** between the engine and the independent check. Resolved as follows.

1. **Condition text that starts with a digit was read as a quantity (engine side).** ChEMBL cell lines and strains such as "3T3-L1" start with digits. The engine's condition reader parsed them as quantities, so it marked those records unreadable. Example: 163 records for CHEMBL3979.
   - **Fix:** every bioactivity condition is compared as text (`as_text: true`). The same generic option was added for the pKa pack in step 8.
   - The independent check now also reads every condition as text, as the pack's written rules say.
   - Test added: `test_digit_led_condition_text_is_a_label_not_a_quantity`.
   - After this fix: **4 mismatches.**
2. **M3: choosing the "largest valid class" when its unit is a mass concentration (study script).**
   - `run_study.py` picked the largest valid class among all units, then skipped the molecule when that class was in µg/mL.
   - The preregistration says "only molar units". Its natural reading is to choose among molar classes, and the independent check did that.
   - **Fix:** `run_study.py` now chooses among molar classes. Examples: CHEMBL5564149 (PIK3CA) and CHEMBL44 (EGFR).
   - After this fix: **0 mismatches.**
3. **Damaged API pages (data).** Checking the first run's EGFR numbers, 5,840 records (20%) were excluded with "key: target_chembl_id not stated". Inspection showed:
   - **80 whole API pages** (49,989 records over 24 targets) came back with the assay and target fields blank: no assay id, assay type, BAO format, variant or target.
   - Every ChEMBL activity has an assay and a target. One such record's assay, fetched separately, is assigned to CHEMBL203 with confidence 9. So this is an API fault under load, not ChEMBL data.
   - These records were excluded from groups. Their blank conditions would otherwise have counted as "the same".
   - **Fix:** `fetch.py` now refuses such a page and fetches it again; `join.py` refuses to build an input with any such record.
   - **The first run's numbers are void and are not reported.**

The first-run headline numbers, kept here for the record only:
- EGFR M1 refused share of paired pairs: 89.4%;
- panel: 72.9%.

They were computed on the damaged data and must not be quoted.

## Second full run (after the repair)

(Filled in below when it finishes.)
