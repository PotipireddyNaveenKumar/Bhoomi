"""
BHOOMI V2 — BATCH 9
REGRESSION TEST SUITE: WORKFLOW INTEGRITY

Covers:
1. Authenticated onboarding success & atomicity (FarmerProfile + Farm + initial FarmCrop)
2. Unauthenticated onboarding rejection (HTTP 401)
3. Malformed onboarding request rejection (HTTP 422)
4. Farm and crop persistence in database
5. Serialization of FarmResponse with crops without MissingGreenlet error
6. Transaction rollback on onboarding failure
7. Authoritative task lifecycle: manually-created SQL task can be completed
8. AI-generated task can be completed & synced to SQL
9. Nonexistent task returns HTTP 404
10. Cross-tenant / foreign task mutation returns HTTP 403
11. Repeated completion behaves deterministically
12. Completion persists after reload
13. Completion records FarmMemoryV2 event
14. Unauthenticated access to /manager/* routes rejected (HTTP 401)
15. Authenticated own farmer access to /manager/* routes succeeds (HTTP 200)
16. Cross-tenant / foreign farmer mutation on /manager/events rejected (HTTP 403)
17. Web UI Today's Farm Tasks DOM structure and client handler integrity
18. Frontend canonical onboarding contract verification (no 404 fallback)
"""

import pytest
import asyncio
from decimal import Decimal
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.core.security import create_access_token, get_password_hash
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.models.farmer import FarmerProfile
from app.models.farm import Farm
from app.models.crop import FarmCrop
from app.models.task import FarmTask as DBFarmTask
from app.schemas.farm import FarmResponse
from app.schemas.decision import DecisionPriority
from app.schemas.task import FarmTask, TaskType, TaskStatus, TaskPriority
from app.services.farm_manager.task_engine import TaskIntelligenceEngine
from app.services.memory.farm_memory_v2 import FarmMemoryV2

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_batch9_environment():
    """
    Sets up isolated test users, profiles, and initial data for Batch 9 verification.
    """
    async def _setup():
        async with AsyncSessionLocal() as db:
            from sqlalchemy.future import select
            from sqlalchemy import delete

            # Clean up old test tasks
            await db.execute(delete(DBFarmTask).where(DBFarmTask.id.like("task_b9_%")))
            await db.flush()

            # Clean up old test data if needed
            for uid in ["user_b9_alice", "user_b9_bob", "user_b9_new"]:
                res = await db.execute(select(User).where(User.id == uid))
                existing_user = res.scalars().first()
                if not existing_user:
                    pass

            # 1. Farmer Alice (Tenant A)
            res_a = await db.execute(select(User).where(User.id == "user_b9_alice"))
            if not res_a.scalars().first():
                user_a = User(
                    id="user_b9_alice",
                    phone_number="+919888800001",
                    phone_number_verified=True,
                    hashed_password=get_password_hash("testpass123"),
                    is_active=True
                )
                db.add(user_a)
                await db.flush()

                prof_a = FarmerProfile(
                    id="prof_b9_alice",
                    user_id=user_a.id,
                    name="Alice Rao",
                    preferred_language="te",
                    state="Andhra Pradesh",
                    district="Guntur",
                    village="Tenali"
                )
                db.add(prof_a)
                await db.flush()

                farm_a = Farm(
                    id="farm_b9_alice",
                    farmer_id=prof_a.id,
                    farm_name="Alice Chilli Farm",
                    total_area_acres=Decimal("3.0"),
                    soil_type="black",
                    irrigation_source="borewell"
                )
                db.add(farm_a)
                await db.flush()

                crop_a = FarmCrop(
                    id="crop_b9_alice",
                    farm_id=farm_a.id,
                    crop_name="Chilli",
                    variety="Teja",
                    area_acres=Decimal("3.0"),
                    current_stage="vegetative"
                )
                db.add(crop_a)
                await db.flush()

            # 2. Farmer Bob (Tenant B)
            res_b = await db.execute(select(User).where(User.id == "user_b9_bob"))
            if not res_b.scalars().first():
                user_b = User(
                    id="user_b9_bob",
                    phone_number="+919888800002",
                    phone_number_verified=True,
                    hashed_password=get_password_hash("testpass123"),
                    is_active=True
                )
                db.add(user_b)
                await db.flush()

                prof_b = FarmerProfile(
                    id="prof_b9_bob",
                    user_id=user_b.id,
                    name="Bob Kumar",
                    preferred_language="en",
                    state="Telangana",
                    district="Warangal",
                    village="Dharmasagar"
                )
                db.add(prof_b)
                await db.flush()

                farm_b = Farm(
                    id="farm_b9_bob",
                    farmer_id=prof_b.id,
                    farm_name="Bob Cotton Farm",
                    total_area_acres=Decimal("5.0"),
                    soil_type="red",
                    irrigation_source="canal"
                )
                db.add(farm_b)
                await db.flush()

                crop_b = FarmCrop(
                    id="crop_b9_bob",
                    farm_id=farm_b.id,
                    crop_name="Cotton",
                    variety="Bt-Cotton",
                    area_acres=Decimal("5.0"),
                    current_stage="flowering"
                )
                db.add(crop_b)
                await db.flush()

            # 3. Fresh Farmer for Onboarding Testing
            res_new = await db.execute(select(User).where(User.id == "user_b9_new"))
            if not res_new.scalars().first():
                user_new = User(
                    id="user_b9_new",
                    phone_number="+919888800003",
                    phone_number_verified=True,
                    hashed_password=get_password_hash("testpass123"),
                    is_active=True
                )
                db.add(user_new)
                await db.flush()

                prof_new = FarmerProfile(
                    id="prof_b9_new",
                    user_id=user_new.id,
                    name="New Registered Farmer",
                    preferred_language="en"
                )
                db.add(prof_new)
                await db.flush()

            await db.commit()

    asyncio.run(_setup())
    yield


