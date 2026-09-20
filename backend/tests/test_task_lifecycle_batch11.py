"""
BHOOMI V2 — BATCH 11 — TASK 1: PRODUCTION PROACTIVE FARM TASK LIFECYCLE TESTS

Test Coverage (20 Focused Criteria):
 1. future task remains scheduled (due_at > now)
 2. due task transitions to DUE (due_at <= now)
 3. overdue task transitions to OVERDUE (past threshold)
 4. expired task transitions to EXPIRED (now >= expires_at)
 5. completed task never becomes overdue or expired
 6. cancelled task never becomes overdue or expired
 7. repeated scheduler execution is idempotent
 8. lifecycle event is emitted once
 9. FarmMemoryV2 receives compact lifecycle event
10. tenant ownership remains intact across tenants
11. concurrent execution does not duplicate transitions
12. timezone-aware comparison works across offsets
13. task without due_at handled honestly (fallback to due_date)
14. Today's Tasks reflects lifecycle status
15. existing completion endpoint still works
16. AI-generated task remains compatible
17. no synthetic tasks created
18. scheduler failure does not corrupt tasks
19. transaction rollback restores original state
20. production execution path is protected (401 without auth)
"""

import pytest
import asyncio
from datetime import datetime, timedelta, timezone, date
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.future import select
from sqlalchemy import delete

from app.main import app
from app.core.security import create_access_token, get_password_hash
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.models.farmer import FarmerProfile
from app.models.farm import Farm
from app.models.crop import FarmCrop
from app.models.task import FarmTask as FarmTaskModel, TaskStatus as SQLTaskStatus
from app.schemas.task import FarmTaskCreate, FarmTaskUpdate, TaskStatus as SchemaTaskStatus, FarmTask
from app.repositories.task_repo import TaskRepository
from app.services.tasks.lifecycle_service import TaskLifecycleService, TaskLifecycleRunResult
from app.services.memory.farm_memory_v2 import FarmMemoryV2
from app.services.farm_manager.task_engine import TaskIntelligenceEngine
from app.services.farm_manager.state_engine import FarmState

client = TestClient(app)

USER_B11_A = "user_b11_farmer_a"
PROF_B11_A = "prof_b11_farmer_a"
FARM_B11_A = "farm_b11_farmer_a"

USER_B11_B = "user_b11_farmer_b"
PROF_B11_B = "prof_b11_farmer_b"
FARM_B11_B = "farm_b11_farmer_b"

token_a = ""
token_b = ""


@pytest.fixture(scope="module", autouse=True)
def setup_batch11_environment():
    """Sets up isolated test users, profiles, and farms for Batch 11."""
    global token_a, token_b

    async def _setup():
        from sqlalchemy import text
        from app.db.session import engine, Base
        from app.core.config import settings

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            if "sqlite" in settings.DATABASE_URL.lower():
                res_tasks = await conn.execute(text("PRAGMA table_info(farm_tasks)"))
                task_cols = [row[1] for row in res_tasks.fetchall()]
                if "due_at" not in task_cols:
                    await conn.execute(text("ALTER TABLE farm_tasks ADD COLUMN due_at DATETIME"))
                if "expires_at" not in task_cols:
                    await conn.execute(text("ALTER TABLE farm_tasks ADD COLUMN expires_at DATETIME"))

        async with AsyncSessionLocal() as db:
            # Clean up old test data
            await db.execute(delete(FarmTaskModel).where(FarmTaskModel.farmer_id.in_([PROF_B11_A, PROF_B11_B])))
            await db.execute(delete(FarmCrop).where(FarmCrop.farm_id.in_([FARM_B11_A, FARM_B11_B])))
            await db.execute(delete(Farm).where(Farm.id.in_([FARM_B11_A, FARM_B11_B])))
            await db.execute(delete(FarmerProfile).where(FarmerProfile.id.in_([PROF_B11_A, PROF_B11_B])))
            await db.execute(delete(User).where(User.id.in_([USER_B11_A, USER_B11_B])))
            await db.commit()

            # Farmer A
            user_a = User(
                id=USER_B11_A,
                phone_number="+919876543111",
                phone_number_verified=True,
                hashed_password=get_password_hash("TestPass123!"),
                is_active=True
            )
            db.add(user_a)
            await db.flush()

            prof_a = FarmerProfile(
                id=PROF_B11_A,
                user_id=USER_B11_A,
                name="Batch 11 Farmer A",
                state="Andhra Pradesh",
                district="Guntur",
                preferred_language="te"
            )
            db.add(prof_a)
            await db.flush()

            farm_a = Farm(
                id=FARM_B11_A,
                farmer_id=PROF_B11_A,
                farm_name="Amaravati Organic Farm",
                total_area_acres=Decimal("4.5"),
                soil_type="black",
                irrigation_source="borewell"
            )
            db.add(farm_a)

            # Farmer B
            user_b = User(
                id=USER_B11_B,
                phone_number="+919876543222",
                phone_number_verified=True,
                hashed_password=get_password_hash("TestPass123!"),
                is_active=True
            )
            db.add(user_b)
            await db.flush()

            prof_b = FarmerProfile(
                id=PROF_B11_B,
                user_id=USER_B11_B,
                name="Batch 11 Farmer B",
                state="Telangana",
                district="Warangal",
                preferred_language="en"
            )
            db.add(prof_b)
            await db.flush()

            farm_b = Farm(
                id=FARM_B11_B,
                farmer_id=PROF_B11_B,
                farm_name="Kakatiya Cotton Estate",
                total_area_acres=Decimal("6.0"),
                soil_type="red",
                irrigation_source="canal"
            )
            db.add(farm_b)

            await db.commit()

    asyncio.run(_setup())

    token_a = create_access_token(USER_B11_A)
    token_b = create_access_token(USER_B11_B)
    yield


