"""Query aggregation module."""

from unbubble_sources.aggregator.base import QueryAggregator
from unbubble_sources.aggregator.noop import NoOpAggregator

# PCAAggregator and its embedder require the 'ml' extras.
# Importing them here would cause an ImportError for users without ML deps,
# so they are NOT re-exported from this package-level __init__.
# Import them directly if needed:
#   from unbubble_sources.aggregator.pca import PCAAggregator
#   from unbubble_sources.aggregator.embeddings import SentenceTransformerEmbedder

__all__ = [
    "NoOpAggregator",
    "QueryAggregator",
]
