"""Parsing utilities for normalizing raw API values."""

from datetime import datetime


def maybe_parse_datetime(value: str) -> datetime | None:
    """Attempt parsing the input string into a datetime object, returns None if it is not a date in the correct format."""
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
