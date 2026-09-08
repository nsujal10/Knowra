from fastapi import APIRouter, Depends
from app.security.dependencies import require_permission
from app.schemas.auth import CurrentUserContext

router = APIRouter()

@router.get("/admin-test", dependencies=[Depends(require_permission("users:read"))])
def admin_test():
    return {"message": "Admin access granted"}

@router.get("/manager-test", dependencies=[Depends(require_permission("actions:update"))])
def manager_test():
    return {"message": "Manager access granted"}

@router.get("/employee-test", dependencies=[Depends(require_permission("meetings:create"))])
def employee_test():
    return {"message": "Employee access granted"}
