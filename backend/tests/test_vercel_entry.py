import os
import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
# Load api/index.py the way Vercel does: from the repository root, where backend/ is not
# on the import path, and print the routes the loaded app serves.
LOAD_ENTRY = """
import importlib.util
spec = importlib.util.spec_from_file_location("vercel_entry", "api/index.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
print(sorted({route.path for route in module.app.routes}))
"""


def test_vercel_entry_file_serves_the_api_from_the_repository_root() -> None:
    """Vercel runs api/index.py with the repository root as the working directory."""
    # Without pytest-cov's variables the child is not measured; from the root it would miss
    # backend's branch-coverage setting, and its data could not be combined with ours.
    env = {
        name: value
        for name, value in os.environ.items()
        if not name.startswith(("COV_CORE_", "COVERAGE_"))
    }
    result = subprocess.run(
        [sys.executable, "-c", LOAD_ENTRY],
        cwd=REPOSITORY_ROOT,
        env={**env, "PYTHONPATH": ""},
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "'/api/vehicles/search'" in result.stdout
    assert "'/health'" in result.stdout
