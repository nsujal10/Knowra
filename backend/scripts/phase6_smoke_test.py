import sys
import os
import requests
import time
import subprocess

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from app.core.database import engine, SessionLocal
from app.models.base import Base
from app.models.refresh_session import RefreshSession

# Reset Database
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

# Seed
import scripts.seed_security
scripts.seed_security.seed()

# Start Server in Background
server = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8000"])
time.sleep(2) # wait for boot

BASE_URL = "http://localhost:8000/api/v1"

def print_step(msg):
    print(f"\n--- {msg} ---")

try:
    print_step("1. Register User A -> Org A -> ADMIN")
    res = requests.post(f"{BASE_URL}/auth/register", json={
        "email": "userA@test.com", "password": "password123",
        "full_name": "User A", "organization_name": "Org A"
    })
    assert res.status_code == 201
    
    print_step("2. Login User A")
    res = requests.post(f"{BASE_URL}/auth/login", json={"email": "userA@test.com", "password": "password123"})
    assert res.status_code == 200
    tokens = res.json()
    token_A = tokens["access_token"]
    refresh_A = tokens["refresh_token"]
    
    print_step("3. Call /auth/me")
    res = requests.get(f"{BASE_URL}/auth/me", headers={"Authorization": f"Bearer {token_A}"})
    assert res.status_code == 200
    me_A = res.json()
    assert me_A["role_code"] == "ADMIN"
    org_A_id = me_A["organization_id"]
    
    print_step("4. Register User C -> Org C")
    res = requests.post(f"{BASE_URL}/auth/register", json={
        "email": "userC@test.com", "password": "password123",
        "full_name": "User C", "organization_name": "Org C"
    })
    assert res.status_code == 201
    
    print_step("5. Create User B (EMPLOYEE) under Org A (Simulation via DB)")
    db = SessionLocal()
    from app.models.user import User
    from app.models.membership import Membership
    from app.models.role import Role
    from app.security.password import hash_password
    
    user_b = User(email="userB@test.com", password_hash=hash_password("password123"), full_name="User B")
    db.add(user_b)
    emp_role = db.query(Role).filter_by(code="EMPLOYEE").first()
    db.commit()
    db.add(Membership(user_id=user_b.id, organization_id=org_A_id, role_id=emp_role.id))
    db.commit()
    
    print_step("6. Login User B")
    res = requests.post(f"{BASE_URL}/auth/login", json={"email": "userB@test.com", "password": "password123"})
    assert res.status_code == 200
    tokens_B = res.json()
    token_B = tokens_B["access_token"]
    refresh_B = tokens_B["refresh_token"]
    
    print_step("7. User B access /employee-test (Allowed)")
    res = requests.get(f"{BASE_URL}/security/employee-test", headers={"Authorization": f"Bearer {token_B}"})
    assert res.status_code == 200
    
    print_step("8. User B access /admin-test (Forbidden)")
    res = requests.get(f"{BASE_URL}/security/admin-test", headers={"Authorization": f"Bearer {token_B}"})
    assert res.status_code == 403
    
    print_step("9. User B Refresh Token Rotation")
    res = requests.post(f"{BASE_URL}/auth/refresh", json={"refresh_token": refresh_B})
    assert res.status_code == 200
    tokens_B_new = res.json()
    refresh_B_new = tokens_B_new["refresh_token"]
    
    print_step("10. Attempt Replay of Old Refresh Token (Breach Detect)")
    res = requests.post(f"{BASE_URL}/auth/refresh", json={"refresh_token": refresh_B})
    assert res.status_code == 401
    
    print_step("11. Check Token Family Revocation")
    # Using new refresh token should now fail because family was revoked in step 10
    res = requests.post(f"{BASE_URL}/auth/refresh", json={"refresh_token": refresh_B_new})
    assert res.status_code == 401
    
    print_step("12. Verify Audit Logs")
    from app.models.audit_log import AuditLog
    logs = db.query(AuditLog).all()
    actions = [log.action for log in logs]
    assert "TOKEN_REUSE_DETECTED" in actions
    
    print("\n[PASS] All Authentication and Authorization flows successfully verified!")

finally:
    server.terminate()
    server.wait()
