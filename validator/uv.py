import os
import shutil
import subprocess
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


def sync_project(project_root: Path, extra: str, env_vars: Optional[dict] = None):
    """Sync the uv-managed project venv with base deps + a specific extra.

    Use when uv owns the venv (no pre-existing activated venv). Enforces
    lockfile consistency: installs/upgrades/downgrades to match resolution.
    """
    logger.info(f"Syncing uv project environment with extra '{extra}' at {project_root}")
    run_command(
        ["uv", "sync", "--extra", extra],
        cwd=str(project_root),
        env=env_vars,
    )


def install_into_existing_venv(
    project_root: Path,
    venv_path: str,
    extra: str,
    env_vars: Optional[dict] = None,
):
    """Install only missing deps into an existing user-managed venv.

    Uses `uv pip install` (not `uv sync`) so we don't downgrade or remove
    packages the user already has. Existing satisfying versions are kept;
    only missing requirements (and their transitive deps) get installed.
    """
    logger.info(
        f"Installing extras '{extra}' into existing venv {venv_path} (additive, no removals)"
    )
    run_command(
        [
            "uv",
            "pip",
            "install",
            "--python",
            venv_path,
            "-e",
            f".[{extra}]",
        ],
        cwd=str(project_root),
        env=env_vars,
    )


def run_in_env(
    project_root: Path,
    command: List[str],
    venv_path: Optional[str] = None,
    env_vars: Optional[dict] = None,
):
    """Run a command inside the target venv.

    If `venv_path` is given (existing user venv), invoke its python directly
    to avoid uv re-syncing. Otherwise use `uv run` against the project venv.
    """
    if venv_path:
        python_bin = str(Path(venv_path) / "bin" / "python")
        logger.info(f"Running command {command} via {python_bin}")
        # Replace leading "python" if present so callers can pass either form.
        if command and command[0] == "python":
            cmd = [python_bin, *command[1:]]
        else:
            cmd = [python_bin, *command]
        run_command(cmd, cwd=str(project_root), env=env_vars)
        return

    logger.info(f"Running command {command} via uv at {project_root}")
    run_command(["uv", "run", *command], cwd=str(project_root), env=env_vars)


def ensure_env_and_run(
    project_root: Path,
    extra: str,
    command: List[str],
    env_vars: Optional[dict] = None,
):
    """Ensure deps for `extra` are present, then run the command.

    Two modes:
    - Reuse mode: VIRTUAL_ENV / UV_PROJECT_ENVIRONMENT points at an existing
      venv. Use `uv pip install` to add only what's missing — never downgrade
      or remove already-installed packages — and run the command with that
      venv's interpreter directly.
    - Project mode: no pre-existing venv. Use `uv sync` to manage `.venv/`
      strictly per pyproject.toml + uv.lock, then run via `uv run`.
    """
    ensure_uv_installed()

    project_env = resolve_project_environment()
    base_env = dict(env_vars) if env_vars else {}

    if project_env:
        install_into_existing_venv(
            project_root,
            project_env,
            extra,
            env_vars=base_env or None,
        )
        run_in_env(
            project_root,
            command,
            venv_path=project_env,
            env_vars=base_env or None,
        )
    else:
        sync_project(project_root, extra, env_vars=base_env or None)
        run_in_env(project_root, command, env_vars=base_env or None)
