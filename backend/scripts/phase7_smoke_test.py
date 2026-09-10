import sys
import os
import requests
import time
import subprocess
from uuid import UUID

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from app.core.database import  engine, SessionLocal
from app.core.database import engine, SessionLocal
from app.models.base import Base
Base.metadata.create_all(bind=engine)

# Seed basic auth structures
import scripts.seed_security
scripts.seed_security.seed()

server = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8000"])
time.sleep(3)

BASE_URL = "http://localhost:8000/api/v1"

def print_step(msg):
    print(f"\n--- {msg} ---")

try:
    print_step("1. Provision Tenant A & Tenant B")
    resA = requests.post(f"{BASE_URL}/auth/register", json={"email": "a@tenant.com", "password": "Sipl@12345", "full_name": "A", "organization_name": "Org A"})
    resB = requests.post(f"{BASE_URL}/auth/register", json={"email": "b@tenant.com", "password": "Sipl@12345", "full_name": "B", "organization_name": "Org B"})
    
    tokenA = requests.post(f"{BASE_URL}/auth/login", json={"email": "a@tenant.com", "password": "Sipl@12345"}).json()["access_token"]
    tokenB = requests.post(f"{BASE_URL}/auth/login", json={"email": "b@tenant.com", "password": "Sipl@12345"}).json()["access_token"]
    
    print_step("2. Create Meeting under Tenant A")
    res = requests.post(f"{BASE_URL}/meetings", headers={"Authorization": f"Bearer {tokenA}"}, json={"title": "Secret Strategy A"})
    assert res.status_code == 201
    meeting_id = res.json()["id"]
    print(f"Meeting created: {meeting_id}")
    
    print_step("3. Tenant A Reads Own Meeting -> 200 OK")
    res = requests.get(f"{BASE_URL}/meetings/{meeting_id}", headers={"Authorization": f"Bearer {tokenA}"})
    assert res.status_code == 200
    
    print_step("4. Tenant B Attempts to Read Tenant A's Meeting -> 404 Not Found")
    res = requests.get(f"{BASE_URL}/meetings/{meeting_id}", headers={"Authorization": f"Bearer {tokenB}"})
    assert res.status_code == 404
    
    print_step("5. Tenant B Attempts to Update Tenant A's Meeting -> 404 Not Found")
    res = requests.patch(f"{BASE_URL}/meetings/{meeting_id}", headers={"Authorization": f"Bearer {tokenB}"}, json={"title": "Hacked"})
    assert res.status_code == 404
    
    print_step("6. Tenant B Attempts to Delete Tenant A's Meeting -> 404 Not Found")
    res = requests.delete(f"{BASE_URL}/meetings/{meeting_id}", headers={"Authorization": f"Bearer {tokenB}"})
    assert res.status_code == 404
    
    print_step("7. Tenant A Validates List Isolation")
    res = requests.post(f"{BASE_URL}/meetings", headers={"Authorization": f"Bearer {tokenB}"}, json={"title": "Strategy B"})
    listA = requests.get(f"{BASE_URL}/meetings", headers={"Authorization": f"Bearer {tokenA}"}).json()
    assert len(listA) == 1
    assert listA[0]["id"] == meeting_id
    
    print_step("8. Celery Task Context Validation (Simulation)")
    from app.tasks.pipeline import process_meeting_task
    try:
        # Pass Tenant B's UUID to query Tenant A's Meeting ID
        tenant_B_id = requests.get(f"{BASE_URL}/auth/me", headers={"Authorization": f"Bearer {tokenB}"}).json()["organization_id"]
        process_meeting_task(tenant_id=tenant_B_id, meeting_id=meeting_id)
        assert False, "Worker failed to reject cross-tenant processing"
    except ValueError as e:
        print("Worker correctly rejected mismatched tenant context:", e)
        
    print("\n[PASS] Multi-Tenancy & Isolation boundaries successfully verified.")

finally:
    server.terminate()
    server.wait()
