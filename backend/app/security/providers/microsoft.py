from urllib.parse import urlencode
from typing import Dict, Any
from app.core.config import settings
from app.security.providers.oidc import OIDCProvider, OIDCUserInfo
from app.security.exceptions import CredentialsException


class MicrosoftIdentityProvider(OIDCProvider):
    provider_name: str = "microsoft"
    default_scopes: list[str] = ["openid", "profile", "email", "offline_access"]

    def __init__(self):
        self.client_id = settings.MICROSOFT_CLIENT_ID
        self.client_secret = settings.MICROSOFT_CLIENT_SECRET
        self.tenant_id = settings.MICROSOFT_TENANT_ID or "common"

        self.authorize_endpoint = (
            f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/authorize"
        )
        self.token_endpoint = (
            f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        )
        self.jwks_uri = (
            f"https://login.microsoftonline.com/{self.tenant_id}/discovery/v2.0/keys"
        )
        self.userinfo_endpoint = "https://graph.microsoft.com/oidc/userinfo"
        super().__init__()

    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "response_mode": "query",
            "scope": " ".join(self.default_scopes),
            "state": state,
            "prompt": "select_account",
        }
        return f"{self.authorize_endpoint}?{urlencode(params)}"

    def parse_user_info(self, token_data: Dict[str, Any]) -> OIDCUserInfo:
        claims: Dict[str, Any] = {}

        # 1. Parse and verify ID token claims
        id_token = token_data.get("id_token")
        if id_token:
            try:
                claims = self.verify_and_parse_id_token(id_token)
            except Exception:
                claims = {}

        # 2. Fallback to Microsoft Graph OIDC userinfo endpoint
        if not (claims.get("email") or claims.get("preferred_username")) and token_data.get("access_token"):
            claims = self.fetch_userinfo_endpoint(token_data["access_token"])

        # Microsoft OIDC subject can be 'oid' (object ID) or 'sub'
        sub = str(claims.get("oid") or claims.get("sub") or "")
        # Email can be in 'email', 'preferred_username', or 'upn'
        email = claims.get("email") or claims.get("preferred_username") or claims.get("upn")

        if not sub or not email:
            raise CredentialsException(
                detail="Microsoft Entra ID response missing required user ID or email claims"
            )

        return OIDCUserInfo(
            sub=sub,
            email=str(email).lower().strip(),
            name=claims.get("name"),
            email_verified=True,
            picture=claims.get("picture"),
            raw_claims=claims,
        )