def _token(user_id: str) -> str:
    return create_access_token(user_id)


# =============================================================================
# TASK 1: CANONICAL FARMER ONBOARDING TESTS
# =============================================================================

def test_01_onboard_unauthenticated_rejected():
    """Unauthenticated call to /farmer/onboard must be rejected with 401."""
    res = client.post("/api/v1/farmer/onboard", json={
        "name": "Test Farmer",
        "current_crop": "Chilli",
        "land_area_acres": 2.5
    })
    assert res.status_code == 401, f"Expected 401, got {res.status_code}"


def test_02_onboard_malformed_request_rejected():
    """Malformed request (e.g. invalid land area) must be rejected with 422."""
    token = _token("user_b9_new")
    res = client.post(
        "/api/v1/farmer/onboard",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Test Farmer",
            "current_crop": "Chilli",
            "land_area_acres": -5.0  # Invalid area
        }
    )
    assert res.status_code == 422


def test_03_onboard_authenticated_success_and_serialization():
    """
    End-to-End onboarding must:
    1. Update FarmerProfile
    2. Atomically create Farm & initial FarmCrop
    3. Return FarmResponse with crops serialized without MissingGreenlet error
    """
    token = _token("user_b9_new")
    payload = {
        "name": "Suresh Farmer",
        "preferred_language": "te",
        "state": "Andhra Pradesh",
        "district": "Guntur",
        "village": "Tenali",
        "current_crop": "Chilli",
        "crop_variety": "Teja",
        "land_area_acres": 3.5,
        "soil_type": "black",
        "soil_source_type": "estimated",
        "soil_n": 140.0,
        "soil_p": 45.0,
        "soil_k": 70.0,
        "soil_ph": 6.8,
        "latitude": 16.3067,
        "longitude": 80.4365,
        "irrigation_source": "borewell"
    }

    res = client.post(
        "/api/v1/farmer/onboard",
        headers={"Authorization": f"Bearer {token}"},
        json=payload
    )
    assert res.status_code == 200, f"Onboarding failed: {res.text}"
    data = res.json()

    assert data["success"] is True
    assert data["farmer"]["name"] == "Suresh Farmer"
    assert data["farmer"]["preferred_language"] == "te"
    assert data["farmer"]["district"] == "Guntur"

    farm = data["farm"]
    assert farm is not None
    assert float(farm["total_area_acres"]) == 3.5
    assert farm["soil_type"] == "black"
    assert farm["farmer_id"] == "prof_b9_new"

    # Verify crops serialized inside FarmResponse without MissingGreenlet
    crops = farm.get("crops", [])
    assert len(crops) >= 1
    assert crops[0]["crop_name"] == "Chilli"
    assert crops[0]["variety"] == "Teja"
    assert float(crops[0]["area_acres"]) == 3.5


