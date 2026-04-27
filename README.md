# LLM Validator System

## Overview

The Flock LLM Validator script is a modular system for doing validation for Flock AI Arena validation assignments. It uses a single [uv](https://docs.astral.sh/uv/)-managed virtual environment with per-module optional-dependency groups, fetches validation assignments from the Flock API, executes the validation, and submits results back to the API. The system is extensible, allowing new validation modules or task types to be added easily.

The project is split into two layers:
1. The outer layer that runs outside the venv and is responsible for syncing module dependencies and launching the inner runner via `uv run`.
2. The inner layer that runs inside the venv and is responsible for all validation and assignment orchestration logic.

## Setup

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/) (e.g. `curl -LsSf https://astral.sh/uv/install.sh | sh`).
2. No manual dependency install is required — `run.py` will run `uv sync --extra <module>` automatically on first launch. To pre-install everything yourself:

```bash
uv sync --extra all
```

## Usage

### Running Validation Jobs

Use the CLI to start the validation process. The CLI settings are defined in `validator/entrypoint.py`.

```bash
python run.py \
  <module> \
  --task_ids <task_id1,task_id2,...> \
  --flock-api-key <your_flock_api_key> \
  --hf-token <your_hf_token>
```

#### Arguments and Options
- `<module>`: Name of the validation module to use (e.g., `lora`).
- `--task_ids`: Comma-separated list of task IDs to validate.
- `--flock-api-key`: Flock API key (can also be set via the `FLOCK_API_KEY` environment variable).
- `--hf-token`: HuggingFace token (can also be set via the `HF_TOKEN` environment variable).
- `--time-sleep`: (Optional) Time to sleep between retries in seconds (default: 180).
- `--assignment-lookup-interval`: (Optional) Assignment lookup interval in seconds (default: 180).
- `--debug`: (Optional) Enable debug mode.

#### Example

```bash
python run.py lora --task_ids 123,456 --flock-api-key $FLOCK_API_KEY --hf-token $HF_TOKEN
```

### Environment Variables
You can set the following environment variables instead of passing them as CLI options:
- `FLOCK_API_KEY`
- `HF_TOKEN`
- `TIME_SLEEP`
- `ASSIGNMENT_LOOKUP_INTERVAL`

### Adding New Validation Modules
1. Create a new subdirectory or file in `validator/modules/`.
2. Implement a class that inherits from `BaseValidationModule` and define the required schemas.
3. Expose your module class as `MODULE` in the module's `__init__.py`.
4. The system will dynamically load your module when specified via the CLI.

### Configuration
- Module and task-specific configuration files should be placed in the `configs/` directory.
- Per-task-type config: `configs/<module>.json`
- Per-task-id config (which overrides the per-task-type config): `configs/tasks/<task_id>.json`

## Error Handling
- Recoverable errors (subclass `RecoverableException`) will not mark the assignment as failed and will log the error.
- Other exceptions will mark the assignment as failed.
