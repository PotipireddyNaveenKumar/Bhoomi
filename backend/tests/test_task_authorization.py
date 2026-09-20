"""
BHOOMI — Task Authorization & Tenant Isolation Test Suite
Verifies all 10 criteria specified in Master Stabilization Batch 1 Task 2:
1. Authenticated farmer can access own tasks (/today, /week)
2. Authenticated farmer cannot access another farmer's tasks
3. Authenticated farmer cannot mutate another farmer's task (/complete, /postpone, /skip)
4. Unauthenticated request is rejected (HTTP 401)
5. Reviewer demo works through its authorized path (Reviewer Demo login -> authorized farm)
6. Task completion still works for authenticated owner
7. Postpone still works for authenticated owner
8. Skip still works for authenticated owner
9. /today endpoint returns only authorized tasks
10. /week endpoint returns only authorized tasks
"""

import pytest
import asyncio
from decimal import Decimal
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.core.security import create_access_token, get_password_hash
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.models.farmer import FarmerProfile
from app.models.farm import Farm
from app.models.crop import FarmCrop
from app.schemas.task import FarmTask, TaskType, TaskStatus, TaskPriority
from app.services.farm_manager.task_engine import TaskIntelligenceEngine
from app.services.reviewer_provisioning import ensure_reviewer_account

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_tenants_and_tasks():
    """
    Provisions two isolated farmers (Farmer A and Farmer B) and sets up
    tasks in memory for both farms to test tenant isolation.
    """
    async def _setup():
        async with AsyncSessionLocal() as db:
            from sqlalchemy.future import select
            res_a = await db.execute(select(User).where(User.id == "user_tenant_a"))
            if not res_a.scalars().first():
                # 1. Farmer A
                user_a = User(
                    id="user_tenant_a",
                    phone_number="+919111111111",
                    phone_number_verified=True,
                    hashed_password=get_password_hash("password_a_123"),
                    is_active=True
                )
                db.add(user_a)
                await db.flush()

                prof_a = FarmerProfile(
                    id="prof_tenant_a",
                    user_id=user_a.id,
                    name="Farmer Alice",
                    preferred_language="en",
                    state="Andhra Pradesh",
                    district="Guntur",
                    village="Tenali"
                )
                db.add(prof_a)
                await db.flush()

                farm_a = Farm(
                    id="farm_tenant_a",
                    farmer_id=prof_a.id,
                    farm_name="Alice Chilli Farm",
                    total_area_acres=Decimal("2.5"),
                    soil_type="black",
                    irrigation_source="borewell"
                )
                db.add(farm_a)
                await db.flush()

                crop_a = FarmCrop(
                    id="crop_tenant_a",
                    farm_id=farm_a.id,
                    crop_name="Chilli",
                    variety="Teja",
                    area_acres=Decimal("2.5"),
                    current_stage="vegetative"
                )
                db.add(crop_a)
                await db.flush()

            res_b = await db.execute(select(User).where(User.id == "user_tenant_b"))
            if not res_b.scalars().first():
                # 2. Farmer B
                user_b = User(
                    id="user_tenant_b",
                    phone_number="+919222222222",
                    phone_number_verified=True,
                    hashed_password=get_password_hash("password_b_123"),
                    is_active=True
                )
                db.add(user_b)
                await db.flush()

                prof_b = FarmerProfile(
                    id="prof_tenant_b",
                    user_id=user_b.id,
                    name="Farmer Bob",
                    preferred_language="en",
                    state="Telangana",
                    district="Warangal",
                    village="Dharmasagar"
                )
                db.add(prof_b)
                await db.flush()

                farm_b = Farm(
                    id="farm_tenant_b",
                    farmer_id=prof_b.id,
                    farm_name="Bob Cotton Farm",
                    total_area_acres=Decimal("4.0"),
                    soil_type="red",
                    irrigation_source="canal"
                )
                db.add(farm_b)
                await db.flush()

                crop_b = FarmCrop(
                    id="crop_tenant_b",
                    farm_id=farm_b.id,
                    crop_name="Cotton",
                    variety="Bt-Cotton",
                    area_acres=Decimal("4.0"),
                    current_stage="flowering"
                )
                db.add(crop_b)
                await db.flush()

            # Ensure Reviewer account is also provisioned
            await ensure_reviewer_account(db)
            await db.commit()

    asyncio.run(_setup())

    # Populate in-memory tasks for farm A
    task_a1 = FarmTask(
        task_id="task_alice_irrigation_001",
        farm_id="farm_tenant_a",
        title="Irrigate chilli field",
        task_type=TaskType.IRRIGATION,
        crop="Chilli",
        due_at="2026-09-20T08:00:00Z",
        status=TaskStatus.DUE,
        priority=TaskPriority.HIGH,
        trigger="Soil moisture below 30%",
        reason="Soil moisture deficit detected"
    )
    TaskIntelligenceEngine._tasks_by_farm["farm_tenant_a"] = [task_a1]

    # Populate in-memory tasks for farm B
    task_b1 = FarmTask(
        task_id="task_bob_pest_002",
        farm_id="farm_tenant_b",
        title="Scout for bollworm in cotton",
        task_type=TaskType.SPRAYING,
        crop="Cotton",
        due_at="2026-09-20T09:00:00Z",
        status=TaskStatus.DUE,
        priority=TaskPriority.CRITICAL,
        trigger="Pheromone trap threshold exceeded",
        reason="Bollworm pest alert triggered"
    )
    TaskIntelligenceEngine._tasks_by_farm["farm_tenant_b"] = [task_b1]

    yield

    # Cleanup memory
    TaskIntelligenceEngine._tasks_by_farm.pop("farm_tenant_a", None)
    TaskIntelligenceEngine._tasks_by_farm.pop("farm_tenant_b", None)