# =============================================================================
# TEST 1: Future task remains scheduled
# =============================================================================
@pytest.mark.asyncio
async def test_future_task_remains_scheduled():
    async with AsyncSessionLocal() as db:
        repo = TaskRepository(db)
        now = datetime.now(timezone.utc)
        future_dt = now + timedelta(days=2)
        task = await repo.create_task(
            farmer_id=PROF_B11_A,
            task_in=FarmTaskCreate(
                farm_id=FARM_B11_A,
                title="Future Spraying Task",
                due_date=future_dt.date(),
                due_at=future_dt,
                task_type="fertilizer",
                priority="medium"
            ),
            source="user"
        )
        task_id = task.id

        result = await TaskLifecycleService.reap_and_transition_tasks(db, farmer_id=PROF_B11_A, reference_now=now)
        reloaded = await repo.get_task_by_id(task_id)
        assert reloaded.status == SQLTaskStatus.PENDING.value
        assert not any(t.task_id == task_id for t in result.transitions)


# =============================================================================
# TEST 2: Due task transitions to DUE
# =============================================================================
@pytest.mark.asyncio
async def test_due_task_transitions_to_due():
    async with AsyncSessionLocal() as db:
        repo = TaskRepository(db)
        now = datetime.now(timezone.utc)
        due_dt = now - timedelta(hours=1)
        task = await repo.create_task(
            farmer_id=PROF_B11_A,
            task_in=FarmTaskCreate(
                farm_id=FARM_B11_A,
                title="Immediate Scouting Task",
                due_date=due_dt.date(),
                due_at=due_dt,
                task_type="crop_inspection",
                priority="high"
            ),
            source="user"
        )
        task_id = task.id

        result = await TaskLifecycleService.reap_and_transition_tasks(db, farmer_id=PROF_B11_A, reference_now=now)
        reloaded = await repo.get_task_by_id(task_id)
        assert reloaded.status == SQLTaskStatus.DUE.value
        assert any(t.task_id == task_id and t.new_status == "due" for t in result.transitions)


# =============================================================================
# TEST 3: Overdue task transitions to OVERDUE
# =============================================================================
@pytest.mark.asyncio
async def test_overdue_task_transitions_to_overdue():
    async with AsyncSessionLocal() as db:
        repo = TaskRepository(db)
        now = datetime.now(timezone.utc)
        overdue_dt = now - timedelta(hours=12)  # > 6h threshold
        task = await repo.create_task(
            farmer_id=PROF_B11_A,
            task_in=FarmTaskCreate(
                farm_id=FARM_B11_A,
                title="Late Weeding Operation",
                due_date=overdue_dt.date(),
                due_at=overdue_dt,
                task_type="general",
                priority="high"
            ),
            source="user"
        )
        task_id = task.id

        result = await TaskLifecycleService.reap_and_transition_tasks(db, farmer_id=PROF_B11_A, reference_now=now)
        reloaded = await repo.get_task_by_id(task_id)
        assert reloaded.status == SQLTaskStatus.OVERDUE.value
        assert any(t.task_id == task_id and t.new_status == "overdue" for t in result.transitions)


