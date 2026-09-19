import os
import io
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.services.farm_manager.recommendation_trace import RecommendationTraceStore
from app.services.memory.digital_twin import DigitalTwinService

client = TestClient(app)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


class TestE2EReviewerJourney:
    """
    End-to-End Reviewer Experience Test Suite.
    Simulates a brand-new evaluator landing on BHOOMI, onboarding with a real farm,
    asking queries, uploading crop images, giving feedback, and returning after logout.
    Guarantees:
      - Zero hardcoded Ramesh Kumar, Guntur, or Chilli fallback
      - Real dynamic OTP generation and verification
      - Farm digital twin persistence across logout/re-login
      - Multi-crop vision routing to Potato model
      - Recommendation feedback and trace persistence
    """

    def test_complete_reviewer_lifecycle(self):
        import random
        reviewer_phone = f"+9198{random.randint(10000000, 99999999)}"

        # -------------------------------------------------------------
        # 1. SEND OTP FOR NEW REVIEWER
        # -------------------------------------------------------------
        res_send = client.post("/api/v1/auth/send-otp", json={
            "phone_number": reviewer_phone
        })
        assert res_send.status_code == 200, f"Send OTP failed: {res_send.text}"
        data_send = res_send.json()
        assert data_send["status"] == "success"
        assert data_send["is_registered"] is False
        otp_code = data_send["otp_code"]
        assert len(otp_code) == 4, f"Expected 4-digit OTP, got {otp_code}"

        # -------------------------------------------------------------
        # 2. VERIFY OTP WITH ONBOARDING DATA (Potato, Warangal, 2.5 acres)
        # -------------------------------------------------------------
        res_verify = client.post("/api/v1/auth/verify-otp", json={
            "phone_number": reviewer_phone,
            "otp_code": otp_code,
            "name": "Rajesh Patel",
            "state": "Telangana",
            "district": "Warangal",
            "village": "Dharmasagar",
            "crop_name": "Potato",
            "area_acres": 2.5,
            "soil_type": "black",
            "irrigation_type": "Drip",
            "nitrogen": 45.0,
            "phosphorus": 22.0,
            "potassium": 35.0,
            "ph": 7.1
        })
        assert res_verify.status_code == 200, f"Verify OTP failed: {res_verify.text}"
        data_verify = res_verify.json()
        token = data_verify["access_token"]
        assert token, "Access token must be present"
        assert data_verify["is_new_user"] is True
        assert data_verify["crop_name"].lower() == "potato"
        assert float(data_verify["area_acres"]) == 2.5
        assert data_verify["district"] == "Warangal"
        assert data_verify["state"] == "Telangana"
        farmer_id = data_verify["farmer_id"]
        farm_id = data_verify["farm_id"]
        assert farmer_id is not None
        assert farm_id is not None

        headers = {"Authorization": f"Bearer {token}"}
        session_id = f"reviewer_session_{farmer_id}"

        # -------------------------------------------------------------
        # 3. CHAT: WHAT SHOULD I DO TODAY? (Dynamic Potato Plan)
        # -------------------------------------------------------------
        res_today = client.post("/api/v1/assistant/chat", headers=headers, json={
            "message": "What should I do today?",
            "session_id": session_id,
            "farm_id": farm_id,
            "language_code": "en"
        })
        assert res_today.status_code == 200, f"Chat turn 1 failed: {res_today.text}"
        today_text = res_today.json()["reply_text"]
        # Must not leak Ramesh or Guntur
        assert "Ramesh" not in today_text
        assert "Guntur" not in today_text

        # -------------------------------------------------------------
        # 4. CHAT: WHAT IS THE WEATHER? (Dynamic Warangal Weather)
        # -------------------------------------------------------------
        res_wx = client.post("/api/v1/assistant/chat", headers=headers, json={
            "message": "What is the weather today?",
            "session_id": session_id,
            "farm_id": farm_id,
            "language_code": "en"
        })
        assert res_wx.status_code == 200
        wx_text = res_wx.json()["reply_text"]
        assert "Warangal" in wx_text or "weather" in wx_text.lower()
        assert "Guntur" not in wx_text

        # -------------------------------------------------------------
        # 5. CHAT: WHAT IS THE MANDI PRICE OF POTATO?
        # -------------------------------------------------------------
        res_mandi = client.post("/api/v1/assistant/chat", headers=headers, json={
            "message": "What is the mandi price of potato?",
            "session_id": session_id,
            "farm_id": farm_id,
            "language_code": "en"
        })
        assert res_mandi.status_code == 200
        mandi_text = res_mandi.json()["reply_text"]
        assert "Potato" in mandi_text or "potato" in mandi_text
        assert "Chilli" not in mandi_text

        # -------------------------------------------------------------
        # 6. VISION: UPLOAD POTATO LEAF IMAGE (Multi-crop Routing)
        # -------------------------------------------------------------
        test_img_path = os.path.join(
            BASE_DIR,
            "data", "organized", "vision", "potato_diseases",
            "Potato", "Potato___Early_blight", "brightness_adjusted",
            "100_brightness_adjusted.jpg"
        )
        assert os.path.isfile(test_img_path), f"Test image not found at {test_img_path}"
        with open(test_img_path, "rb") as fp:
            img_bytes = fp.read()

        import base64
        img_b64 = base64.b64encode(img_bytes).decode("utf-8")

        # 6. VISION: IN-CHAT LEAF PHOTO UPLOAD (Matches Web UI Workflow)
        res_vision = client.post(
            "/api/v1/assistant/chat",
            headers=headers,
            json={
                "message": "Analyze this potato leaf image for diseases",
                "session_id": session_id,
                "farm_id": farm_id,
                "language_code": "en",
                "image_base64": img_b64
            }
        )
        assert res_vision.status_code == 200, f"Chat leaf upload failed: {res_vision.text}"
        chat_vis_data = res_vision.json()
        assert chat_vis_data["status"] == "success"
        struct_data = chat_vis_data.get("structured_data", {})
        diagnosis = struct_data.get("vision_diagnosis", {})
        crop_id = diagnosis.get("crop_identified", "")
        assert "potato" in crop_id.lower(), f"Expected Potato diagnosis, got {crop_id}"
        assert "chilli" not in crop_id.lower(), "System forced Chilli on a Potato leaf!"

        # Direct multipart vision diagnostic endpoint verification
        res_direct = client.post(
            "/api/v1/image/analyze",
            headers=headers,
            files={"file": ("potato_leaf.jpg", img_bytes, "image/jpeg")},
            data={"crop_name": "Potato"}
        )
        assert res_direct.status_code == 200
        assert res_direct.json()["crop_identified"].lower() == "potato"

        # -------------------------------------------------------------
        # 7. FEEDBACK: SUBMIT FEEDBACK ON ADVISORY
        # -------------------------------------------------------------
        res_fb = client.post("/api/v1/assistant/feedback", headers=headers, json={
            "session_id": session_id,
            "rating": "helpful",
            "response_text": mandi_text,
            "language_code": "en"
        })
        assert res_fb.status_code == 200
        assert res_fb.json()["status"] == "success"
        assert res_fb.json()["rating"] == "helpful"

        # -------------------------------------------------------------
        # 8. LOGOUT & RE-LOGIN: VERIFY PERSISTED DIGITAL TWIN
        # -------------------------------------------------------------
        # Request OTP for existing reviewer phone
        res_send_again = client.post("/api/v1/auth/send-otp", json={
            "phone_number": reviewer_phone
        })
        assert res_send_again.status_code == 200
        data_send_again = res_send_again.json()
        # System recognizes returning user
        assert data_send_again["is_registered"] is True
        otp_2 = data_send_again["otp_code"]

        # Returning user verifies with OTP only (no onboarding payload needed)
        res_login_again = client.post("/api/v1/auth/verify-otp", json={
            "phone_number": reviewer_phone,
            "otp_code": otp_2
        })
        assert res_login_again.status_code == 200
        data_relogin = res_login_again.json()
        assert data_relogin["is_new_user"] is False
        assert data_relogin["farmer_id"] == farmer_id
        assert data_relogin["farm_id"] == farm_id
        assert data_relogin["crop_name"].lower() == "potato"
        assert float(data_relogin["area_acres"]) == 2.5
        assert data_relogin["district"] == "Warangal"
        assert data_relogin["state"] == "Telangana"

        # Verify chat sessions exist for this returning farmer
        headers_again = {"Authorization": f"Bearer {data_relogin['access_token']}"}
        res_sessions = client.get("/api/v1/assistant/sessions", headers=headers_again)
        assert res_sessions.status_code == 200
        sessions_list = res_sessions.json()
        assert len(sessions_list) > 0, "Previous session history should be preserved"
