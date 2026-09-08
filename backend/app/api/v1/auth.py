from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, RefreshRequest, CurrentUserContext
from app.services.auth_service import AuthService
from app.security.dependencies import get_current_user

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