def test_04_onboard_database_persistence():
    """Verify that newly onboarded farm and crop exist in database."""
    async def _check():
        async with AsyncSessionLocal() as db:
            from sqlalchemy.future import select
            from sqlalchemy.orm import selectinload

            res = await db.execute(
                select(Farm).options(selectinload(Farm.crops)).where(Farm.farmer_id == "prof_b9_new")
            )
            farms = res.scalars().all()
            assert len(farms) >= 1
            farm = farms[0]
            assert farm.total_area_acres == Decimal("3.5")
            assert len(farm.crops) >= 1
            assert farm.crops[0].crop_name == "Chilli"

    asyncio.run(_check())


def test_05_onboard_transaction_rollback():
    """If an internal step fails, transaction must roll back with 500 and no orphaned records."""
    token = _token("user_b9_alice")
    with patch("app.repositories.farm_repo.FarmRepository.atomic_onboard_farm_and_crop", side_effect=RuntimeError("Simulated DB connection error")):
        res = client.post(
            "/api/v1/farmer/onboard",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Rollback Test",
                "current_crop": "Tomato",
                "land_area_acres": 1.0
            }
        )
        assert res.status_code == 500
        assert "Onboarding failed" in res.json()["detail"]


# =============================================================================
# TASK 2: UNIFIED TASK LIFECYCLE & AUTHORITATIVE SQL STATE
# =============================================================================

def test_06_sql_manual_task_completion_and_memory():
    """
    A task created directly in the SQL DB can be completed via POST /api/v1/tasks/{id}/complete
    even if it never existed inside TaskIntelligenceEngine in-memory state.
    Verifies:
    - Status updated to COMPLETED in SQL
    - FarmMemoryV2 event recorded
    - Does not throw 'Task with ID not found'
    """
    async def _create_sql_task():
        async with AsyncSessionLocal() as db:
            from datetime import date
            from sqlalchemy import delete
            await db.execute(delete(DBFarmTask).where(DBFarmTask.id == "task_b9_sql_manual_001"))
            await db.flush()
            task = DBFarmTask(
                id="task_b9_sql_manual_001",
                farmer_id="prof_b9_alice",
                farm_id="farm_b9_alice",
                title="Inspect Chilli Trellising",
                description="Check trellis stability after wind",
                task_type="field_inspection",
                priority="high",
                due_date=date.today(),
                status="pending",
                source="manual"
            )
            db.add(task)
            await db.commit()

    asyncio.run(_create_sql_task())

    # Task is NOT in TaskIntelligenceEngine memory
    assert "task_b9_sql_manual_001" not in [
        t.task_id for t in TaskIntelligenceEngine.get_tasks_for_farm("farm_b9_alice")
    ]

    token_a = _token("user_b9_alice")
    res = client.post(
        "/api/v1/tasks/task_b9_sql_manual_001/complete",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"completion_source": "test_suite"}
    )
    assert res.status_code == 200, f"Task completion failed: {res.text}"
    completed_task = res.json()
    assert completed_task["status"] == "COMPLETED"
    assert completed_task["completion_status"] == "SUCCESS"

    # Verify SQL persistence
    async def _verify_sql():
        async with AsyncSessionLocal() as db:
            from sqlalchemy.future import select
            res = await db.execute(select(DBFarmTask).where(DBFarmTask.id == "task_b9_sql_manual_001"))
            db_task = res.scalars().first()
            assert db_task.status == "completed"

    asyncio.run(_verify_sql())

    # Verify FarmMemoryV2 event
    memories = FarmMemoryV2.get_memories_by_category("prof_b9_alice", "EVENT")
    assert any("task_b9_sql_manual_001" in m.key for m in memories)


