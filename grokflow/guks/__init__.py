"""
GUKS (GrokFlow Universal Knowledge System) Package

Provides semantic search and cross-project learning capabilities for GrokFlow CLI.

Key Components:
  - embeddings.py: Vector-based semantic search
  - api.py: REST API for IDE integration
  - analytics.py: Pattern detection and insights
  - completions.py: GUKS-powered code completions (future)

Usage:
    from grokflow.guks import EnhancedGUKS, GUKSAnalytics

    # Query GUKS
    guks = EnhancedGUKS()
    results = guks.query(code="user.name", error="TypeError")

    # Analyze patterns
    analytics = GUKSAnalytics(guks.patterns)
    recurring = analytics.detect_recurring_bugs()
    constraints = analytics.suggest_constraint_rules()
"""

from .embeddings import EnhancedGUKS, GUKSEmbeddingEngine
from .analytics import GUKSAnalytics

__version__ = "1.0.0"
__all__ = ['EnhancedGUKS', 'GUKSEmbeddingEngine', 'GUKSAnalytics']