def _token_for_user(user_id: str) -> str:
    return create_access_token(user_id)


# -----------------------------------------------------------------------------
# 1. Unauthenticated Request Rejected (HTTP 401)
# -----------------------------------------------------------------------------
def test_04_unauthenticated_request_rejected():
    with patch.object(settings, "ENVIRONMENT", "production"), \
         patch.object(settings, "DEMO_MODE", False):
        res_today = client.get("/api/v1/tasks/today")
        assert res_today.status_code == 401, f"Expected 401, got {res_today.status_code}"

        res_week = client.get("/api/v1/tasks/week")
        assert res_week.status_code == 401, f"Expected 401, got {res_week.status_code}"

        res_comp = client.post("/api/v1/tasks/task_alice_irrigation_001/complete", json={})
        assert res_comp.status_code == 401, f"Expected 401, got {res_comp.status_code}"

        res_post = client.post("/api/v1/tasks/task_alice_irrigation_001/postpone", json={"reason": "Rain"})
        assert res_post.status_code == 401, f"Expected 401, got {res_post.status_code}"

        res_skip = client.post("/api/v1/tasks/task_alice_irrigation_001/skip", json={"reason": "Not needed"})
        assert res_skip.status_code == 401, f"Expected 401, got {res_skip.status_code}"


# -----------------------------------------------------------------------------
# 2. Authenticated Farmer Can Access Own Tasks (/today and /week)
# -----------------------------------------------------------------------------
def test_01_authenticated_farmer_access_own_tasks():
    token_a = _token_for_user("user_tenant_a")
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # /today
    res_today = client.get("/api/v1/tasks/today", headers=headers_a)
    assert res_today.status_code == 200
    tasks_today = res_today.json()
    assert isinstance(tasks_today, list)
    # Alice's farm tasks should belong to Chilli / Alice's farm
    assert all(t["crop"] == "Chilli" for t in tasks_today)

    # /week
    res_week = client.get("/api/v1/tasks/week", headers=headers_a)
    assert res_week.status_code == 200
    tasks_week = res_week.json()
    assert isinstance(tasks_week, list)
    assert all(t["crop"] == "Chilli" for t in tasks_week)


# -----------------------------------------------------------------------------
# 3. Authenticated Farmer Cannot Access Another Farmer's Tasks
# -----------------------------------------------------------------------------
def test_02_authenticated_farmer_cannot_access_other_farmer_farm():
    token_a = _token_for_user("user_tenant_a")
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Alice attempts to request tasks using Bob's farm_id
    res_cross = client.get("/api/v1/tasks/today?farm_id=farm_tenant_b", headers=headers_a)
    assert res_cross.status_code == 403, f"Expected 403 Forbidden, got {res_cross.status_code}"
    assert "Specified farm does not belong" in res_cross.json()["detail"]

    res_cross_week = client.get("/api/v1/tasks/week?farm_id=farm_tenant_b", headers=headers_a)
    assert res_cross_week.status_code == 403
    assert "Specified farm does not belong" in res_cross_week.json()["detail"]


# -----------------------------------------------------------------------------
# 4. Authenticated Farmer Cannot Mutate Another Farmer's Task
# -----------------------------------------------------------------------------
def test_03_authenticated_farmer_cannot_mutate_other_farmer_task():
    token_a = _token_for_user("user_tenant_a")
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Alice attempts to complete Bob's task
    res_complete = client.post(
        "/api/v1/tasks/task_bob_pest_002/complete",
        json={"farm_id": "farm_tenant_b"},
        headers=headers_a
    )
    assert res_complete.status_code == 403, f"Expected 403 Forbidden, got {res_complete.status_code}"

    # Alice attempts to complete Bob's task without passing farm_id (server detects ownership violation)
    res_complete_blind = client.post(
        "/api/v1/tasks/task_bob_pest_002/complete",
        json={},
        headers=headers_a
    )
    assert res_complete_blind.status_code == 403, f"Expected 403 Forbidden, got {res_complete_blind.status_code}"

    # Alice attempts to postpone Bob's task
    res_postpone = client.post(
        "/api/v1/tasks/task_bob_pest_002/postpone",
        json={"reason": "Mallicious postpone"},
        headers=headers_a
    )
    assert res_postpone.status_code == 403, f"Expected 403 Forbidden, got {res_postpone.status_code}"

    # Alice attempts to skip Bob's task
    res_skip = client.post(
        "/api/v1/tasks/task_bob_pest_002/skip",
        json={"reason": "Malicious skip"},
        headers=headers_a
    )
    assert res_skip.status_code == 403, f"Expected 403 Forbidden, got {res_skip.status_code}"

    # Verify Bob's task was NOT mutated
    bob_task = next(t for t in TaskIntelligenceEngine._tasks_by_farm["farm_tenant_b"] if t.task_id == "task_bob_pest_002")
    assert bob_task.status == TaskStatus.DUE, "Bob's task status was modified by Alice!"


