import pytest
import asyncio
import sys
from playwright.async_api import async_playwright

# Ensure UTF-8 stdout for Windows command line emoji support
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:8000"

@pytest.mark.asyncio
async def test_e2e_weather_market_finance_browser():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        print("\n[STEP 1] Navigating to BHOOMI Web Application...")
        await page.goto(BASE_URL, wait_until="networkidle")
        title = await page.title()
        print(f"Page Title: {title}")
        assert "BHOOMI" in title

        # Check if auth modal is visible; perform quick demo login if needed
        print("[AUTH] Checking authentication state and bypassing auth modal...")
        await page.evaluate("""() => {
            if (typeof window.quickDemoLogin === 'function') {
                window.quickDemoLogin();
            }
            const authModal = document.getElementById('authModal');
            if (authModal) authModal.style.display = 'none';
        }""")
        await page.wait_for_timeout(1000)

        # 1. TEST FINANCE MODAL & 7-COMPONENT CALCULATION
        print("\n[STEP 2] Testing Farm Finance & Profit Modal...")
        finance_btn = page.locator("#btnOpenFinance")
        assert await finance_btn.is_visible(), "Finance & Profit button must be visible in header"
        await finance_btn.click()
        await page.wait_for_selector("#financeModal", state="visible", timeout=5000)

        finance_modal = page.locator("#financeModal")
        assert await finance_modal.is_visible(), "Finance modal should be displayed"

        # Populate 7-component costs
        await page.fill("#finCrop", "Chilli")
        await page.fill("#finArea", "1.0")
        await page.select_option("#finAreaUnit", "acre")

        await page.fill("#finCostSeed", "5000")
        await page.fill("#finCostFertilizer", "12000")
        await page.fill("#finCostPesticide", "8000")
        await page.fill("#finCostLabour", "25000")
        await page.fill("#finCostIrrigation", "6000")
        await page.fill("#finCostMachinery", "10000")
        await page.fill("#finCostOther", "4000")

        await page.fill("#finYield", "10.0")
        await page.select_option("#finYieldUnit", "quintal")
        await page.fill("#finPrice", "12000")
        await page.select_option("#finPriceUnit", "rupees_per_quintal")

        print("[FINANCE] Submitting profit calculation...")
        await page.click("#btnCalcProfit")
        await page.wait_for_selector("#finResultsPanel", state="visible", timeout=5000)
        await page.wait_for_function(
            "() => { const el = document.getElementById('finResultsPanel'); return el && !el.innerText.includes('Calculating') && el.innerText.includes('Total Cost'); }",
            timeout=10000
        )

        results_panel = page.locator("#finResultsPanel")
        assert await results_panel.is_visible(), "Results panel must be displayed"
        results_text = await results_panel.inner_text()
        print(f"Finance Calculation Results:\n{results_text[:300].encode('ascii', errors='replace').decode()}...")

        assert "70,000" in results_text, "Total cost of ₹70,000 must appear"
        assert ("1,20,000" in results_text or "120,000" in results_text), "Gross revenue of ₹1,20,000 must appear"
        assert "50,000" in results_text, "Net profit of ₹50,000 must appear"
        assert "Deterministic" in results_text

        # 2. TEST WHAT-IF SIMULATION
        print("\n[STEP 3] Testing What-If Simulation Levers...")
        # Open simulation details if collapsed
        await page.evaluate("""() => {
            const details = document.querySelector('#financeForm details');
            if (details) details.open = true;
        }""")
        await page.wait_for_timeout(300)

        await page.fill("#simPriceChange", "-20")
        await page.click("#btnRunSim")
        await page.wait_for_function(
            "() => { const el = document.getElementById('finResultsPanel'); return el && !el.innerText.includes('Simulating') && (el.innerText.includes('Simulation') || el.innerText.includes('Scenario')); }",
            timeout=10000
        )

        sim_results = await results_panel.inner_text()
        print(f"What-If Simulation Results:\n{sim_results[:300].encode('ascii', errors='replace').decode()}...")

        assert "Multi-Lever What-If Simulation" in sim_results or "Scenario Comparison" in sim_results
        assert "9,600" in sim_results, "Simulated price ₹9,600 must appear"
        assert "26,000" in sim_results, "Simulated profit ₹26,000 must appear"
        assert "-48" in sim_results, "Profit impact -48% must appear"

        # Capture finance modal screenshot artifact
        fin_screenshot = "C:/Users/SURESH/.gemini/antigravity-ide/brain/2a128586-41a3-4e2c-b4bd-b724cf51ed0b/finance_modal_verification.png"
        await page.screenshot(path=fin_screenshot)
        print(f"Saved finance modal screenshot to: {fin_screenshot}")

        # Close finance modal
        await page.evaluate("""() => {
            if (typeof window.closeFinanceModal === 'function') {
                window.closeFinanceModal();
            } else {
                const m = document.getElementById('financeModal');
                if (m) m.style.display = 'none';
            }
        }""")
        await page.wait_for_timeout(500)
        assert not await finance_modal.is_visible(), "Finance modal should close"

        # 3. TEST CHAT QUERY: TOMORROW RAIN & SPRAY ADVISORY
        print("\n[STEP 4] Testing Weather Tomorrow & Spray Advisory in Chat...")
        chat_input = page.locator("#chatInput")
        await chat_input.fill("Will it rain tomorrow in Warangal? Is it safe to spray?")
        await page.evaluate("() => { if (typeof checkSendButtonState === 'function') checkSendButtonState(); }")
        await page.click("#btnSend")

        # Wait for assistant response
        print("Waiting for assistant response...")
        await page.wait_for_selector(".message-row.assistant", timeout=30000)
        await page.wait_for_timeout(3000)

        assistant_messages = page.locator(".message-row.assistant .message-text")
        last_msg = await assistant_messages.last.inner_text()
        print(f"Assistant Response:\n{last_msg[:250].encode('ascii', errors='replace').decode()}...")
        assert len(last_msg) > 10, "Assistant should reply to weather query"

        # Check for weather card or spray safe advisory
        weather_card = page.locator(".assistant-card")
        card_count = await weather_card.count()
        print(f"Assistant rendered {card_count} structured visual card(s)")
        assert card_count >= 1, "Assistant must attach structured intelligence card"

        card_text = await weather_card.last.inner_text()
        print(f"Card content: {card_text[:200].encode('ascii', errors='replace').decode()}")
        assert any(k in card_text for k in ["Asia/Kolkata", "Warangal", "Temp", "Spray", "Rain", "Weather", "Forecast"])

        # 4. TEST CHAT QUERY: LIVE MARKET PRICES
        print("\n[STEP 5] Testing Market Prices Query in Chat...")
        await chat_input.fill("What is the current mandi price of cotton in Warangal?")
        await page.evaluate("() => { if (typeof checkSendButtonState === 'function') checkSendButtonState(); }")
        await page.click("#btnSend")

        print("Waiting for assistant market response...")
        await page.wait_for_timeout(5000)

        assistant_messages = page.locator(".message-row.assistant .message-text")
        market_msg = await assistant_messages.last.inner_text()
        print(f"Assistant Market Response:\n{market_msg[:250].encode('ascii', errors='replace').decode()}...")
        assert len(market_msg) > 10, "Assistant should reply to market price query"

        # Save screenshot artifact
        screenshot_path = "C:/Users/SURESH/.gemini/antigravity-ide/brain/2a128586-41a3-4e2c-b4bd-b724cf51ed0b/browser_verification.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"Saved full page screenshot to: {screenshot_path}")

        await browser.close()
        print("\n[SUCCESS] Browser E2E verification complete!")

if __name__ == "__main__":
    asyncio.run(test_e2e_weather_market_finance_browser())
