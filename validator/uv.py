import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from loguru import logger


def run_command(cmd, env: Optional[dict] = None, **kwargs):
    """Run a command with unbuffered output, streaming to stdout."""
    merged_env = {**os.environ, **env} if env else None
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=merged_env,
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


def resolve_project_environment() -> Optional[str]:
    """If the user has an activated venv, reuse it as the uv project environment.

    Returns the venv path to set as UV_PROJECT_ENVIRONMENT, or None to let uv
    fall back to its default `.venv/` in the project root.
    """
    explicit = os.environ.get("UV_PROJECT_ENVIRONMENT")
    if explicit:
        logger.info(f"Reusing UV_PROJECT_ENVIRONMENT from caller: {explicit}")
        return explicit

    active_venv = os.environ.get("VIRTUAL_ENV")
    if active_venv and Path(active_venv).is_dir():
        logger.info(f"Detected activated venv, reusing it for uv: {active_venv}")
        return active_venv

    return None


def sync_extra(project_root: Path, extra: str, env_vars: Optional[dict] = None):
    """Sync the project venv with base deps + a specific optional-dependency extra."""
    logger.info(f"Syncing uv environment with extra '{extra}' at {project_root}")
    run_command(
        ["uv", "sync", "--extra", extra],
        cwd=str(project_root),
        env=env_vars,
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
    """Ensure the venv has the requested extra installed, then run the command.

    If the caller has an activated venv (VIRTUAL_ENV set) or has set
    UV_PROJECT_ENVIRONMENT explicitly, that venv is reused — uv installs the
    requested extra into it instead of creating a fresh `.venv/`.
    """
    ensure_uv_installed()

    project_env = resolve_project_environment()
    overrides = dict(env_vars) if env_vars else {}
    if project_env:
        overrides["UV_PROJECT_ENVIRONMENT"] = project_env

    sync_extra(project_root, extra, env_vars=overrides or None)
    run_in_env(project_root, command, env_vars=overrides or None)