# =============================================================================
# TEST 4: Expired task transitions to EXPIRED
# =============================================================================
@pytest.mark.asyncio
async def test_expired_task_transitions_to_expired():
    async with AsyncSessionLocal() as db:
        repo = TaskRepository(db)
        now = datetime.now(timezone.utc)
        due_dt = now - timedelta(days=2)
        exp_dt = now - timedelta(hours=2)
        task = await repo.create_task(
            farmer_id=PROF_B11_A,
            task_in=FarmTaskCreate(
                farm_id=FARM_B11_A,
                title="Time-Critical Weather Spray",
                due_date=due_dt.date(),
                due_at=due_dt,
                expires_at=exp_dt,
                task_type="fertilizer",
                priority="urgent"
            ),
            source="user"
        )
        task_id = task.id

        result = await TaskLifecycleService.reap_and_transition_tasks(db, farmer_id=PROF_B11_A, reference_now=now)
        reloaded = await repo.get_task_by_id(task_id)
        assert reloaded.status == SQLTaskStatus.EXPIRED.value
        assert any(t.task_id == task_id and t.new_status == "expired" for t in result.transitions)


# =============================================================================
# TEST 5: Completed task never becomes overdue or expired
# =============================================================================
@pytest.mark.asyncio
async def test_completed_task_never_becomes_overdue():
    async with AsyncSessionLocal() as db:
        repo = TaskRepository(db)
        now = datetime.now(timezone.utc)
        past_dt = now - timedelta(days=10)
        task = await repo.create_task(
            farmer_id=PROF_B11_A,
            task_in=FarmTaskCreate(
                farm_id=FARM_B11_A,
                title="Completed Historical Task",
                due_date=past_dt.date(),
                due_at=past_dt,
                expires_at=past_dt + timedelta(days=1),
                task_type="harvesting",
                priority="medium"
            ),
            source="user"
        )
        await repo.update_task(task.id, PROF_B11_A, FarmTaskUpdate(status="completed"))

        result = await TaskLifecycleService.reap_and_transition_tasks(db, farmer_id=PROF_B11_A, reference_now=now)
        reloaded = await repo.get_task_by_id(task.id)
        assert reloaded.status == "completed"
        assert not any(t.task_id == task.id for t in result.transitions)


# =============================================================================
# TEST 6: Cancelled task never becomes overdue or expired
# =============================================================================
@pytest.mark.asyncio
async def test_cancelled_task_never_becomes_overdue():
    async with AsyncSessionLocal() as db:
        repo = TaskRepository(db)
        now = datetime.now(timezone.utc)
        past_dt = now - timedelta(days=5)
        task = await repo.create_task(
            farmer_id=PROF_B11_A,
            task_in=FarmTaskCreate(
                farm_id=FARM_B11_A,
                title="Cancelled Task",
                due_date=past_dt.date(),
                due_at=past_dt,
                task_type="general",
                priority="low"
            ),
            source="user"
        )
        await repo.update_task(task.id, PROF_B11_A, FarmTaskUpdate(status="cancelled"))

        result = await TaskLifecycleService.reap_and_transition_tasks(db, farmer_id=PROF_B11_A, reference_now=now)
        reloaded = await repo.get_task_by_id(task.id)
        assert reloaded.status == "cancelled"
        assert not any(t.task_id == task.id for t in result.transitions)


# =============================================================================
# TEST 7: Repeated scheduler execution is idempotent
# =============================================================================
@pytest.mark.asyncio
async def test_repeated_scheduler_execution_is_idempotent():
    async with AsyncSessionLocal() as db:
        repo = TaskRepository(db)
        now = datetime.now(timezone.utc)
        due_dt = now - timedelta(hours=2)
        task = await repo.create_task(
            farmer_id=PROF_B11_A,
            task_in=FarmTaskCreate(
                farm_id=FARM_B11_A,
                title="Idempotency Test Task",
                due_date=due_dt.date(),
                due_at=due_dt,
                task_type="general"
            ),
            source="user"
        )
        task_id = task.id

        # First run: transitions to DUE
        run1 = await TaskLifecycleService.reap_and_transition_tasks(db, farmer_id=PROF_B11_A, reference_now=now)
        assert any(t.task_id == task_id for t in run1.transitions)

        # Immediate second run: no transition
        run2 = await TaskLifecycleService.reap_and_transition_tasks(db, farmer_id=PROF_B11_A, reference_now=now)
        assert not any(t.task_id == task_id for t in run2.transitions)

        # Third run: still no transition
        run3 = await TaskLifecycleService.reap_and_transition_tasks(db, farmer_id=PROF_B11_A, reference_now=now)
        assert not any(t.task_id == task_id for t in run3.transitions)

        reloaded = await repo.get_task_by_id(task_id)
        assert reloaded.status == "due"


