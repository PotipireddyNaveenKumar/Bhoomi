import json

log_path = r"C:\Users\SURESH\.gemini\antigravity-ide\brain\084f891f-a0c0-492a-92ae-4dbface0aea9\.system_generated\logs\transcript_full.jsonl"
with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
    for line in f:
        if '"step_index":4015' in line:
            obj = json.loads(line)
            with open("demo_prompt.txt", "w", encoding="utf-8") as out:
                out.write(obj.get("content", ""))
            print("Successfully extracted prompt 4015, length:", len(obj.get("content", "")))
            break
