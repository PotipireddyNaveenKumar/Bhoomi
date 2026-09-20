import os
import pytest
import uuid
from decimal import Decimal
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.future import select
from sqlalchemy import delete

from app.main import app
from app.core.security import create_access_token, get_password_hash
from app.db.session import AsyncSessionLocal, engine
from app.models.user import User
from app.models.farmer import FarmerProfile
from app.models.farm import Farm
from app.models.crop import FarmCrop
from app.models.recommendation_trace import RecommendationTrace
from app.repositories.recommendation_repo import RecommendationRepository
from app.services.farm_manager.recommendation_trace import (
    RecommendationTraceStore,
    RecommendationRecord,
    FeedbackStatus
)
from app.services.farm_manager.state_engine import FarmState
from app.services.farm_manager.decision_engine import FarmDecisionEngine
from app.services.memory.farm_memory_v2 import FarmMemoryV2

client = TestClient(app)

# Test IDs
USER_A_ID = "user_b10_alice"
PROF_A_ID = "prof_b10_alice"
FARM_A_ID = "farm_b10_alice"

USER_B_ID = "user_b10_bob"
PROF_B_ID = "prof_b10_bob"
FARM_B_ID = "farm_b10_bob"

USER_C_ID = "user_b10_charlie"
PROF_C_ID = "prof_b10_charlie"
FARM_C_ID = "farm_b10_charlie"

token_a = ""
token_b = ""
token_c = ""


@pytest.fixture(scope="module", autouse=True)
def setup_batch10_environment():
    """
    Sets up isolated test users, profiles, and farms for Batch 10 persistent trace verification.
    """
    global token_a, token_b, token_c

    async def _setup():
        async with AsyncSessionLocal() as db:
            # Clean up old test data
            await db.execute(delete(RecommendationTrace).where(RecommendationTrace.farmer_id.in_([PROF_A_ID, PROF_B_ID, PROF_C_ID])))
            await db.execute(delete(FarmCrop).where(FarmCrop.farm_id.in_([FARM_A_ID, FARM_B_ID, FARM_C_ID])))
            await db.execute(delete(Farm).where(Farm.id.in_([FARM_A_ID, FARM_B_ID, FARM_C_ID])))
            await db.execute(delete(FarmerProfile).where(FarmerProfile.id.in_([PROF_A_ID, PROF_B_ID, PROF_C_ID])))
            await db.execute(delete(User).where(User.id.in_([USER_A_ID, USER_B_ID, USER_C_ID])))
            await db.commit()

            # 1. Tenant Alice
            user_a = User(
                id=USER_A_ID,
                phone_number="+919999900001",
                phone_number_verified=True,
                hashed_password=get_password_hash("pass123"),
                is_active=True
            )
            db.add(user_a)
            await db.flush()

            prof_a = FarmerProfile(
                id=PROF_A_ID,
                user_id=user_a.id,
                name="Alice Test",
                preferred_language="te",
                state="Andhra Pradesh",
                district="Guntur",
                village="Tenali"
            )
            db.add(prof_a)
            await db.flush()

            farm_a = Farm(
                id=FARM_A_ID,
                farmer_id=prof_a.id,
                farm_name="Alice Organic Farm",
                total_area_acres=Decimal("4.0"),
                soil_type="black",
                irrigation_source="borewell"
            )
            db.add(farm_a)
            await db.flush()

            # 2. Tenant Bob
            user_b = User(
                id=USER_B_ID,
                phone_number="+919999900002",
                phone_number_verified=True,
                hashed_password=get_password_hash("pass123"),
                is_active=True
            )
            db.add(user_b)
            await db.flush()

            prof_b = FarmerProfile(
                id=PROF_B_ID,
                user_id=user_b.id,
                name="Bob Test",
                preferred_language="en",
                state="Telangana",
                district="Warangal",
                village="Hanamkonda"
            )
            db.add(prof_b)
            await db.flush()

            farm_b = Farm(
                id=FARM_B_ID,
                farmer_id=prof_b.id,
                farm_name="Bob Cotton Farm",
                total_area_acres=Decimal("2.5"),
                soil_type="red",
                irrigation_source="canal"
            )
            db.add(farm_b)
            await db.flush()

            # 3. Tenant Charlie (Clean slate, zero traces for honest empty state test)
            user_c = User(
                id=USER_C_ID,
                phone_number="+919999900003",
                phone_number_verified=True,
                hashed_password=get_password_hash("pass123"),
                is_active=True
            )
            db.add(user_c)
            await db.flush()

            prof_c = FarmerProfile(
                id=PROF_C_ID,
                user_id=user_c.id,
                name="Charlie Test",
                preferred_language="hi",
                state="Maharashtra",
                district="Nagpur",
                village="Katol"
            )
            db.add(prof_c)
            await db.flush()

            farm_c = Farm(
                id=FARM_C_ID,
                farmer_id=prof_c.id,
                farm_name="Charlie Orange Farm",
                total_area_acres=Decimal("3.0"),
                soil_type="black",
                irrigation_source="drip"
            )
            db.add(farm_c)
            await db.commit()

    import asyncio
    asyncio.run(_setup())

    token_a = create_access_token(USER_A_ID)
    token_b = create_access_token(USER_B_ID)
    token_c = create_access_token(USER_C_ID)
    yield


