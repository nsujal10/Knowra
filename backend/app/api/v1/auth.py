from urllib.parse import quote
from typing import Optional
from fastapi import APIRouter, Depends, status, Request, Query, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, RefreshRequest, CurrentUserContext
from app.services.auth_service import AuthService
from app.security.dependencies import get_current_user
from app.security.providers import get_identity_provider

router = APIRouter()

@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    auth_svc = AuthService(db)
    user = auth_svc.register(req.email, req.password, req.full_name, req.organization_name)
    return {"message": "User registered", "id": str(user.id)}

@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    auth_svc = AuthService(db)
    access, refresh = auth_svc.login(req.email, req.password)
    return TokenResponse(access_token=access, refresh_token=refresh)

@router.post("/login/token", response_model=TokenResponse)
def login_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    auth_svc = AuthService(db)

    access, refresh = auth_svc.login(
        form_data.username,
        form_data.password
    )

    return TokenResponse(
        access_token=access,
        refresh_token=refresh
    )

@router.post("/refresh", response_model=TokenResponse)
def refresh(req: RefreshRequest, db: Session = Depends(get_db)):
    auth_svc = AuthService(db)
    access, refresh = auth_svc.refresh_token(req.refresh_token)
    return TokenResponse(access_token=access, refresh_token=refresh)

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(current_user: CurrentUserContext = Depends(get_current_user), db: Session = Depends(get_db)):
    AuthService(db).logout(current_user.user_id, all_sessions=False) # Simplified for MVP to target all active

@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
def logout_all(current_user: CurrentUserContext = Depends(get_current_user), db: Session = Depends(get_db)):
    AuthService(db).logout(current_user.user_id, all_sessions=True)

@router.get("/me", response_model=CurrentUserContext)
def read_users_me(current_user: CurrentUserContext = Depends(get_current_user)):
    return current_user


# ─── Enterprise Single Sign-On (OIDC / OAuth 2.0) ─────────────────────────────

@router.get("/{provider}/login", summary="Initiate OIDC Single Sign-On Flow")
def sso_login(
    provider: str,
    redirect: Optional[str] = Query("/", description="Frontend path to redirect to after successful auth"),
    db: Session = Depends(get_db),
):
    """
    Generates a cryptographically signed CSRF state parameter and redirects
    the client to the Identity Provider's OIDC authorization endpoint.
    """
    idp = get_identity_provider(provider)
    auth_svc = AuthService(db)

    state = auth_svc.generate_oauth_state(provider=provider, redirect_target=redirect or "/")
    base_url = settings.OAUTH_REDIRECT_BASE_URL.rstrip('/')
    if not base_url.endswith("/api/v1/auth"):
        base_url = f"{base_url}/api/v1/auth"
    redirect_uri = f"{base_url}/{provider.lower()}/callback"
    authorization_url = idp.get_authorization_url(state=state, redirect_uri=redirect_uri)

    return RedirectResponse(url=authorization_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.get("/{provider}/callback", summary="Handle OIDC Identity Provider Callback")
def sso_callback(
    provider: str,
    request: Request,
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Exchanges the authorization code with the provider, verifies claims via JWKS,
    executes multi-tenant identity reconciliation and auto-provisioning, and
    redirects the user to the frontend callback handler with Knowra JWTs.
    """
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{provider.capitalize()} error: {error_description or error}",
        )

    if not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing OAuth state parameter",
        )

    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing OAuth authorization code",
        )

    idp = get_identity_provider(provider)
    auth_svc = AuthService(db)

    # 1. Validate CSRF state parameter (signature, expiration, provider match)
    state_payload = auth_svc.verify_oauth_state(state=state, expected_provider=provider)
    redirect_target = state_payload.get("redirect", "/")

    # 2. Exchange authorization code for tokens
    base_url = settings.OAUTH_REDIRECT_BASE_URL.rstrip('/')
    if not base_url.endswith("/api/v1/auth"):
        base_url = f"{base_url}/api/v1/auth"
    redirect_uri = f"{base_url}/{provider.lower()}/callback"
    token_data = idp.exchange_code(code=code, redirect_uri=redirect_uri)

    # 3. Parse and validate ID token / UserInfo claims
    user_info = idp.parse_user_info(token_data)

    # 4. Reconcile identity, account link, and multi-tenant auto-provision
    access_token, refresh_token, user, org_id = auth_svc.reconcile_sso_user(
        provider=provider, user_info=user_info
    )

    # 5. Programmatic JSON response for API clients / automated tests
    accept_header = request.headers.get("accept", "")
    if "application/json" in accept_header and "text/html" not in accept_header:
        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    # 6. Redirect to frontend callback handler
    callback_url = (
        f"{settings.FRONTEND_URL.rstrip('/')}/auth/callback"
        f"?access_token={access_token}&refresh_token={refresh_token}&redirect={quote(redirect_target)}"
    )
    return RedirectResponse(url=callback_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

