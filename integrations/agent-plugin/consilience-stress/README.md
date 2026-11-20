# consilience-stress: an agent plugin for checking scoring code before an optimiser runs against it

It works in Claude Code (`--plugin-dir` or a marketplace install) and follows the same file layout for Antigravity. **Antigravity support is not runtime-tested.**

## What it does

- **The hook.** After the agent **writes or edits a scoring file** that has a contract next to it (`contract.yaml` or `*.contract.yaml`), the hook runs:

  `consilience stress <contract> --budget small --out ./consilience_receipts/stress/<time>/`

  It puts the verdict and its findings into the agent's context. Files with no contract are ignored.
- **The skill `stress-check`:** when to use it, how to write a contract, and how to read the result.
- **The command `/stress-check <contract.yaml>`:** run the check on demand.

The hook always exits 0. It never blocks the agent or changes the scorer, and it uses no network. It stops after 280 seconds and says so.

## Install

```bash
pip install 'consilience[stress]'
claude --plugin-dir integrations/agent-plugin/consilience-stress
```

## Where to read more

- `docs/stress.md`: what the check is for, who it is for, the contract reference, every check and finding, and its limits.
- `LIVE_RUN.md`: a recorded headless session.
