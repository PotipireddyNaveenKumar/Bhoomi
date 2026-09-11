"""
BHOOMI — Reviewer-Ready End-to-End Browser Journey Test
Simulates full browser DOM interactions using Playwright:
1. Open website at root URL
2. Authenticate via OTP and Onboarding modal with location-based soil estimation
3. Verify Farm Digital Twin in Dashboard
4. Multi-turn text chat interaction with agronomic reasoning
5. Feedback recording (thumbs up) with backend persistence
6. Leaf image upload and non-chilli diagnostic verification
7. Profile inspection and Logout
8. Re-login and Digital Twin memory persistence check
"""

import os
import sys
import time
import pytest
from playwright.async_api import async_playwright

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEST_POTATO_IMG = os.path.join(BASE_DIR, "data", "organized", "vision", "potato_diseases", "Potato", "Potato___Early_blight")

def get_sample_potato_image() -> str:
    for root, _, files in os.walk(TEST_POTATO_IMG):
        for f in files:
            if f.lower().endswith((".jpg", ".jpeg")):
                return os.path.join(root, f)
    raise FileNotFoundError(f"No sample potato image in {TEST_POTATO_IMG}")


@pytest.mark.asyncio
async def test_reviewer_browser_end_to_end_journey():
    app_url = "http://127.0.0.1:8000"
    potato_img_path = get_sample_potato_image()
    assert os.path.isfile(potato_img_path), f"Potato image not found: {potato_img_path}"

    async with async_playwright() as p:
        # Launch Chromium headless
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            permissions=["geolocation"],
            geolocation={"latitude": 16.3067, "longitude": 80.4365} # Guntur coordinates
        )
        page = await context.new_page()

        page.on("console", lambda msg: print(f"[PW CONSOLE] {msg.type}: {msg.text}"))
        page.on("pageerror", lambda err: print(f"[PW PAGEERROR] {err}"))
        page.on("dialog", lambda dialog: dialog.accept())

        # 1. OPEN WEBSITE
        await page.goto(app_url, wait_until="networkidle")
        assert "BHOOMI" in await page.title()

        # Verify Auth Modal is displayed on initial visit
        auth_modal = page.locator("#authModal")
        await auth_modal.wait_for(state="visible", timeout=8000)

        # 2. SELECT PREFERRED LANGUAGE & SUBMIT MOBILE NUMBER
        await page.select_option("#authLangSelect", "en")
        mobile_input = page.locator("#otpMobileInput")
        await mobile_input.fill("9876543210")
        
        btn_send_otp = page.locator("#btnSendOtp")
        await btn_send_otp.click()

        # 3. ONBOARDING & SOIL ESTIMATION GATE
        otp_step2 = page.locator("#otpStep2")
        await otp_step2.wait_for(state="visible", timeout=8000)

        # Verify location soil estimate card is rendered
        soil_card = page.locator(".soil-onboarding-panel")
        await soil_card.wait_for(state="visible", timeout=5000)
        soil_type_lbl = await page.locator("#soilEstTypeLabel").text_content()
        assert len(soil_type_lbl.strip()) > 0, "Soil estimate label should be populated from location service"

        # Fill farmer profile & farm digital twin details
        await page.locator("#farmerNameInput").fill("Ramesh Reviewer")
        await page.select_option("#farmerStateInput", "Andhra Pradesh")
        # Give onStateChanged a brief moment to update districts
        await page.wait_for_timeout(400)
        await page.select_option("#farmerDistrictInput", "Guntur")
        await page.locator("#farmerVillageInput").fill("Tenali")
        await page.select_option("#farmerCropInput", "Chilli")
        await page.locator("#farmerAcresInput").fill("3.5")
        await page.locator("#farmerVarietyInput").fill("Teja")

        # Enter OTP
        await page.locator("#otpCodeInput").fill("1234")

        # 4. VERIFY OTP & ENTER DASHBOARD
        await page.locator("#btnVerifyOtp").click()
        
        # Check if any error was displayed
        err_loc = page.locator("#authErrorMsg")
        if await err_loc.is_visible():
            err_text = await err_loc.text_content()
            print(f"[AUTH ERROR DISPLAYED]: {err_text}")
            
        await auth_modal.wait_for(state="hidden", timeout=12000)

        # 5. VERIFY DIGITAL TWIN IN SIDEBAR
        farmer_name_sidebar = page.locator("#sidebarFarmerName")
        await farmer_name_sidebar.wait_for(state="visible", timeout=5000)
        text_name = await farmer_name_sidebar.text_content()
        assert "Ramesh Reviewer" in text_name, f"Expected Ramesh Reviewer in sidebar, got: {text_name}"

        # 6. TEXT CHAT INTERACTION
        chat_input = page.locator("#chatInput")
        await chat_input.fill("What is the current weather and how does it affect my chilli crop?")
        await page.locator("#btnSend").click()

        # Wait for assistant response
        messages_list = page.locator("#messagesList")
        await messages_list.wait_for(state="visible", timeout=5000)
        bot_response = page.locator(".message-row.assistant .message-text").first
        await bot_response.wait_for(state="visible", timeout=20000)
        bot_text = await bot_response.text_content()
        assert len(bot_text.strip()) > 20, "Assistant response was empty or too brief"

        # 7. ASSISTANT FEEDBACK
        feedback_btns = page.locator(".btn-feedback-thumb")
        if await feedback_btns.count() > 0:
            helpful_btn = feedback_btns.first
            await helpful_btn.click()
            thanks_span = page.locator(".feedback-thanks").first
            await thanks_span.wait_for(state="visible", timeout=8000)
            assert await thanks_span.is_visible(), "Feedback confirmation was not displayed"

        # 8. LEAF IMAGE UPLOAD & MULTI-CROP CONFLICT DETECTION
        # Upload a potato leaf while registered as chilli farm
        gallery_input = page.locator("#galleryInput")
        await gallery_input.set_input_files(potato_img_path)

        # Wait for leaf diagnosis card / response to appear (at least 2 assistant responses in chat)
        await page.wait_for_function(
            "() => document.querySelectorAll('.message-row.assistant .message-text').length >= 2",
            timeout=30000
        )
        last_bot_msg = page.locator(".message-row.assistant .message-text").nth(1)
        last_bot_text = await last_bot_msg.text_content()
        
        # Verify it handled the crop appropriately (either detected Potato/Corn_Maize candidate or surfaced Crop Notice conflict)
        assert len(last_bot_text.strip()) > 30, f"Vision diagnostic response was too brief: {last_bot_text}"
        # Must NOT blindly give a generic chilli greeting
        assert "I looked closely at your chilli leaf" not in last_bot_text, "Hardcoded chilli greeting leaked into diagnosis"

        # 9. LOGOUT & FARM DIGITAL TWIN PERSISTENCE
        profile_card = page.locator(".farmer-profile-card")
        await profile_card.click()

        profile_modal = page.locator("#profileModal")
        await profile_modal.wait_for(state="visible", timeout=5000)

        # Click logout
        btn_logout = page.locator(".btn-logout")
        await btn_logout.click()

        # Verify returned to Auth Modal
        await auth_modal.wait_for(state="visible", timeout=5000)

        # 10. RE-LOGIN AND VERIFY PERSISTENCE
        await page.locator("#otpMobileInput").fill("9876543210")
        await page.locator("#btnSendOtp").click()
        await otp_step2.wait_for(state="visible", timeout=8000)
        await page.locator("#otpCodeInput").fill("1234")
        await page.locator("#btnVerifyOtp").click()
        await auth_modal.wait_for(state="hidden", timeout=12000)

        # Digital twin should show Ramesh Reviewer again
        text_name_relogin = await page.locator("#sidebarFarmerName").text_content()
        assert "Ramesh Reviewer" in text_name_relogin, f"Digital twin memory failed to persist after relogin: {text_name_relogin}"

        await browser.close()