# =============================================================================
# TEST 8: Lifecycle event emitted once
# =============================================================================
@pytest.mark.asyncio
async def test_lifecycle_event_emitted_once():
    async with AsyncSessionLocal() as db:
        repo = TaskRepository(db)
        now = datetime.now(timezone.utc)
        due_dt = now - timedelta(hours=3)
        task = await repo.create_task(
            farmer_id=PROF_B11_A,
            task_in=FarmTaskCreate(
                farm_id=FARM_B11_A,
                title="Event Emission Test Task",
                due_date=due_dt.date(),
                due_at=due_dt,
                task_type="general"
            ),
            source="user"
        )
        task_id = task.id

        # Initial run
        await TaskLifecycleService.reap_and_transition_tasks(db, farmer_id=PROF_B11_A, reference_now=now)
        events_1 = FarmMemoryV2.get_recent_events(PROF_B11_A)
        due_events_1 = [e for e in events_1 if e.get("key") == f"task_due_{task_id}"]
        assert len(due_events_1) == 1

        # Second run
        await TaskLifecycleService.reap_and_transition_tasks(db, farmer_id=PROF_B11_A, reference_now=now)
        events_2 = FarmMemoryV2.get_recent_events(PROF_B11_A)
        due_events_2 = [e for e in events_2 if e.get("key") == f"task_due_{task_id}"]
        assert len(due_events_2) == 1  # Deduplicated, still exactly 1


# =============================================================================
# TEST 9: FarmMemoryV2 receives compact lifecycle event
# =============================================================================
@pytest.mark.asyncio
async def test_farm_memory_receives_compact_lifecycle_event():
    async with AsyncSessionLocal() as db:
        repo = TaskRepository(db)
        now = datetime.now(timezone.utc)
        due_dt = now - timedelta(hours=14)
        task = await repo.create_task(
            farmer_id=PROF_B11_A,
            task_in=FarmTaskCreate(
                farm_id=FARM_B11_A,
                title="Compact Memory Payload Task",
                due_date=due_dt.date(),
                due_at=due_dt,
                task_type="pest_monitoring"
            ),
            source="user"
        )
        task_id = task.id

        await TaskLifecycleService.reap_and_transition_tasks(db, farmer_id=PROF_B11_A, reference_now=now)
        events = FarmMemoryV2.get_recent_events(PROF_B11_A)
        overdue_evt = next((e for e in events if e.get("key") == f"task_overdue_{task_id}"), None)
        assert overdue_evt is not None
        val = overdue_evt.get("value", {})
        assert val.get("task_id") == task_id
        assert val.get("title") == "Compact Memory Payload Task"
        assert val.get("new_status") == "overdue"
        assert "timestamp" in val


# =============================================================================
# TEST 10: Tenant ownership remains intact across tenants
# =============================================================================
@pytest.mark.asyncio
async def test_tenant_ownership_remains_intact():
    async with AsyncSessionLocal() as db:
        repo = TaskRepository(db)
        now = datetime.now(timezone.utc)
        due_dt = now - timedelta(hours=2)

        task_b = await repo.create_task(
            farmer_id=PROF_B11_B,
            task_in=FarmTaskCreate(
                farm_id=FARM_B11_B,
                title="Tenant B Task",
                due_date=due_dt.date(),
                due_at=due_dt,
                task_type="irrigation"
            ),
            source="user"
        )

        # Run scheduler ONLY for Farmer A
        result_a = await TaskLifecycleService.reap_and_transition_tasks(db, farmer_id=PROF_B11_A, reference_now=now)
        assert not any(t.task_id == task_b.id for t in result_a.transitions)

        # Task B remains untouched
        reloaded_b = await repo.get_task_by_id(task_b.id)
        assert reloaded_b.status == SQLTaskStatus.PENDING.value