# -----------------------------------------------------------------------------
# 5. Task Completion Works for Authenticated Owner
# -----------------------------------------------------------------------------
def test_06_task_completion_works_for_owner():
    token_a = _token_for_user("user_tenant_a")
    headers_a = {"Authorization": f"Bearer {token_a}"}

    res = client.post(
        "/api/v1/tasks/task_alice_irrigation_001/complete",
        json={"completion_source": "mobile_app"},
        headers=headers_a
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"].upper() == "COMPLETED"
    assert data["task_id"] == "task_alice_irrigation_001"

    # Verify memory updated
    alice_task = next(t for t in TaskIntelligenceEngine._tasks_by_farm["farm_tenant_a"] if t.task_id == "task_alice_irrigation_001")
    assert alice_task.status == TaskStatus.COMPLETED


# -----------------------------------------------------------------------------
# 6. Postpone Still Works for Authenticated Owner
# -----------------------------------------------------------------------------
def test_07_postpone_works_for_owner():
    # Setup new task for Alice to postpone
    task_post = FarmTask(
        task_id="task_alice_weeding_003",
        farm_id="farm_tenant_a",
        title="Weeding in Chilli bed",
        task_type=TaskType.WEED_MANAGEMENT,
        crop="Chilli",
        due_at="2026-09-20T10:00:00Z",
        status=TaskStatus.DUE,
        priority=TaskPriority.MEDIUM,
        trigger="Scheduled cultural practice",
        reason="Cultural weeding schedule"
    )
    TaskIntelligenceEngine._tasks_by_farm["farm_tenant_a"].append(task_post)

    token_a = _token_for_user("user_tenant_a")
    headers_a = {"Authorization": f"Bearer {token_a}"}

    res = client.post(
        "/api/v1/tasks/task_alice_weeding_003/postpone",
        json={"reason": "Heavy rain forecast", "days_to_postpone": 2},
        headers=headers_a
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"].upper() == "POSTPONED"
    assert data["postponement_reason"] == "Heavy rain forecast"


# -----------------------------------------------------------------------------
# 7. Skip Still Works for Authenticated Owner
# -----------------------------------------------------------------------------
def test_08_skip_works_for_owner():
    task_skip = FarmTask(
        task_id="task_alice_fertilizer_004",
        farm_id="farm_tenant_a",
        title="Apply foliar micronutrients",
        task_type=TaskType.FERTILIZATION,
        crop="Chilli",
        due_at="2026-09-20T11:00:00Z",
        status=TaskStatus.DUE,
        priority=TaskPriority.LOW,
        trigger="Optional booster schedule",
        reason="Routine foliar spray schedule"
    )
    TaskIntelligenceEngine._tasks_by_farm["farm_tenant_a"].append(task_skip)

    token_a = _token_for_user("user_tenant_a")
    headers_a = {"Authorization": f"Bearer {token_a}"}

    res = client.post(
        "/api/v1/tasks/task_alice_fertilizer_004/skip",
        json={"reason": "Foliage looks vigorous, skipping"},
        headers=headers_a
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"].upper() == "SKIPPED"


# -----------------------------------------------------------------------------
# 8. Reviewer Demo Works Through Its Authorized Path
# -----------------------------------------------------------------------------
def test_05_reviewer_demo_task_access():
    # Login as Reviewer Demo
    res_login = client.post("/api/v1/auth/login", json={"is_demo": True})
    assert res_login.status_code == 200
    rev_token = res_login.json()["access_token"]
    rev_headers = {"Authorization": f"Bearer {rev_token}"}

    # Reviewer accesses /today
    res_today = client.get("/api/v1/tasks/today", headers=rev_headers)
    assert res_today.status_code == 200
    tasks = res_today.json()
    assert isinstance(tasks, list)

    # Reviewer accesses /week
    res_week = client.get("/api/v1/tasks/week", headers=rev_headers)
    assert res_week.status_code == 200
    assert isinstance(res_week.json(), list)


# -----------------------------------------------------------------------------
# 9. Non-existent Task Returns 404
# -----------------------------------------------------------------------------
def test_nonexistent_task_returns_404():
    token_a = _token_for_user("user_tenant_a")
    headers_a = {"Authorization": f"Bearer {token_a}"}

    res = client.post(
        "/api/v1/tasks/task_ghost_99999/complete",
        json={},
        headers=headers_a
    )
    assert res.status_code == 404
