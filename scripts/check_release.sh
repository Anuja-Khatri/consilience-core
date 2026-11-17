#!/usr/bin/env bash
# Release check for consilience (see docs/RELEASE.md). Uploads nothing.
#
# 1. builds the sdist and wheel into dist/ and runs `twine check --strict`;
# 2. lists the wheel and checks it holds the package, the pack and the examples only;
# 3. installs the wheel into a brand-new virtual environment (nothing else in it) and
#    checks the optional nanopub dependencies are NOT installed;
# 4. in an empty folder, runs every ```console block of README.md command by command and
#    compares the output line by line with the README (a line "..." skips lines; a line
#    ending in "..." matches by prefix), then runs the README's Python example and
#    compares each print with its comment.
#
# Usage: bash scripts/check_release.sh      (needs Python 3.10+ as `python3`,
#                                            or set PYTHON=/path/to/python3.x)
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
unset PYTHONPATH || true   # test the built package only, never the source tree
PY="${PYTHON:-python3}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

"$PY" -c 'import sys; assert sys.version_info >= (3, 10), f"need Python 3.10+, found {sys.version.split()[0]}"'
echo "python: $("$PY" --version)"

echo "== 1. build and twine check"
"$PY" -m venv "$WORK/build-venv"
"$WORK/build-venv/bin/python" -m pip install -q --disable-pip-version-check --upgrade pip build twine
rm -rf "$REPO/dist"
"$WORK/build-venv/bin/python" -m build --outdir "$REPO/dist" "$REPO" >"$WORK/build.log" 2>&1 \
  || { cat "$WORK/build.log"; exit 1; }
ls -l "$REPO/dist"
"$WORK/build-venv/bin/twine" check --strict "$REPO"/dist/*

echo "== 2. wheel contents"
"$WORK/build-venv/bin/python" - "$REPO"/dist/consilience-*-py3-none-any.whl <<'PY'
import sys, zipfile
names = sorted(zipfile.ZipFile(sys.argv[1]).namelist())
for n in names:
    print("  " + n)
need = ["consilience/data/packs/electrochemistry.yaml", "consilience/data/examples/readings.csv",
        "consilience/data/examples/readings_rules.yaml", "consilience/data/examples/measurement_a.json",
        "consilience/cli.py", "consilience/units.py"]
missing = [n for n in need if n not in names]
assert not missing, f"missing from the wheel: {missing}"
bad = [n for n in names if not (n.startswith("consilience/") or n.startswith("consilience-"))]
assert not bad, f"unexpected files in the wheel: {bad}"
PY

echo "== 3. install the wheel into a brand-new venv"
"$PY" -m venv "$WORK/test-venv"
"$WORK/test-venv/bin/python" -m pip install -q --disable-pip-version-check "$REPO"/dist/consilience-*-py3-none-any.whl
BIN="$WORK/test-venv/bin"
"$BIN/python" -I - <<'PY'
import importlib.util
for mod in ("nanopub", "rdflib"):
    assert importlib.util.find_spec(mod) is None, f"{mod} must not be installed by default"
PY
"$BIN/consilience" version

echo "== 4. README quickstart in an empty folder"
mkdir "$WORK/run"
"$BIN/python" -I - "$REPO/README.md" "$WORK/run" "$BIN" <<'PY'
import contextlib, io, os, re, subprocess, sys

readme, cwd, binp = sys.argv[1], sys.argv[2], sys.argv[3]
text = open(readme, encoding="utf-8").read()
env = dict(os.environ, PATH=binp + os.pathsep + os.environ["PATH"])
env.pop("PYTHONPATH", None)


def matches(got, want):
    """Line match with '...' (any lines) and 'prefix...' (prefix) wildcards."""
    if not want:
        return not got
    w = want[0]
    if w == "...":
        return any(matches(got[i:], want[1:]) for i in range(len(got) + 1))
    if not got:
        return False
    ok = got[0].startswith(w[:-3]) if w.endswith("...") else got[0] == w
    return ok and matches(got[1:], want[1:])


last = 0
for block in re.findall(r"```console\n(.*?)```", text, re.S):
    steps, cur = [], None
    for line in block.splitlines():
        if line.startswith("$ "):
            cur = [line[2:], []]
            steps.append(cur)
        else:
            cur[1].append(line)
    for cmd, want in steps:
        if cmd.startswith("cd "):
            cwd = os.path.join(cwd, cmd[3:])
            got = []
        elif cmd == "echo $?":
            got = [str(last)]
        else:
            r = subprocess.run(["bash", "-c", cmd], cwd=cwd, env=env,
                               capture_output=True, text=True)
            got, last = (r.stdout + r.stderr).splitlines(), r.returncode
        if not matches(got, want):
            print("FAIL: $ " + cmd)
            print("--- README says:\n" + "\n".join(want))
            print("--- got:\n" + "\n".join(got))
            sys.exit(1)
        print(f"ok: $ {cmd}" + (f"  -> {got[0]}" if cmd == "echo $?" else ""))

# the Python example, run in the folder the console blocks ended in
block = re.search(r"```python\n(.*?)```", text, re.S).group(1)
os.chdir(cwd)
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    exec(compile(block, "README python example", "exec"), {})
got = buf.getvalue().splitlines()
want = [re.search(r"#\s*(.*)$", ln).group(1) for ln in block.splitlines()
        if ln.startswith("print(")]
assert len(got) == len(want), (got, want)
for g, w in zip(got, want):
    assert g == w, f"README Python example printed {g!r}, README says {w!r}"
    print(f"ok: python prints {g}")
PY

echo "== release check passed: dist/ is ready (nothing was uploaded)"