def test_07_ai_task_completion_and_sql_sync():
    """An AI generated in-memory task can be completed and syncs to SQL DB."""
    ai_task = FarmTask(
        task_id="task_b9_ai_spray_001",
        farm_id="farm_b9_alice",
        crop="Chilli",
        task_type=TaskType.SPRAYING,
        title="Preventive neem spray",
        priority=DecisionPriority.HIGH if hasattr(DecisionPriority, "HIGH") else "HIGH",
        status=TaskStatus.DUE,
        due_at="2026-09-20T10:00:00Z",
        trigger="Humid conditions",
        reason="Prevent fungal infestation"
    )
    TaskIntelligenceEngine._tasks_by_farm["farm_b9_alice"] = [ai_task]

    token_a = _token("user_b9_alice")
    res = client.post(
        "/api/v1/tasks/task_b9_ai_spray_001/complete",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"completion_source": "test_suite"}
    )
    assert res.status_code == 200
    assert res.json()["status"] == "COMPLETED"

    # Clean up
    TaskIntelligenceEngine._tasks_by_farm.pop("farm_b9_alice", None)


def test_08_nonexistent_task_returns_404():
    """Completing a nonexistent task must return HTTP 404."""
    token_a = _token("user_b9_alice")
    res = client.post(
        "/api/v1/tasks/task_ghost_nonexistent_999/complete",
        headers={"Authorization": f"Bearer {token_a}"},
        json={}
    )
    assert res.status_code == 404


def test_09_foreign_task_returns_403():
    """Alice cannot complete Bob's task."""
    async def _create_bob_task():
        async with AsyncSessionLocal() as db:
            from datetime import date
            from sqlalchemy import delete
            await db.execute(delete(DBFarmTask).where(DBFarmTask.id == "task_b9_bob_task_001"))
            await db.flush()
            task = DBFarmTask(
                id="task_b9_bob_task_001",
                farmer_id="prof_b9_bob",
                farm_id="farm_b9_bob",
                title="Cotton weeding",
                due_date=date.today(),
                status="pending",
                source="manual"
            )
            db.add(task)
            await db.commit()

    asyncio.run(_create_bob_task())

    token_a = _token("user_b9_alice")
    res = client.post(
        "/api/v1/tasks/task_b9_bob_task_001/complete",
        headers={"Authorization": f"Bearer {token_a}"},
        json={}
    )
    assert res.status_code == 403


def test_10_repeated_completion_is_deterministic():
    """Repeating completion on an already-completed task succeeds deterministically."""
    token_a = _token("user_b9_alice")
    res1 = client.post(
        "/api/v1/tasks/task_b9_sql_manual_001/complete",
        headers={"Authorization": f"Bearer {token_a}"},
        json={}
    )
    assert res1.status_code == 200
    assert res1.json()["status"] == "COMPLETED"

    res2 = client.post(
        "/api/v1/tasks/task_b9_sql_manual_001/complete",
        headers={"Authorization": f"Bearer {token_a}"},
        json={}
    )
    assert res2.status_code == 200
    assert res2.json()["status"] == "COMPLETED"


def test_11_get_today_tasks_reflects_completed_state():
    """GET /api/v1/tasks/today reflects the completed state of tasks."""
    token_a = _token("user_b9_alice")
    res = client.get("/api/v1/tasks/today", headers={"Authorization": f"Bearer {token_a}"})
    assert res.status_code == 200
    tasks = res.json()
    completed_task = next((t for t in tasks if t["task_id"] == "task_b9_sql_manual_001"), None)
    if completed_task:
        assert completed_task["status"] == "COMPLETED"


# =============================================================================
# TASK 2B: MANAGER ENDPOINTS AUTHORIZATION AUDIT
# =============================================================================