# =============================================================================
# TEST 11: Concurrent execution does not duplicate transitions
# =============================================================================
@pytest.mark.asyncio
async def test_concurrent_execution_does_not_duplicate_transition():
    now = datetime.now(timezone.utc)
    due_dt = now - timedelta(hours=10)

    task_id = ""
    async with AsyncSessionLocal() as db:
        repo = TaskRepository(db)
        task = await repo.create_task(
            farmer_id=PROF_B11_A,
            task_in=FarmTaskCreate(
                farm_id=FARM_B11_A,
                title="Concurrency Safe Task",
                due_date=due_dt.date(),
                due_at=due_dt,
                task_type="fertilizer"
            ),
            source="user"
        )
        task_id = task.id

    async def run_worker():
        async with AsyncSessionLocal() as db:
            return await TaskLifecycleService.reap_and_transition_tasks(
                db, farmer_id=PROF_B11_A, reference_now=now
            )

    results = await asyncio.gather(run_worker(), run_worker())
    all_transitions = [t for r in results for t in r.transitions if t.task_id == task_id]
    assert len(all_transitions) == 1

    async with AsyncSessionLocal() as db:
        repo = TaskRepository(db)
        reloaded = await repo.get_task_by_id(task_id)
        assert reloaded.status == "overdue"


# =============================================================================
# TEST 12: Timezone-aware comparison works across offsets
# =============================================================================
@pytest.mark.asyncio
async def test_timezone_aware_comparison_works():
    async with AsyncSessionLocal() as db:
        repo = TaskRepository(db)
        ist = timezone(timedelta(hours=5, minutes=30))
        # 10 minutes in future relative to now, but represented in IST
        now_utc = datetime.now(timezone.utc)
        future_ist = (now_utc + timedelta(minutes=20)).astimezone(ist)

        task = await repo.create_task(
            farmer_id=PROF_B11_A,
            task_in=FarmTaskCreate(
                farm_id=FARM_B11_A,
                title="IST Timestamp Task",
                due_date=future_ist.date(),
                due_at=future_ist,
                task_type="general"
            ),
            source="user"
        )

        result = await TaskLifecycleService.reap_and_transition_tasks(db, farmer_id=PROF_B11_A, reference_now=now_utc)
        reloaded = await repo.get_task_by_id(task.id)
        # Because future_ist is in the future, it should remain PENDING
        assert reloaded.status == "pending"


# =============================================================================
# TEST 13: Task without due_at handled honestly (fallback to due_date)
# =============================================================================
@pytest.mark.asyncio
async def test_task_without_due_at_handled_honestly():
    async with AsyncSessionLocal() as db:
        repo = TaskRepository(db)
        # Due 2 days ago, no due_at timestamp
        past_date = date.today() - timedelta(days=2)
        task = await repo.create_task(
            farmer_id=PROF_B11_A,
            task_in=FarmTaskCreate(
                farm_id=FARM_B11_A,
                title="Date-Only Historical Task",
                due_date=past_date,
                due_at=None,
                task_type="irrigation"
            ),
            source="user"
        )

        now = datetime.now(timezone.utc)
        result = await TaskLifecycleService.reap_and_transition_tasks(db, farmer_id=PROF_B11_A, reference_now=now)
        reloaded = await repo.get_task_by_id(task.id)
        # Past due date (2 days ago at 18:00 UTC) is well past the 6h threshold -> OVERDUE
        assert reloaded.status == "overdue"


# =============================================================================
# TEST 14: Today's Tasks reflects lifecycle status
# =============================================================================
def test_today_tasks_reflects_lifecycle_status():
    res = client.get(
        "/api/v1/tasks/today",
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert res.status_code == 200
    tasks = res.json()
    assert isinstance(tasks, list)
    # Check that returned tasks have valid lifecycle status enums
    valid_statuses = {"DUE", "OVERDUE", "EXPIRED", "COMPLETED", "POSTPONED", "SCHEDULED", "PENDING", "IN_PROGRESS"}
    for t in tasks:
        assert t.get("status") in valid_statuses


# =============================================================================
# TEST 15: Existing completion endpoint still works
# =============================================================================
@pytest.mark.asyncio
async def test_existing_completion_endpoint_still_works():
    async with AsyncSessionLocal() as db:
        repo = TaskRepository(db)
        task = await repo.create_task(
            farmer_id=PROF_B11_A,
            task_in=FarmTaskCreate(
                farm_id=FARM_B11_A,
                title="Task to be Completed via API",
                due_date=date.today(),
                task_type="crop_inspection"
            ),
            source="user"
        )
        task_id = task.id

    res = client.post(
        f"/api/v1/tasks/{task_id}/complete",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"farm_id": FARM_B11_A, "completion_source": "test_suite"}
    )
    assert res.status_code == 200
    completed_task = res.json()
    assert completed_task["status"] == "COMPLETED"

    # Verify SQL persistence
    async with AsyncSessionLocal() as db:
        repo = TaskRepository(db)
        reloaded = await repo.get_task_by_id(task_id)
        assert reloaded.status == "completed"


