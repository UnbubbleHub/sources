"""YAML configuration loading utilities."""

from pathlib import Path

import yaml

from unbubble_sources.config.models import UnbubbleConfig


def load_config(path: Path | str) -> UnbubbleConfig:
    """Load configuration from YAML file.

    Args:
        path: Path to YAML config file.

    Returns:
        Validated UnbubbleConfig.

    Raises:
        FileNotFoundError: If config file doesn't exist.
        pydantic.ValidationError: If config is invalid.
    """
    path = Path(path)
    with path.open() as f:
        raw = yaml.safe_load(f)

    return UnbubbleConfig.model_validate(raw)


def get_default_config_path() -> Path:
    """Get path to default config file."""
    return Path(__file__).parent.parent.parent / "configs" / "default.yaml"
