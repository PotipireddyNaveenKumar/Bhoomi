import re
import asyncio
import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
from playwright.async_api import async_playwright

TELUGU_CHAR_RANGE = re.compile(r'[\u0C00-\u0C7F]')
PROD_URL = "https://bhoomi-production-0e92.up.railway.app"

async def run_prod_verification():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            permissions=["microphone"],
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()

        print(f"\n--- 1. Navigating to Production BHOOMI ({PROD_URL}) ---")
        await page.goto(f"{PROD_URL}/login", wait_until="networkidle")

        # Perform Reviewer Demo Login to enter dashboard
        print("Logging in via Reviewer Demo Login on Production...")
        await page.click("button:has-text('Reviewer Demo Login')")
        await page.wait_for_selector("#dashboardView", state="visible", timeout=15000)
        print("Successfully authenticated and entered dashboard.")

        # Ensure language is English
        print("\n--- 2. Setting Global Language to English ---")
        await page.select_option("#langSelect", "en")
        await page.wait_for_timeout(500)

        # Open Voice Assistant Modal
        print("\n--- 3. Opening Voice Assistant Modal in English Mode ---")
        await page.click("#txtVoiceCallBtn")
        await page.wait_for_selector("#voiceCallModal", state="visible", timeout=5000)

        # Verify English text
        title = await page.inner_text("#voiceCallAgentTitle")
        badge = await page.inner_text("#voiceStatusBadge")
        farmer_role = await page.inner_text("#voiceFarmerRole")
        farmer_text = await page.inner_text("#voiceFarmerText")
        ai_role = await page.inner_text("#voiceAiRole")
        ai_text = await page.inner_text("#voiceAiText")
        mic_label = await page.inner_text("#voiceCallMicLabel")
        end_call = await page.inner_text("#txtEndCall")

        print(f"Title: {title}")
        print(f"Status Badge: {badge}")
        print(f"Farmer Role: {farmer_role}")
        print(f"Farmer Text: {farmer_text}")
        print(f"AI Role: {ai_role}")
        print(f"AI Text: {ai_text}")
        print(f"Mic Label: {mic_label}")
        print(f"End Call: {end_call}")

        assert "BHOOMI Voice Assistant" in title, f"Title mismatch: {title}"
        assert "Farmer" in farmer_role, f"Farmer role mismatch: {farmer_role}"
        assert "Speak your question" in farmer_text or "Listening" in farmer_text, f"Farmer text mismatch: {farmer_text}"
        assert "BHOOMI (Voice Assistant)" in ai_role, f"AI role mismatch: {ai_role}"
        assert "Hello!" in ai_text, f"AI text mismatch: {ai_text}"
        assert "End Call" in end_call, f"End call mismatch: {end_call}"

        modal_text = await page.inner_text("#voiceCallModal")
        telugu_chars = TELUGU_CHAR_RANGE.findall(modal_text)
        assert len(telugu_chars) == 0, f"Found unexpected Telugu characters in English mode: {set(telugu_chars)}"
        print(">>> SUCCESS: Production Voice Assistant in English has ZERO Telugu characters.")

        await page.screenshot(path="C:/Users/SURESH/.gemini/antigravity-ide/brain/757eb8a2-93ae-4322-9e27-e89b75cfe07c/prod_voice_modal_english.png")

        # --- 4. Switch to Telugu WITHOUT closing modal ---
        print("\n--- 4. Switching Global Language to Telugu While Modal is Open ---")
        await page.select_option("#langSelect", "te")
        await page.wait_for_timeout(500)

        # Verify Telugu text immediately updated live
        te_title = await page.inner_text("#voiceCallAgentTitle")
        te_badge = await page.inner_text("#voiceStatusBadge")
        te_farmer_role = await page.inner_text("#voiceFarmerRole")
        te_farmer_text = await page.inner_text("#voiceFarmerText")
        te_ai_role = await page.inner_text("#voiceAiRole")
        te_ai_text = await page.inner_text("#voiceAiText")
        te_mic_label = await page.inner_text("#voiceCallMicLabel")
        te_end_call = await page.inner_text("#txtEndCall")

        print(f"Telugu Title: {te_title}")
        print(f"Telugu Status Badge: {te_badge}")
        print(f"Telugu Farmer Role: {te_farmer_role}")
        print(f"Telugu Farmer Text: {te_farmer_text}")
        print(f"Telugu AI Role: {te_ai_role}")
        print(f"Telugu AI Text: {te_ai_text}")
        print(f"Telugu Mic Label: {te_mic_label}")
        print(f"Telugu End Call: {te_end_call}")

        assert "భూమి" in te_title, f"Telugu title mismatch: {te_title}"
        assert "రైతు" in te_farmer_role, f"Telugu farmer role mismatch: {te_farmer_role}"
        assert "వింటున్నాను" in te_farmer_text or "సమస్య" in te_farmer_text, f"Telugu farmer text mismatch: {te_farmer_text}"
        assert "వాయిస్ అసిస్టెంట్" in te_ai_role, f"Telugu AI role mismatch: {te_ai_role}"
        assert "నమస్కారం" in te_ai_text, f"Telugu AI text mismatch: {te_ai_text}"
        assert "ముగించు" in te_end_call, f"Telugu end call mismatch: {te_end_call}"
        print(">>> SUCCESS: Production Voice Assistant immediately updated to Telugu while open.")

        await page.screenshot(path="C:/Users/SURESH/.gemini/antigravity-ide/brain/757eb8a2-93ae-4322-9e27-e89b75cfe07c/prod_voice_modal_telugu.png")

        # --- 5. Switch back to English WITHOUT closing modal ---
        print("\n--- 5. Switching Global Language back to English While Modal is Open ---")
        await page.select_option("#langSelect", "en")
        await page.wait_for_timeout(500)

        en2_title = await page.inner_text("#voiceCallAgentTitle")
        en2_farmer_role = await page.inner_text("#voiceFarmerRole")
        en2_ai_text = await page.inner_text("#voiceAiText")
        en2_end_call = await page.inner_text("#txtEndCall")

        print(f"English (Reverted) Title: {en2_title}")
        print(f"English (Reverted) Farmer Role: {en2_farmer_role}")
        print(f"English (Reverted) AI Text: {en2_ai_text}")
        print(f"English (Reverted) End Call: {en2_end_call}")

        assert "BHOOMI Voice Assistant" in en2_title
        assert "Farmer" in en2_farmer_role
        assert "Hello!" in en2_ai_text
        assert "End Call" in end_call

        modal_text2 = await page.inner_text("#voiceCallModal")
        telugu_chars2 = TELUGU_CHAR_RANGE.findall(modal_text2)
        assert len(telugu_chars2) == 0, f"Found unexpected Telugu characters after revert: {set(telugu_chars2)}"
        print(">>> SUCCESS: Production Voice Assistant immediately reverted back to English.")

        # --- 6. Switch to Hindi (Third Language) WITHOUT closing modal ---
        print("\n--- 6. Switching Global Language to Hindi While Modal is Open ---")
        await page.select_option("#langSelect", "hi")
        await page.wait_for_timeout(500)

        hi_title = await page.inner_text("#voiceCallAgentTitle")
        hi_farmer_role = await page.inner_text("#voiceFarmerRole")
        hi_ai_role = await page.inner_text("#voiceAiRole")
        hi_ai_text = await page.inner_text("#voiceAiText")
        hi_end_call = await page.inner_text("#txtEndCall")

        print(f"Hindi Title: {hi_title}")
        print(f"Hindi Farmer Role: {hi_farmer_role}")
        print(f"Hindi AI Role: {hi_ai_role}")
        print(f"Hindi AI Text: {hi_ai_text}")
        print(f"Hindi End Call: {hi_end_call}")

        assert "भूमि" in hi_title
        assert "किसान" in hi_farmer_role
        assert "वॉयस असिस्टेंट" in hi_ai_role
        assert "नमस्ते" in hi_ai_text
        assert "समाप्त करें" in hi_end_call
        print(">>> SUCCESS: Production Voice Assistant immediately updated to Hindi.")

        await page.screenshot(path="C:/Users/SURESH/.gemini/antigravity-ide/brain/757eb8a2-93ae-4322-9e27-e89b75cfe07c/prod_voice_modal_hindi.png")

        # Verify recognizer language mapping in production
        rec_lang = await page.evaluate("() => window.getLocaleForLang ? window.getLocaleForLang('hi') : null")
        print(f"Recognizer locale in Hindi: {rec_lang}")
        assert rec_lang == "hi-IN", f"getLocaleForLang mismatch for Hindi: {rec_lang}"

        # Switch back to English and close modal
        await page.select_option("#langSelect", "en")
        await page.wait_for_timeout(300)
        rec_lang_en = await page.evaluate("() => window.getLocaleForLang ? window.getLocaleForLang('en') : null")
        print(f"Recognizer locale in English: {rec_lang_en}")
        assert rec_lang_en == "en-IN", f"getLocaleForLang mismatch for English: {rec_lang_en}"

        await page.click("button:has-text('End Call')")
        await page.wait_for_selector("#voiceCallModal", state="hidden")
        print("Closed voice modal successfully on production.")

        await browser.close()
        print("\n=======================================================")
        print("ALL LIVE PRODUCTION BROWSER LOCALIZATION TESTS PASSED!")
        print("=======================================================")

if __name__ == "__main__":
    asyncio.run(run_prod_verification())