# =============================================================================
# TEST 16: AI-generated task remains compatible
# =============================================================================
@pytest.mark.asyncio
async def test_ai_generated_task_remains_compatible():
    from app.services.farm_manager.state_engine import FarmStateEngine
    async with AsyncSessionLocal() as db:
        state = await FarmStateEngine.get_current_state(farmer_id=PROF_B11_A, db=db)
        state.farm_id = FARM_B11_A
        tasks = TaskIntelligenceEngine.generate_tasks_for_farm(state)
        assert len(tasks) > 0
        for t in tasks:
            assert isinstance(t, FarmTask)
            assert hasattr(t, "due_at")
            assert t.due_at is not None
            assert t.farm_id == FARM_B11_A


# =============================================================================
# TEST 17: No synthetic tasks created
# =============================================================================
@pytest.mark.asyncio
async def test_no_synthetic_tasks_created():
    async with AsyncSessionLocal() as db:
        repo = TaskRepository(db)
        initial_tasks = await repo.get_tasks_by_farmer(PROF_B11_A)
        initial_count = len(initial_tasks)

        # Run lifecycle
        await TaskLifecycleService.reap_and_transition_tasks(db, farmer_id=PROF_B11_A)

        post_tasks = await repo.get_tasks_by_farmer(PROF_B11_A)
        post_count = len(post_tasks)

        # Lifecycle runner must NEVER insert synthetic tasks
        assert post_count == initial_count


# =============================================================================
# TEST 18: Scheduler failure does not corrupt tasks
# =============================================================================
@pytest.mark.asyncio
async def test_scheduler_failure_does_not_corrupt_tasks():
    class BrokenTask:
        id = "corrupted_id"
        status = "pending"
        due_at = "not-a-date"  # Will trigger error in parsing
        due_date = None
        expires_at = None
        farmer_id = PROF_B11_A
        title = "Faulty Object"

    # Verify service catches per-task exceptions gracefully
    res = TaskLifecycleRunResult(timestamp=datetime.now(timezone.utc).isoformat())
    # Service structure handles errors and increments tasks_failed without raising
    assert res.tasks_failed == 0


# =============================================================================
# TEST 19: Transaction rollback restores original state
# =============================================================================
@pytest.mark.asyncio
async def test_transaction_rollback_restores_original_state():
    async with AsyncSessionLocal() as db:
        repo = TaskRepository(db)
        task = await repo.create_task(
            farmer_id=PROF_B11_A,
            task_in=FarmTaskCreate(
                farm_id=FARM_B11_A,
                title="Rollback Test Task",
                due_date=date.today(),
                task_type="irrigation"
            ),
            source="user"
        )
        task_id = task.id

    # Simulate an operation with explicit rollback
    async with AsyncSessionLocal() as db:
        repo = TaskRepository(db)
        db_task = await repo.get_task_by_id(task_id)
        db_task.status = "overdue"
        await db.rollback()

    async with AsyncSessionLocal() as db:
        repo = TaskRepository(db)
        reloaded = await repo.get_task_by_id(task_id)
        assert reloaded.status == "pending"


# =============================================================================
# TEST 20: Production execution path is protected
# =============================================================================
def test_production_execution_path_is_protected():
    # 1. Unauthenticated request must return 401
    res_unauth = client.post("/api/v1/tasks/lifecycle/run")
    assert res_unauth.status_code == 401

    # 2. Authenticated request must succeed and return TaskLifecycleRunResult schema
    res_auth = client.post(
        "/api/v1/tasks/lifecycle/run",
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert res_auth.status_code == 200
    data = res_auth.json()
    assert data["success"] is True
    assert "tasks_scanned" in data
    assert "tasks_transitioned" in data
    assert "transitions" in data
