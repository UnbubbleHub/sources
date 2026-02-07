"""URL handling utilities."""

from __future__ import annotations

import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def extract_domain(url: str) -> str:
    """Extract domain name from URL.

    Args:
        url: The URL to extract the domain from.

    Returns:
        The domain name (without 'www.' prefix), or "Unknown" if extraction fails.
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        if not domain:
            logger.warning(f"Could not get domain from url {url}")
            return "Unknown"
        # Remove www. prefix
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return "Unknown"
