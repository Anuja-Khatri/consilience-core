# Live run, 20 Nov 2026

A headless Claude Code session (version 2.1.329 (Claude Code)) with this plugin loaded through `--plugin-dir`.

The working folder held:
- OpenEvolve's `third_autocorr_ineq` evaluator (vendored @ ac5f8f5);
- its contract, glue and reference, copied from `benchmarks/evaluator-stress/pilot/oe_c3_post/`.

The agent was asked only to add a comment line to `evaluator.py`:

```bash
claude -p "In evaluator.py, add the single comment line '# reviewed' as the first line of the file using your Edit tool (do nothing else). Afterwards, quote word for word any text that a hook added to your context." \
  --plugin-dir integrations/agent-plugin/consilience-stress --allowedTools Edit Read
```

The agent's reply, verbatim. The long local paths are shortened to `<workdir>`:

`# reviewed` is now the first line of `evaluator.py`; nothing else was changed.

A PostToolUse hook on the Edit added this text to my context, quoted word for word:

```
Consilience stress check (small budget) after this edit:
consilience stress: openevolve/third_autocorr_ineq (post-fix)
BLOCK: 1 finding(s) with a counterexample you can re-run.
margin m = 5e-05 (from record_resolution); reference score 0.759358; record 1.0000
  BLOCK C2 trusts_self_report: score_gain=0.000396337, slack_claim_units=0.001
  C3 naive search: 4 restarts, 0% ended invalid (best invalid None, best valid 0.766471)
  limits: naive search; not a security sandbox; findings concern the hashed scoring code only
check: consilience verify <workdir>/consilience_receipts/stress/20261120-185828/receipt.json
Receipt and counterexamples: <workdir>/consilience_receipts/stress/20261120-185828 (re-check with: consilience verify <workdir>/consilience_receipts/stress/20261120-185828/receipt.json)
```

The hook reports one BLOCK finding (`C2 trusts_self_report`) against the scoring code. I did not act on it or run the suggested `consilience verify` command, since you asked for the edit only.

## What this shows

- The hook found the contract next to the edited file and ran `consilience stress --budget small`.
- The verdict reached the agent's context without being asked for: a BLOCK, because the scorer credits a candidate's self-reported C3 value within a 0.001 slack (`C2 trusts_self_report`).
- The receipt was written and can be re-checked with `consilience verify`.
- The agent did not act on the finding, because it was told to do only the edit. The hook informs; it does not block.