class TestRecommendationTraceStoreBatch10:
    """
    Exhaustive validation suite for Batch 10 persistent recommendation trace store.
    """

    @pytest.mark.asyncio
    async def test_01_create_recommendation_trace(self):
        """1. Persists a recommendation trace to SQL atomically."""
        async with AsyncSessionLocal() as db:
            repo = RecommendationRepository(db)
            trace = await repo.create_trace(
                decision_id="dec_test_01",
                farmer_id=PROF_A_ID,
                farm_id=FARM_A_ID,
                recommendation_id="rec_test_01",
                intent="IRRIGATION",
                decision_type="IRRIGATION",
                recommendation_text="Apply 25mm drip irrigation before 10 AM.",
                confidence=0.92,
                weather_source="openmeteo",
                market_source="mock",
                input_context={"soil_moisture": "22%", "temp": 32.5},
                tools_used=["IrrigationDecisionEngine"],
                assumptions=["No rainfall predicted next 48h"]
            )
            assert trace.id is not None
            assert trace.decision_id == "dec_test_01"
            assert trace.farmer_id == PROF_A_ID
            assert trace.farm_id == FARM_A_ID
            assert trace.confidence == 0.92

    @pytest.mark.asyncio
    async def test_02_retrieve_by_decision_id(self):
        """2. Fetches trace by decision_id or recommendation_id."""
        async with AsyncSessionLocal() as db:
            repo = RecommendationRepository(db)
            by_dec = await repo.get_by_decision_id("dec_test_01")
            assert by_dec is not None
            assert by_dec.decision_id == "dec_test_01"
            assert by_dec.recommendation_text == "Apply 25mm drip irrigation before 10 AM."

            by_rec = await repo.get_by_decision_id("rec_test_01")
            assert by_rec is not None
            assert by_rec.id == by_dec.id

    @pytest.mark.asyncio
    async def test_03_farmer_history(self):
        """3. Queries farmer history ordered newest first."""
        # Insert a second trace for Alice
        async with AsyncSessionLocal() as db:
            repo = RecommendationRepository(db)
            await repo.create_trace(
                decision_id="dec_test_02",
                farmer_id=PROF_A_ID,
                farm_id=FARM_A_ID,
                recommendation_text="Spray Neem Oil 10000 ppm for pest protection.",
                intent="SPRAYING",
                decision_type="SPRAYING",
                confidence=0.88
            )

            traces = await repo.list_for_farmer(PROF_A_ID)
            assert len(traces) >= 2
            # Newest first
            assert traces[0].decision_id == "dec_test_02"
            assert traces[1].decision_id == "dec_test_01"

    @pytest.mark.asyncio
    async def test_04_farm_history(self):
        """4. Queries history scoped to a specific farm."""
        async with AsyncSessionLocal() as db:
            repo = RecommendationRepository(db)
            farm_traces = await repo.list_for_farm(FARM_A_ID)
            assert len(farm_traces) >= 2
            for t in farm_traces:
                assert t.farm_id == FARM_A_ID

    @pytest.mark.asyncio
    async def test_05_pagination_limit(self):
        """5. Verifies pagination limit and offset."""
        async with AsyncSessionLocal() as db:
            repo = RecommendationRepository(db)
            p1 = await repo.list_for_farmer(PROF_A_ID, limit=1, offset=0)
            assert len(p1) == 1
            assert p1[0].decision_id == "dec_test_02"

            p2 = await repo.list_for_farmer(PROF_A_ID, limit=1, offset=1)
            assert len(p2) == 1
            assert p2[0].decision_id == "dec_test_01"

    @pytest.mark.asyncio
    async def test_06_persistence_across_fresh_store_instance(self):
        """6. Fresh store and repository instances can read previously stored traces."""
        # Create brand new session and repository
        async with AsyncSessionLocal() as fresh_db:
            fresh_repo = RecommendationRepository(fresh_db)
            trace = await fresh_repo.get_by_decision_id("dec_test_01")
            assert trace is not None
            assert trace.decision_id == "dec_test_01"
            assert trace.farmer_id == PROF_A_ID

    @pytest.mark.asyncio
    async def test_07_persistence_across_session_boundaries(self):
        """
        7. Key proof:
        WRITE -> DISPOSE SERVICE/SESSION -> NEW SERVICE/SESSION -> READ
        """
        decision_id = f"dec_session_{uuid.uuid4().hex[:8]}"

        # Step 1: Write in Session 1
        async with AsyncSessionLocal() as session1:
            repo1 = RecommendationRepository(session1)
            await repo1.create_trace(
                decision_id=decision_id,
                farmer_id=PROF_A_ID,
                farm_id=FARM_A_ID,
                recommendation_text="Durable trace across session disposal test.",
                confidence=0.99
            )
            # session1 closes here

        # Step 2: Fresh Session 2 completely independent
        async with AsyncSessionLocal() as session2:
            repo2 = RecommendationRepository(session2)
            recovered = await repo2.get_by_decision_id(decision_id)
            assert recovered is not None
            assert recovered.decision_id == decision_id
            assert recovered.recommendation_text == "Durable trace across session disposal test."
            assert recovered.confidence == 0.99

    @pytest.mark.asyncio
    async def test_08_duplicate_decision_id_behavior(self):
        """8. Attempting duplicate decision_id is handled idempotently without error."""
        async with AsyncSessionLocal() as db:
            repo = RecommendationRepository(db)
            first = await repo.create_trace(
                decision_id="dec_duplicate_test",
                farmer_id=PROF_A_ID,
                recommendation_text="First version",
            )
            second = await repo.create_trace(
                decision_id="dec_duplicate_test",
                farmer_id=PROF_A_ID,
                recommendation_text="Attempted duplicate",
            )
            assert first.id == second.id
            assert second.recommendation_text == "First version"

    def test_09_authenticated_access_history_and_detail(self):
        """9. Authenticated farmer can access history and detail endpoints."""
        headers = {"Authorization": f"Bearer {token_a}"}

        # 1. History
        res_hist = client.get("/api/v1/decisions/history", headers=headers)
        assert res_hist.status_code == 200
        data = res_hist.json()
        assert data["success"] is True
        assert len(data["decisions"]) >= 2
        assert data["decisions"][0]["farmer_id"] == PROF_A_ID

        # 2. Detail
        res_det = client.get("/api/v1/decisions/dec_test_01", headers=headers)
        assert res_det.status_code == 200
        trace = res_det.json()
        assert trace["decision_id"] == "dec_test_01"
        assert trace["farmer_id"] == PROF_A_ID

    def test_10_unauthenticated_access_rejected_401(self):
        """10. Unauthenticated requests to /history and /{decision_id} return 401."""
        res_hist = client.get("/api/v1/decisions/history")
        assert res_hist.status_code == 401

        res_det = client.get("/api/v1/decisions/dec_test_01")
        assert res_det.status_code == 401

    def test_11_cross_tenant_access_rejected_403(self):
        """11. Farmer B attempting to access Farmer A's decision trace receives 403 Forbidden."""
        headers_b = {"Authorization": f"Bearer {token_b}"}
        res = client.get("/api/v1/decisions/dec_test_01", headers=headers_b)
        assert res.status_code == 403
        assert "Access forbidden" in res.json()["detail"]

    def test_12_nonexistent_decision_returns_404(self):
        """12. Looking up nonexistent decision returns 404."""
        headers = {"Authorization": f"Bearer {token_a}"}
        res = client.get("/api/v1/decisions/nonexistent_dec_9999", headers=headers)
        assert res.status_code == 404

    def test_13_farm_ownership_enforcement(self):
        """13. Querying history with foreign farm_id returns 403 Forbidden."""
        headers_a = {"Authorization": f"Bearer {token_a}"}
        # Alice tries to query Bob's farm history
        res = client.get(f"/api/v1/decisions/history?farm_id={FARM_B_ID}", headers=headers_a)
        assert res.status_code == 403
        assert "Specified farm does not belong" in res.json()["detail"]

    @pytest.mark.asyncio
    async def test_14_structured_evidence_and_metadata_persistence(self):
        """14. Structured JSON data, calculations, XAI info, and metadata persist intact."""
        async with AsyncSessionLocal() as db:
            repo = RecommendationRepository(db)
            t = await repo.create_trace(
                decision_id="dec_structured_01",
                farmer_id=PROF_A_ID,
                recommendation_text="Apply potash based on SHAP feature importance.",
                calculations={"k_deficit_kg": 18.5, "target_yield_q": 25.0},
                evidence={"rag_citation": "ICAR Chilli Advisory 2024", "soil_test_date": "2026-08-10"},
                xai_info={"shap_top_feature": "soil_k", "feature_importance": {"soil_k": 0.42, "rainfall": -0.15}},
                metadata_json={"evaluator": "bhoomi_v2_core", "batch": 10}
            )

        async with AsyncSessionLocal() as db2:
            repo2 = RecommendationRepository(db2)
            fetched = await repo2.get_by_decision_id("dec_structured_01")
            assert fetched.calculations["k_deficit_kg"] == 18.5
            assert fetched.evidence["rag_citation"] == "ICAR Chilli Advisory 2024"
            assert fetched.xai_info["shap_top_feature"] == "soil_k"
            assert fetched.metadata_json["batch"] == 10

    @pytest.mark.asyncio
    async def test_15_locale_persistence(self):
        """15. Locale and language code persist reliably."""
        async with AsyncSessionLocal() as db:
            repo = RecommendationRepository(db)
            await repo.create_trace(
                decision_id="dec_locale_te_01",
                farmer_id=PROF_A_ID,
                recommendation_text="నీటిపారుదల షెడ్యూల్: రేపు ఉదయం 25 మి.మీ.",
                locale="te"
            )
            fetched = await repo.get_by_decision_id("dec_locale_te_01")
            assert fetched.locale == "te"
            assert "నీటిపారుదల" in fetched.recommendation_text

    @pytest.mark.asyncio
    async def test_16_model_provider_version_persistence(self):
        """16. Model versions and provider identifiers persist."""
        async with AsyncSessionLocal() as db:
            repo = RecommendationRepository(db)
            await repo.create_trace(
                decision_id="dec_prov_01",
                farmer_id=PROF_A_ID,
                recommendation_text="Pest risk advisory",
                model_versions={"vision": "yolov8-crop-v2", "rag": "bhoomi-embeddings-v1"},
                weather_source="openmeteo",
                market_source="data_gov"
            )
            fetched = await repo.get_by_decision_id("dec_prov_01")
            assert fetched.model_versions["vision"] == "yolov8-crop-v2"
            assert fetched.weather_source == "openmeteo"
            assert fetched.market_source == "data_gov"

    @pytest.mark.asyncio
    async def test_17_rollback_on_failed_transaction(self):
        """17. Verifies transaction rollback preserves atomicity on error."""
        async with AsyncSessionLocal() as db:
            try:
                # Add valid object
                t1 = RecommendationTrace(
                    decision_id="dec_rollback_valid",
                    recommendation_id="rec_rollback_valid",
                    farmer_id=PROF_A_ID,
                    recommendation_text="Will be rolled back"
                )
                db.add(t1)

                # Intentional error: None in non-nullable field
                t2 = RecommendationTrace(
                    decision_id=None,  # Not null violation
                    recommendation_id="rec_invalid",
                    farmer_id=PROF_A_ID,
                    recommendation_text="Invalid"
                )
                db.add(t2)
                await db.commit()
            except Exception:
                await db.rollback()

        # Verify t1 was NOT persisted
        async with AsyncSessionLocal() as db2:
            repo = RecommendationRepository(db2)
            check = await repo.get_by_decision_id("dec_rollback_valid")
            assert check is None

    def test_18_existing_recommendation_generation_persists_trace(self):
        """18. FarmDecisionEngine.generate_plan executes and writes durable traces to SQL."""
        from app.services.farm_manager.state_engine import DataFreshness
        state = FarmState(
            farmer_id=PROF_A_ID,
            farmer_name="Alice Test",
            phone="+919999900001",
            preferred_language="te",
            location="Guntur",
            district="Guntur",
            village="Tenali",
            state="Andhra Pradesh",
            total_acres=4.0,
            soil_type="black",
            irrigation_source="borewell",
            active_crop="Chilli",
            crop_stage="flowering",
            weather_summary={
                "temperature": 31.0,
                "humidity": 60,
                "rain_probability": 10.0,
                "rainfall_mm": 0.0,
                "condition": "Sunny"
            },
            soil_moisture_percentage=25.0,
            data_freshness={
                "weather": DataFreshness(source="IMD", retrieved_at="2026-09-20T10:00:00Z", freshness_status="CURRENT", is_live=True),
                "market": DataFreshness(source="AGMARKNET", retrieved_at="2026-09-20T10:00:00Z", freshness_status="CURRENT", is_live=True),
            },
            last_updated="2026-09-20T10:00:00Z"
        )
        plan = FarmDecisionEngine.generate_plan(state)
        assert plan is not None
        assert plan.weather_action is not None

        # Verify trace is retrievable via RecommendationTraceStore
        weather_dec_id = plan.weather_action.decision_id
        trace = RecommendationTraceStore.get_trace(weather_dec_id)
        assert trace is not None
        assert trace.farmer_id == PROF_A_ID

        # Verify trace is directly retrievable via API for Alice
        headers = {"Authorization": f"Bearer {token_a}"}
        res = client.get(f"/api/v1/decisions/{weather_dec_id}", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["decision_id"] == weather_dec_id
        assert data["farmer_id"] == PROF_A_ID

    def test_19_farm_memory_v2_integration_remains_intact(self):
        """19. Feedback updates trace in SQL and preserves FarmMemoryV2 integration."""
        headers = {"Authorization": f"Bearer {token_a}"}
        res_fb = client.post("/api/v1/manager/feedback", headers=headers, json={
            "recommendation_id": "dec_test_01",
            "action_taken": "ACCEPTED",
            "feedback_rating": "USEFUL",
            "notes": "Applied exactly as advised, crop moisture optimal."
        })
        assert res_fb.status_code == 200

        # Verify updated in SQL
        updated_trace = RecommendationTraceStore.get_trace("dec_test_01")
        assert updated_trace is not None
        assert updated_trace.farmer_action == "ACCEPTED"
        assert updated_trace.feedback_rating == "USEFUL"
        assert "moisture optimal" in updated_trace.feedback_notes

    def test_20_evaluate_unauthenticated_returns_401(self):
        """20. Unauthenticated requests to /api/v1/decisions/evaluate return 401."""
        res = client.post("/api/v1/decisions/evaluate", json={"intent": "IRRIGATION"})
        assert res.status_code == 401

    def test_21_evaluate_uses_jwt_farmer_identity_and_prevents_impersonation(self):
        """21. POST /api/v1/decisions/evaluate enforces JWT identity even if body contains spoofed farmer_id."""
        headers = {"Authorization": f"Bearer {token_a}"}
        payload = {
            "farmer_id": PROF_B_ID,  # Alice attempts to evaluate on behalf of Bob
            "intent": "IRRIGATION"
        }
        res = client.post("/api/v1/decisions/evaluate", headers=headers, json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        # Decisions generated must be owned by Alice (PROF_A_ID)
        assert data["plan"]["farmer_id"] == PROF_A_ID

    def test_22_evaluate_foreign_farm_rejected_403(self):
        """22. Evaluating with farm_id not belonging to authenticated farmer returns 403 Forbidden."""
        headers = {"Authorization": f"Bearer {token_a}"}
        payload = {
            "farm_id": FARM_B_ID,  # Alice tries to evaluate Bob's farm
            "intent": "IRRIGATION"
        }
        res = client.post("/api/v1/decisions/evaluate", headers=headers, json=payload)
        assert res.status_code == 403
        assert "Specified farm does not belong" in res.json()["detail"]

    def test_23_history_empty_state_no_synthetic_data(self):
        """23. Farmer with no history returns honest empty list (no synthetic/mocked traces)."""
        headers = {"Authorization": f"Bearer {token_c}"}
        res = client.get("/api/v1/decisions/history", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["total"] == 0
        assert data["decisions"] == []

    def test_24_history_filtering_by_decision_type(self):
        """24. History can be filtered by decision_type."""
        headers = {"Authorization": f"Bearer {token_a}"}
        res = client.get("/api/v1/decisions/history?decision_type=IRRIGATION", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert len(data["decisions"]) >= 1
        for dec in data["decisions"]:
            assert dec["decision_type"] == "IRRIGATION"

        # Filtering by nonexistent type returns empty list
        res_none = client.get("/api/v1/decisions/history?decision_type=NONEXISTENT_TYPE", headers=headers)
        assert res_none.status_code == 200
        assert len(res_none.json()["decisions"]) == 0

    def test_25_history_api_pagination(self):
        """25. History API respects limit and offset."""
        headers = {"Authorization": f"Bearer {token_a}"}
        res_p1 = client.get("/api/v1/decisions/history?limit=1&offset=0", headers=headers)
        res_p2 = client.get("/api/v1/decisions/history?limit=1&offset=1", headers=headers)
        assert res_p1.status_code == 200
        assert res_p2.status_code == 200
        d1 = res_p1.json()["decisions"]
        d2 = res_p2.json()["decisions"]
        assert len(d1) == 1
        assert len(d2) == 1
        assert d1[0]["decision_id"] != d2[0]["decision_id"]

    def test_26_decision_detail_complete_contract(self):
        """26. Decision detail returns all required contract fields with honest nulls."""
        headers = {"Authorization": f"Bearer {token_a}"}
        res = client.get("/api/v1/decisions/dec_structured_01", headers=headers)
        assert res.status_code == 200
        d = res.json()
        # Verify required contract keys are present
        required_keys = [
            "decision_id", "decision_type", "created_at", "farm_id", "input_context",
            "recommendation_text", "confidence", "rationale", "evidence", "rag_sources",
            "tools_used", "model_versions", "xai_info", "data_freshness",
            "calculations", "safety_checks", "assumptions", "farmer_action",
            "feedback_rating", "outcome", "locale", "metadata_json"
        ]
        for key in required_keys:
            assert key in d, f"Missing key {key} in decision detail response"
        # Verify honest null for unprovided outcome
        assert d["outcome"] is None
        # Verify structured evidence and calculations
        assert d["calculations"]["k_deficit_kg"] == 18.5
        assert d["xai_info"]["shap_top_feature"] == "soil_k"

    @pytest.mark.asyncio
    async def test_27_farm_memory_v2_receives_decision_and_enriches_farm_state(self):
        """27. Decision evaluation logs compact DECISION event in FarmMemoryV2, available in subsequent FarmState."""
        from app.services.memory.farm_memory_v2 import FarmMemoryV2
        from app.services.farm_manager.state_engine import FarmStateEngine

        # Check FarmMemoryV2 has DECISION entries for Alice
        dec_memories = FarmMemoryV2.get_memories_by_category(PROF_A_ID, "DECISION")
        assert len(dec_memories) > 0

        # Query FarmState for Alice and verify recent_events references past decision
        async with AsyncSessionLocal() as db:
            state = await FarmStateEngine.get_current_state(farmer_id=PROF_A_ID, db=db)
            assert state.recent_events is not None
            has_decision_ref = any("Previous" in ev for ev in state.recent_events)
            assert has_decision_ref, f"recent_events does not contain past decision reference: {state.recent_events}"

    def test_28_reviewer_ui_elements_in_html(self):
        """28. Reviewer Web UI contains Decision History section and Detail Modal in index.html."""
        index_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "web", "index.html")
        assert os.path.exists(index_path)
        with open(index_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert 'id="decisionHistorySection"' in content
        assert 'id="decisionHistoryList"' in content
        assert 'id="decisionDetailModal"' in content
        assert 'id="decisionDetailBody"' in content
        assert 'onclick="closeDecisionDetailModal()"' in content

    def test_29_reviewer_ui_functions_and_localization_in_js(self):
        """29. Reviewer Web UI implements decision functions and localized strings for en, te, hi in app.js."""
        app_js_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "web", "static", "app.js")
        assert os.path.exists(app_js_path)
        with open(app_js_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check function definitions
        assert "loadDecisionHistory" in content
        assert "openDecisionDetail" in content
        assert "closeDecisionDetailModal" in content
        assert "submitTraceFeedback" in content

        # Check localization strings exist for en, te, hi
        for lang in ["en", "te", "hi"]:
            assert f"{lang}: {{" in content or f'"{lang}":' in content or f"'{lang}':" in content
        assert "whyRationale" in content
        assert "evidenceSensors" in content
        assert "actionFeedback" in content

    @pytest.mark.asyncio
    async def test_30_feedback_persistence_across_fresh_session(self):
        """30. Reviewer feedback updates PostgreSQL trace and persists across session disposal."""
        headers = {"Authorization": f"Bearer {token_a}"}
        # Update feedback via API
        res = client.post("/api/v1/manager/feedback", headers=headers, json={
            "recommendation_id": "dec_structured_01",
            "action_taken": "ACCEPTED",
            "feedback_rating": "USEFUL",
            "notes": "Verified in fresh session test - excellent advice."
        })
        assert res.status_code == 200

        # Read back in a completely fresh session
        async with AsyncSessionLocal() as fresh_db:
            repo = RecommendationRepository(fresh_db)
            trace = await repo.get_by_decision_id("dec_structured_01")
            assert trace is not None
            assert trace.farmer_action == "ACCEPTED"
            assert trace.feedback_rating == "USEFUL"
            assert "fresh session test" in trace.feedback_notes

        # Read back via API with fresh request
        res2 = client.get("/api/v1/decisions/dec_structured_01", headers=headers)
        assert res2.status_code == 200
        d = res2.json()
        assert d["farmer_action"] == "ACCEPTED"
        assert d["feedback_rating"] == "USEFUL"
        assert "fresh session test" in d["feedback_notes"]

    def test_31_migration_chain_integrity(self):
        """31. Verifies Alembic migration chain has exactly one head and valid revision."""
        import subprocess, sys
        backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        res = subprocess.run(
            [sys.executable, "-m", "alembic", "heads"],
            cwd=backend_dir,
            capture_output=True,
            text=True
        )
        assert res.returncode == 0
        heads_output = res.stdout.strip()
        assert ("001_rec_traces" in heads_output or "002_task_lifecycle" in heads_output)
        # Verify exactly one single head line
        assert len(heads_output.splitlines()) == 1

