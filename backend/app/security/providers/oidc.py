from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
import jwt
from jwt import PyJWKClient
import httpx
from app.security.exceptions import CredentialsException


class OIDCUserInfo(BaseModel):
    sub: str = Field(..., description="Provider unique subject/user ID")
    email: str = Field(..., description="Verified email address")
    name: Optional[str] = Field(None, description="User full display name")
    email_verified: bool = Field(True, description="Whether the email is verified by the provider")
    picture: Optional[str] = Field(None, description="Profile avatar URL")
    raw_claims: Dict[str, Any] = Field(default_factory=dict, description="Raw provider claims")


class OIDCProvider(ABC):
    provider_name: str
    client_id: str
    client_secret: str
    authorize_endpoint: str
    token_endpoint: str
    jwks_uri: Optional[str] = None
    userinfo_endpoint: Optional[str] = None
    default_scopes: list[str] = []

    def __init__(self):
        self._jwks_client: Optional[PyJWKClient] = None
        if self.jwks_uri:
            self._jwks_client = PyJWKClient(self.jwks_uri)

    @abstractmethod
    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        """Constructs the provider authorization URL with scopes, state, and redirect URI."""
        pass

    def exchange_code(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchanges authorization code for tokens (id_token, access_token) via HTTP POST."""
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.post(self.token_endpoint, data=payload, headers=headers)
                if response.status_code != 200:
                    raise CredentialsException(
                        detail=f"{self.provider_name} token exchange failed: {response.text}"
                    )
                return response.json()
        except httpx.RequestError as exc:
            raise CredentialsException(
                detail=f"Network error during {self.provider_name} token exchange: {str(exc)}"
            )

    def verify_and_parse_id_token(self, id_token: str) -> Dict[str, Any]:
        """Validates ID token signature against provider JWKS and returns decoded claims."""
        if not self._jwks_client:
            # Fallback: decode unverified claims if JWKS is not configured
            return jwt.decode(id_token, options={"verify_signature": False})

        try:
            signing_key = self._jwks_client.get_signing_key_from_jwt(id_token)
            claims = jwt.decode(
                id_token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.client_id,
                options={"verify_exp": True, "verify_aud": bool(self.client_id)},
            )
            return claims
        except Exception as exc:
            raise CredentialsException(
                detail=f"Invalid {self.provider_name} ID token signature: {str(exc)}"
            )

    def fetch_userinfo_endpoint(self, access_token: str) -> Dict[str, Any]:
        """Fetches profile data directly from provider UserInfo endpoint using access_token."""
        if not self.userinfo_endpoint:
            return {}

        headers = {"Authorization": f"Bearer {access_token}"}
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(self.userinfo_endpoint, headers=headers)
                if response.status_code != 200:
                    raise CredentialsException(
                        detail=f"Failed to fetch {self.provider_name} userinfo: {response.text}"
                    )
                return response.json()
        except httpx.RequestError as exc:
            raise CredentialsException(
                detail=f"Network error fetching {self.provider_name} userinfo: {str(exc)}"
            )

    @abstractmethod
    def parse_user_info(self, token_data: Dict[str, Any]) -> OIDCUserInfo:
        """Extracts and normalizes user profile into standard OIDCUserInfo."""
        pass