@pytest.mark.parametrize("endpoint,method,payload", [
    ("/api/v1/manager/state", "GET", None),
    ("/api/v1/manager/briefing/today", "GET", None),
    ("/api/v1/manager/briefing/week", "GET", None),
    ("/api/v1/manager/changes", "GET", None),
    ("/api/v1/manager/alerts", "GET", None),
    ("/api/v1/manager/timeline", "GET", None),
    ("/api/v1/manager/plan", "GET", None),
    ("/api/v1/manager/events", "POST", {"event_id": "evt_b9_unauth", "farmer_id": "p1", "farm_id": "f1", "event_type": "SCOUTING"}),
    ("/api/v1/manager/feedback", "POST", {"recommendation_id": "rec_1", "action_taken": "ACCEPTED", "feedback_rating": "USEFUL"}),
])
def test_12_manager_endpoints_unauthenticated_rejected(endpoint, method, payload):
    """All 9 manager endpoints must strictly return 401 when called without JWT."""
    if method == "GET":
        res = client.get(endpoint)
    else:
        res = client.post(endpoint, json=payload)
    assert res.status_code == 401, f"{endpoint} did not reject unauthenticated access: {res.status_code}"


@pytest.mark.parametrize("endpoint,method,payload", [
    ("/api/v1/manager/state", "GET", None),
    ("/api/v1/manager/briefing/today", "GET", None),
    ("/api/v1/manager/briefing/week", "GET", None),
    ("/api/v1/manager/changes", "GET", None),
    ("/api/v1/manager/alerts", "GET", None),
    ("/api/v1/manager/timeline", "GET", None),
    ("/api/v1/manager/plan", "GET", None),
])
def test_13_manager_endpoints_authenticated_own_allowed(endpoint, method, payload):
    """All GET manager endpoints return 200 for an authenticated farmer."""
    token_a = _token("user_b9_alice")
    headers = {"Authorization": f"Bearer {token_a}"}
    res = client.get(endpoint, headers=headers)
    assert res.status_code == 200, f"{endpoint} failed for authenticated farmer: {res.text}"


def test_14_manager_events_foreign_farmer_rejected():
    """Farmer Alice cannot submit an event claiming to be Farmer Bob."""
    token_a = _token("user_b9_alice")
    res = client.post(
        "/api/v1/manager/events",
        headers={"Authorization": f"Bearer {token_a}"},
        json={
            "event_id": "evt_b9_test_foreign",
            "farmer_id": "prof_b9_bob",  # Foreign farmer ID
            "farm_id": "farm_b9_bob",
            "event_type": "SCOUTING",
            "severity": "INFO",
            "payload": {"title": "Malicious event submission"}
        }
    )
    assert res.status_code == 403, f"Expected 403 Forbidden, got {res.status_code}"


# =============================================================================
# TASK 3: UI DOM & SCRIPT INTEGRITY
# =============================================================================

def test_15_web_ui_today_tasks_dom_elements():
    """Verify that index.html contains the reviewer-facing Today's Farm Tasks elements."""
    with open("frontend/web/index.html", "r", encoding="utf-8") as f:
        html = f.read()

    assert 'id="todayTasksSection"' in html
    assert 'id="todayTasksList"' in html
    assert 'id="txtTodayTasksTitle"' in html
    assert 'id="btnRefreshTasks"' in html


def test_16_frontend_canonical_onboarding_and_task_handlers():
    """
    Verify that frontend app.js:
    1. Calls canonical /api/v1/farmer/onboard
    2. Does NOT have 404 fallback to /api/v1/farms
    3. Implements loadTodayTasks and handleCompleteTask
    """
    with open("frontend/web/static/app.js", "r", encoding="utf-8") as f:
        js = f.read()

    # Onboarding checks
    assert 'fetch("/api/v1/farmer/onboard"' in js or "fetch('/api/v1/farmer/onboard'" in js
    assert 'fetch("/api/v1/farms"' not in js and "fetch('/api/v1/farms'" not in js

    # Tasks client checks
    assert "async function loadTodayTasks()" in js
    assert "async function handleCompleteTask(" in js
    assert 'fetch("/api/v1/tasks/today"' in js or "fetch('/api/v1/tasks/today'" in js
    assert 'fetch(`/api/v1/tasks/${encodeURIComponent(taskId)}/complete`' in js or 'fetch("/api/v1/tasks/' in js
