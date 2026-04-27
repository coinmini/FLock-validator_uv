import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

from loguru import logger


def run_command(cmd, **kwargs):
    """Run a command with unbuffered output, streaming to stdout."""
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        **kwargs,
    )
    for line in process.stdout:
        print(line, end="")
    process.wait()
    if process.returncode != 0:
        raise subprocess.CalledProcessError(process.returncode, cmd)


def ensure_uv_installed() -> str:
    """Verify uv is on PATH; return its absolute path."""
    uv_path = shutil.which("uv")
    if uv_path is None:
        raise RuntimeError(
            "uv is not installed or not on PATH. "
            "Install it with `curl -LsSf https://astral.sh/uv/install.sh | sh` "
            "or `pip install uv`."
        )
    return uv_path


def sync_extra(project_root: Path, extra: str):
    """Sync the project venv with base deps + a specific optional-dependency extra."""
    logger.info(f"Syncing uv environment with extra '{extra}' at {project_root}")
    run_command(
        ["uv", "sync", "--extra", extra],
        cwd=str(project_root),
    )


def run_in_env(
    project_root: Path,
    command: List[str],
    env_vars: Optional[dict] = None,
):
    """Run a command inside the project's uv-managed venv."""
    logger.info(f"Running command {command} via uv at {project_root}")
    cmd = ["uv", "run"] + command
    run_command(cmd, cwd=str(project_root), env=env_vars)


def ensure_env_and_run(
    project_root: Path,
    extra: str,
    command: List[str],
    env_vars: Optional[dict] = None,
):
    """Ensure the venv has the requested extra installed, then run the command."""
    ensure_uv_installed()
    sync_extra(project_root, extra)
    run_in_env(project_root, command, env_vars)
