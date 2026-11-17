"""Piping output into a reader that stops early must not print a traceback."""
import shutil
import subprocess
import sys

import pytest


@pytest.mark.skipif(shutil.which("bash") is None or shutil.which("head") is None,
                    reason="needs bash and head")
def test_compare_piped_into_head_prints_no_traceback(tmp_path):
    subprocess.run([sys.executable, "-m", "consilience", "examples", str(tmp_path)],
                   check=True, capture_output=True)
    cmd = (f'"{sys.executable}" -m consilience compare '
           f'"{tmp_path}/measurement_a.json" "{tmp_path}/measurement_b.json" '
           f'--pack electrochemistry | head -1 > /dev/null')
    for _ in range(3):  # the failure shows when the reader exits before the final flush
        r = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True)
        assert "Traceback" not in r.stderr, r.stderr
