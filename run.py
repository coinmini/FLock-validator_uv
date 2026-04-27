# This script acts as an entrypoint and is used to set up, manage and run uv environments.

import sys
from pathlib import Path

from validator import uv


def entrypoint():
    project_root = Path(__file__).resolve().parent

    if len(sys.argv) < 2:
        raise ValueError("Module name is required as the first positional argument")

    module = sys.argv[1]

    module_dir = project_root / "validator" / "modules" / module
    if not module_dir.is_dir():
        raise ValueError(f"Module {module} does not exist")

    uv.ensure_env_and_run(
        project_root=project_root,
        extra=module,
        command=["python", "environment_entrypoint.py", *sys.argv[1:]],
    )


if __name__ == "__main__":
    entrypoint()
