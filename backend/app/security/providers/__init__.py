from app.security.providers.oidc import OIDCProvider, OIDCUserInfo
from app.security.providers.google import GoogleIdentityProvider
from app.security.providers.microsoft import MicrosoftIdentityProvider
from app.security.exceptions import CredentialsException


def get_identity_provider(provider: str) -> OIDCProvider:
    normalized = provider.lower().strip()
    if normalized == "google":
        return GoogleIdentityProvider()
    elif normalized in ("microsoft", "azure", "entra"):
        return MicrosoftIdentityProvider()
    else:
        raise CredentialsException(detail=f"Unsupported identity provider: {provider}")


__all__ = [
    "OIDCProvider",
    "OIDCUserInfo",
    "GoogleIdentityProvider",
    "MicrosoftIdentityProvider",
    "get_identity_provider",
]
