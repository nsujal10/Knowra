from urllib.parse import urlencode
from typing import Dict, Any
from app.core.config import settings
from app.security.providers.oidc import OIDCProvider, OIDCUserInfo
from app.security.exceptions import CredentialsException


class GoogleIdentityProvider(OIDCProvider):
    provider_name: str = "google"
    authorize_endpoint: str = "https://accounts.google.com/o/oauth2/v2/auth"
    token_endpoint: str = "https://oauth2.googleapis.com/token"
    jwks_uri: str = "https://www.googleapis.com/oauth2/v3/certs"
    userinfo_endpoint: str = "https://openidconnect.googleapis.com/v1/userinfo"
    default_scopes: list[str] = ["openid", "email", "profile"]

    def __init__(self):
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        super().__init__()

    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.default_scopes),
            "state": state,
            "access_type": "offline",
            "prompt": "select_account",
            "include_granted_scopes": "true",
        }
        return f"{self.authorize_endpoint}?{urlencode(params)}"

    def parse_user_info(self, token_data: Dict[str, Any]) -> OIDCUserInfo:
        claims: Dict[str, Any] = {}

        # 1. Prefer parsing and verifying ID token claims
        id_token = token_data.get("id_token")
        if id_token:
            try:
                claims = self.verify_and_parse_id_token(id_token)
            except Exception:
                # If signature check fails in dev/test, fallback to userinfo endpoint
                claims = {}

        # 2. If ID token was missing or didn't yield claims, fetch userinfo directly
        if not claims.get("email") and token_data.get("access_token"):
            claims = self.fetch_userinfo_endpoint(token_data["access_token"])

        sub = str(claims.get("sub") or "")
        email = claims.get("email")
        if not sub or not email:
            raise CredentialsException(
                detail="Google OAuth response missing required subject or email claims"
            )

        return OIDCUserInfo(
            sub=sub,
            email=email.lower().strip(),
            name=claims.get("name") or claims.get("given_name"),
            email_verified=bool(claims.get("email_verified", True)),
            picture=claims.get("picture"),
            raw_claims=claims,
        )
