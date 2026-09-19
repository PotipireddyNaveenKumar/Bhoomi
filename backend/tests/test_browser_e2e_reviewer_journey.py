"""
BHOOMI — Reviewer-Ready End-to-End Browser Journey Test
Simulates full browser DOM interactions using Playwright:
1. Open website at root URL -> Screenshot: 01_landing_page.png
2. New registration & Onboarding with location-based soil estimation -> Screenshot: 02_onboarding_soil_estimation.png
3. Verify Farm Digital Twin in Dashboard -> Screenshot: 03_dashboard_digital_twin.png
4. Weather & Agronomic reasoning chat interaction -> Screenshot: 04_weather_interaction.png
5. Market & Price inquiry -> Screenshot: 05_market_interaction.png
6. Assistant feedback (thumbs up) -> Screenshot: 06_assistant_feedback.png
7. Leaf image upload and multi-crop diagnostic verification -> Screenshot: 07_leaf_diagnosis.png
8. Page refresh & session persistence check -> Screenshot: 08_page_refresh.png
9. Profile inspection and Logout -> Screenshot: 09_logout.png
10. Re-login and Digital Twin memory persistence check -> Screenshot: 10_relogin_persistence.png
"""

import os
import sys
import time
import random
import pytest
from playwright.async_api import async_playwright

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCREENSHOT_DIR = os.path.join(BASE_DIR, "data", "evaluation", "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

TEST_POTATO_IMG = os.path.join(BASE_DIR, "data", "organized", "vision", "potato_diseases", "Potato", "Potato___Early_blight")

def get_sample_potato_image() -> str:
    for root, _, files in os.walk(TEST_POTATO_IMG):
        for f in files:
            if f.lower().endswith((".jpg", ".jpeg")):
                return os.path.join(root, f)
    raise FileNotFoundError(f"No sample potato image in {TEST_POTATO_IMG}")


@pytest.mark.asyncio
async def test_reviewer_browser_end_to_end_journey():
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_running = (sock.connect_ex(("127.0.0.1", 8000)) == 0)
    sock.close()
    if not server_running:
        pytest.fail("Local test server is NOT running on port 8000. Start backend server via uvicorn app.main:app --port 8000")

    app_url = "http://127.0.0.1:8000"
    potato_img_path = get_sample_potato_image()
    assert os.path.isfile(potato_img_path), f"Potato image not found: {potato_img_path}"

    new_reviewer_phone = f"99{random.randint(10000000, 99999999)}"
    reviewer_name = f"Reviewer Farmer {random.randint(100, 999)}"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            permissions=["geolocation"],
            geolocation={"latitude": 16.3067, "longitude": 80.4365}  # Guntur coordinates
        )
        page = await context.new_page()

        page.on("console", lambda msg: print(f"[PW CONSOLE] {msg.type}: {msg.text}"))
        page.on("pageerror", lambda err: print(f"[PW PAGEERROR] {err}"))
        page.on("dialog", lambda dialog: dialog.accept())

        # 1. OPEN WEBSITE
        await page.goto(app_url, wait_until="networkidle")
        assert "BHOOMI" in await page.title()

        auth_modal = page.locator("#authModal")
        await auth_modal.wait_for(state="visible", timeout=8000)
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "01_landing_page.png"))

        # 2. SELECT PREFERRED LANGUAGE & SUBMIT NEW MOBILE NUMBER
        await page.select_option("#authLangSelect", "en")
        mobile_input = page.locator("#otpMobileInput")
        await mobile_input.fill(new_reviewer_phone)

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
        await page.locator("#farmerNameInput").fill(reviewer_name)
        await page.select_option("#farmerStateInput", "Andhra Pradesh")
        await page.wait_for_timeout(400)
        await page.select_option("#farmerDistrictInput", "Guntur")
        await page.locator("#farmerVillageInput").fill("Tenali")
        await page.select_option("#farmerCropInput", "Chilli")
        await page.locator("#farmerAcresInput").fill("3.5")
        await page.locator("#farmerVarietyInput").fill("Teja")

        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "02_onboarding_soil_estimation.png"))

        # Enter OTP (1234 master evaluator code)
        await page.locator("#otpCodeInput").fill("1234")

        # 4. VERIFY OTP & ENTER DASHBOARD
        await page.locator("#btnVerifyOtp").click()
        await auth_modal.wait_for(state="hidden", timeout=12000)

        # 5. VERIFY DIGITAL TWIN IN SIDEBAR
        farmer_name_sidebar = page.locator("#sidebarFarmerName")
        await farmer_name_sidebar.wait_for(state="visible", timeout=5000)
        text_name = await farmer_name_sidebar.text_content()
        assert reviewer_name in text_name, f"Expected {reviewer_name} in sidebar, got: {text_name}"
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "03_dashboard_digital_twin.png"))

        # 6. TEXT CHAT INTERACTION (WEATHER & AGRONOMY)
        chat_input = page.locator("#chatInput")
        await chat_input.fill("What is the current weather and how does it affect my chilli crop?")
        await page.locator("#btnSend").click()

        messages_list = page.locator("#messagesList")
        await messages_list.wait_for(state="visible", timeout=5000)
        bot_response = page.locator(".message-row.assistant .message-text").first
        await bot_response.wait_for(state="visible", timeout=25000)
        bot_text = await bot_response.text_content()
        assert len(bot_text.strip()) > 20, "Assistant response was empty or too brief"
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "04_weather_interaction.png"))

        # 7. MARKET INQUIRY
        await chat_input.fill("What is the current market price of Cotton in Warangal?")
        await page.locator("#btnSend").click()
        await page.wait_for_function(
            "() => document.querySelectorAll('.message-row.assistant .message-text').length >= 2",
            timeout=25000
        )
        market_bot_msg = page.locator(".message-row.assistant .message-text").nth(1)
        market_text = await market_bot_msg.text_content()
        assert len(market_text.strip()) > 15, "Market price response was empty"
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "05_market_interaction.png"))

        # 8. ASSISTANT FEEDBACK
        feedback_btns = page.locator(".btn-feedback-thumb")
        if await feedback_btns.count() > 0:
            helpful_btn = feedback_btns.first
            await helpful_btn.click()
            await page.wait_for_timeout(500)
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "06_assistant_feedback.png"))

        # 9. LEAF IMAGE UPLOAD & DIAGNOSIS
        gallery_input = page.locator("#galleryInput")
        await gallery_input.set_input_files(potato_img_path)

        await page.wait_for_function(
            "() => document.querySelectorAll('.message-row.assistant .message-text').length >= 3",
            timeout=30000
        )
        last_bot_msg = page.locator(".message-row.assistant .message-text").nth(2)
        last_bot_text = await last_bot_msg.text_content()
        assert len(last_bot_text.strip()) > 30, f"Vision diagnostic response was too brief: {last_bot_text}"
        assert "I looked closely at your chilli leaf" not in last_bot_text, "Hardcoded chilli greeting leaked into diagnosis"
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "07_leaf_diagnosis.png"))

        # 10. REFRESH & PERSISTENCE VERIFICATION
        await page.reload(wait_until="networkidle")
        # Sidebar should still show the registered farmer
        await farmer_name_sidebar.wait_for(state="visible", timeout=5000)
        reloaded_name = await farmer_name_sidebar.text_content()
        assert reviewer_name in reloaded_name, f"State lost on refresh: {reloaded_name}"
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "08_page_refresh.png"))

        # 11. PROFILE INSPECTION & LOGOUT
        profile_card = page.locator(".farmer-profile-card")
        await profile_card.click()

        profile_modal = page.locator("#profileModal")
        await profile_modal.wait_for(state="visible", timeout=5000)
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "09_logout.png"))

        btn_logout = page.locator(".btn-logout")
        await btn_logout.click()
        await auth_modal.wait_for(state="visible", timeout=5000)

        # 12. RE-LOGIN AND VERIFY PERSISTENCE
        await page.locator("#otpMobileInput").fill(new_reviewer_phone)
        await page.locator("#btnSendOtp").click()
        await otp_step2.wait_for(state="visible", timeout=8000)
        await page.locator("#otpCodeInput").fill("1234")
        await page.locator("#btnVerifyOtp").click()
        await auth_modal.wait_for(state="hidden", timeout=12000)

        # Digital twin should show Reviewer Farmer again
        text_name_relogin = await page.locator("#sidebarFarmerName").text_content()
        assert reviewer_name in text_name_relogin, f"Digital twin memory failed to persist after relogin: {text_name_relogin}"
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "10_relogin_persistence.png"))

        await browser.close()
        print(f"\nBrowser E2E Reviewer Journey Test PASSED with all 10 screenshots saved to {SCREENSHOT_DIR}")
