# consilience-pooling: an agent plugin

When an AI agent fetches potency values (IC50, Ki, Kd, EC50) from ChEMBL, this plugin tells it which records may be pooled. For those that may not, it names the reason. For those that may, it says whether they agree. Every check has a receipt anyone can re-run.

**It does not modify any other skill or tool.** It runs after them.

## What it contains

| Part | What it does |
|---|---|
| **Hook** (`hooks/hooks.json`, `hooks/after_fetch.py`) | Runs after Bash and ChEMBL MCP tool calls. If the output, or the file the tool wrote (DeepMind's ChEMBL skill prints `{"output_file": ...}`), holds ChEMBL activity records, it runs `consilience compare-table --map chembl --pack bioactivity` and adds a short summary to the agent's context. Otherwise it stays silent. It never blocks the tool, never uses the network, stops after 20 s, and always exits 0 |
| **Skill** (`skills/check-pooling/SKILL.md`) | When and how to check, and how to read the result |
| **Command** (`commands/check-pooling.md`) | `/check-pooling <file>` for a full, combined fetch |

The hook checks **one fetch at a time**. When the fetch is one page of a larger result, it says so, and points to `/check-pooling` on the combined file.

## Install

1. Install the engine where the agent runs Python:

   ```bash
   pip install "consilience>=0.2"
   ```

2. **Claude Code:** clone this repository and load the folder.

   ```bash
   claude --plugin-dir integrations/agent-plugin/consilience-pooling
   ```

   Or add it through a plugin marketplace that lists it.

3. **Antigravity:** copy the folder to `.agents/plugins/consilience-pooling/` in a workspace, or to `~/.gemini/config/plugins/`. It ships `plugin.json` and a root `hooks.json` in Antigravity's documented format.
   - **Not runtime-tested.** We could not run Antigravity where this was built.
   - Antigravity's PostToolUse hook receives no tool output and returns `{}`. So the hook reads the file named by `--output` in the command and writes the receipt. A PreInvocation hook then shows the summary to the agent once (documented `ephemeralMessage`).

## Tested

| Platform | What was tested |
|---|---|
| **Claude Code** | Recorded PostToolUse inputs, in `tests/test_agent_plugin.py`:<ul><li>DeepMind's status JSON naming an `output_file`;</li><li>inline activity JSON;</li><li>non-matching output (silent, under 1 s);</li><li>malformed output;</li><li>exit code always 0.</li></ul>Plus a live headless run with DeepMind's own ChEMBL script: see `LIVE_RUN.md` |
| **Antigravity** | Files only, not runtime-tested |

## Limits

- **ChEMBL activity records only.** PubChem and BindingDB outputs use other fields and are not supported yet.
- **Assay-level conditions** (organism, cell type, confidence score…) need assay fields joined in. A single activity fetch lacks them, and the summary says so.
- **ATP or substrate concentration** is not checked.
