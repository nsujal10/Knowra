import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from app.core.database import SessionLocal, Base, engine
from app.models.role import Role
from app.models.permission import Permission
from app.models.role_permission import RolePermission

Base.metadata.create_all(bind=engine)

def seed():
    db = SessionLocal()
    
    perms = [
        "users:read", "users:write", "meetings:create", "meetings:read",
        "actions:update", "audit:read", "billing:manage"
    ]
    
    for p in perms:
        if not db.query(Permission).filter_by(code=p).first():
            db.add(Permission(code=p, description=p))
    db.commit()
    
    roles = {
        "ADMIN": perms,
        "MANAGER": ["users:read", "meetings:create", "meetings:read", "actions:update"],
        "EMPLOYEE": ["meetings:create", "meetings:read", "actions:update"]
    }
    
    for r_code, r_perms in roles.items():
        role = db.query(Role).filter_by(code=r_code).first()
        if not role:
            role = Role(code=r_code, name=r_code.title())
            db.add(role)
            db.commit()
            
        for p_code in r_perms:
            perm = db.query(Permission).filter_by(code=p_code).first()
            if not db.query(RolePermission).filter_by(role_id=role.id, permission_id=perm.id).first():
                db.add(RolePermission(role_id=role.id, permission_id=perm.id))
    db.commit()
    print("Security seed completed.")

if __name__ == "__main__":
    seed()
