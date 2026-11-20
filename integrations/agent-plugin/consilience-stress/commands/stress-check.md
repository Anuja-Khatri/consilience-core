---
description: Stress-test a scoring function from its contract (consilience stress), small budget
argument-hint: <path to contract.yaml>
---

Run the Consilience stress check on the contract at `$ARGUMENTS`:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/after_edit.py" --contract "$ARGUMENTS"
```

Report the verdict (PASS / BLOCK / ABSTAIN) and every BLOCK finding: the check, the kind, the rule broken, and where the counterexample is stored.
- **PASS** means "no counterexample found within the budget". It is not proof.
- **Before trusting a PASS, read the contract,** because a missing validity rule is never tested.
- For a deeper run: `consilience stress <contract> --budget standard` (or `large`).
