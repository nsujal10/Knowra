"""
Phase 21 – Authorization Domain Package
"""

from app.auth.scope import AuthorizedRetrievalScope
from app.auth.service import AuthorizationService

__all__ = [
    "AuthorizedRetrievalScope",
    "AuthorizationService",
]
