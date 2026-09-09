import subprocess
import asyncio
import json
import urllib.request
import time
import base64
import os
import sys
import websockets

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
REMOTE_PORT = 9222
USER_DATA_DIR = r"C:\Users\SURESH\SIH\tmp_chrome_diag"
APP_URL = "http://127.0.0.1:8000/app"
SCREENSHOT_PATH = r"C:\Users\SURESH\.gemini\antigravity-ide\brain\084f891f-a0c0-492a-92ae-4dbface0aea9\.tempmediaStorage\media_browser_verification.png"

async def run_diagnostic():
    # 1. Start Chrome
    os.makedirs(USER_DATA_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(SCREENSHOT_PATH), exist_ok=True)

    chrome_cmd = [
        CHROME_PATH,
        f"--remote-debugging-port={REMOTE_PORT}",
        f"--user-data-dir={USER_DATA_DIR}",
        "--headless=new",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        "--window-size=1280,800",
        APP_URL
    ]

    print("Starting Chrome process...")
    proc = subprocess.Popen(chrome_cmd)
    time.sleep(2)

    try:
        # 2. Query target list from CDP
        target_url = None
        for attempt in range(10):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{REMOTE_PORT}/json") as resp:
                    targets = json.loads(resp.read().decode("utf-8"))
                    for t in targets:
                        if t.get("type") == "page":
                            target_url = t.get("webSocketDebuggerUrl")
                            break
                    if target_url:
                        break
            except Exception as e:
                time.sleep(1)

        if not target_url:
            print("ERROR: Could not get webSocketDebuggerUrl from Chrome.")
            return

        print("Connected to target:", target_url)

        # 3. Connect via WebSocket
        async with websockets.connect(target_url) as ws:
            msg_id = 0
            async def send_cmd(method, params=None):
                nonlocal msg_id
                msg_id += 1
                payload = {"id": msg_id, "method": method}
                if params:
                    payload["params"] = params
                await ws.send(json.dumps(payload))
                return msg_id

            await send_cmd("Page.enable")
            await send_cmd("Runtime.enable")
            await send_cmd("Network.enable")
            await send_cmd("DOM.enable")

            console_logs = []
            network_requests = []
            network_responses = []

            async def listen_events():
                while True:
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
                        evt = json.loads(raw)
                        method = evt.get("method")
                        if method == "Runtime.consoleAPICalled":
                            args = evt.get("params", {}).get("args", [])
                            log_text = " ".join([str(a.get("value", a)) for a in args])
                            console_logs.append(log_text)
                            print(f"[CONSOLE] {log_text}")
                        elif method == "Runtime.exceptionThrown":
                            exc = evt.get("params", {}).get("exceptionDetails", {})
                            print(f"[JS EXCEPTION] {exc.get('text')} {exc.get('exception', {})}")
                        elif method == "Network.requestWillBeSent":
                            req = evt.get("params", {}).get("request", {})
                            url = req.get("url", "")
                            if "api" in url:
                                network_requests.append(req)
                                print(f"[NETWORK REQ] {req.get('method')} {url}")
                        elif method == "Network.responseReceived":
                            res = evt.get("params", {}).get("response", {})
                            url = res.get("url", "")
                            if "api" in url:
                                network_responses.append(res)
                                print(f"[NETWORK RESP] {res.get('status')} {url}")
                    except asyncio.TimeoutError:
                        break

            # Let initial page load finish
            await asyncio.sleep(2)
            await listen_events()

            print("Evaluating quickDemoLogin()...")
            eval_id = await send_cmd("Runtime.evaluate", {
                "expression": "quickDemoLogin(); document.title;"
            })
            await asyncio.sleep(1)
            await listen_events()

            print("Typing message and sending...")
            js_send = """
            (function() {
                const inp = document.getElementById('chatInput');
                if (!inp) return 'ERROR: chatInput not found';
                inp.value = 'Which crop should I grow in black soil?';
                inp.dispatchEvent(new Event('input', { bubbles: true }));
                const btn = document.getElementById('btnSend');
                if (!btn) return 'ERROR: btnSend not found';
                btn.disabled = false;
                btn.click();
                return 'CLICKED_SEND';
            })()
            """
            await send_cmd("Runtime.evaluate", {"expression": js_send})

            print("Waiting for response and UI rendering (6 seconds)...")
            for _ in range(6):
                await asyncio.sleep(1)
                await listen_events()

            # Inspect rendered assistant messages and cards
            js_inspect = """
            (function() {
                const rows = Array.from(document.querySelectorAll('.message-row.assistant'));
                const cards = Array.from(document.querySelectorAll('.assistant-card'));
                const texts = rows.map(r => r.innerText.trim());
                const cardTitles = cards.map(c => {
                    const title = c.querySelector('.card-title');
                    const pills = Array.from(c.querySelectorAll('.metric-pill')).map(p => p.innerText.trim());
                    return {
                        title: title ? title.innerText.trim() : '',
                        pills: pills
                    };
                });
                return JSON.stringify({
                    assistant_rows_count: rows.length,
                    texts: texts,
                    cards: cardTitles
                });
            })()
            """
            inspect_id = await send_cmd("Runtime.evaluate", {"expression": js_inspect, "returnByValue": True})
            
            # Wait for evaluate response
            inspect_result = None
            for _ in range(5):
                raw = await ws.recv()
                evt = json.loads(raw)
                if evt.get("id") == inspect_id:
                    inspect_result = evt.get("result", {}).get("result", {}).get("value")
                    break

            print("\n=== UI INSPECTION RESULT ===")
            print(inspect_result)

            # Capture screenshot
            print("Capturing screenshot...")
            ss_id = await send_cmd("Page.captureScreenshot", {"format": "png"})
            while True:
                raw = await ws.recv()
                evt = json.loads(raw)
                if evt.get("id") == ss_id:
                    img_b64 = evt.get("result", {}).get("data")
                    if img_b64:
                        with open(SCREENSHOT_PATH, "wb") as sf:
                            sf.write(base64.b64decode(img_b64))
                        print(f"Screenshot saved to: {SCREENSHOT_PATH}")
                    break

            # Save detailed log report
            out_report = {
                "console_logs": console_logs,
                "network_requests": [{"url": r.get("url"), "method": r.get("method")} for r in network_requests],
                "network_responses": [{"url": r.get("url"), "status": r.get("status")} for r in network_responses],
                "dom_state": json.loads(inspect_result) if inspect_result else None,
                "screenshot": SCREENSHOT_PATH
            }
            with open("scratch_browser_results.json", "w", encoding="utf-8") as rf:
                json.dump(out_report, rf, indent=2)

    finally:
        proc.terminate()
        print("Chrome process terminated.")

if __name__ == "__main__":
    asyncio.run(run_diagnostic())
