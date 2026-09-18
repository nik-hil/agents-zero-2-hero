"""verify.py — run tests and report results (lesson v0.13).

The final piece of the loop. So far the agent could write and edit code; now it
can *check its own work*. `run_tests` runs the test suite in a directory and
returns a structured result — pass/fail plus the output — that the model can read
and act on. The agent then iterates:

    run_tests -> read failures -> edit -> run_tests -> ... until green.

That feedback loop is what turns "generate code and hope" into "generate,
verify, fix". Nothing here is agent-specific — it just shells out to the test
runner and hands the result back as data.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def run_tests(workspace, command: list[str] | None = None, timeout: int = 60) -> dict:
    """Run the test suite in `workspace`. Returns {passed, returncode, output}."""
    workspace = Path(workspace)
    # Default: discover unittest files (test_*.py) in the workspace — stdlib only.
    cmd = command or [sys.executable, "-m", "unittest", "discover", "-s", ".", "-p", "test_*.py"]

    # Avoid the stale-bytecode trap: after the agent edits a .py file, a cached
    # __pycache__/*.pyc with the same size+mtime-second can be reused, hiding the
    # fix. Clear caches and tell Python not to write new ones.
    for pc in workspace.rglob("__pycache__"):
        shutil.rmtree(pc, ignore_errors=True)
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}

    try:
        r = subprocess.run(
            cmd, cwd=str(workspace), env=env,
            capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"passed": False, "error": f"tests timed out after {timeout}s"}
    except Exception as e:  # noqa: BLE001
        return {"passed": False, "error": str(e)}

    # unittest writes its summary to stderr; keep the tail so results are visible
    # without flooding the context.
    output = (r.stdout + r.stderr).strip()
    return {
        "passed": r.returncode == 0,
        "returncode": r.returncode,
        "output": output[-2000:] if output else "(no output)",
    }
