import os
import sys
import re
import json

TARGET_DIRS = [
    "backend/app",
    "frontend/web",
]

KEYWORDS = [
    ("Ramesh", re.compile(r'\bRamesh\b', re.I)),
    ("Tenali", re.compile(r'\bTenali\b', re.I)),
    ("Guntur", re.compile(r'\bGuntur\b', re.I)),
    ("Chilli_default", re.compile(r'(?:default\s*=\s*["\']chilli["\']|or\s*["\']chilli["\'])', re.I)),
    ("Guntur_default", re.compile(r'(?:default\s*=\s*["\']guntur["\']|or\s*["\']guntur["\'])', re.I)),
    ("Warangal_default", re.compile(r'(?:default\s*=\s*["\']warangal["\']|or\s*["\']warangal["\'])', re.I)),
    ("OTP_bypass", re.compile(r'(?:1234|0000|9999|ALLOW_EVALUATOR_OTP)', re.I)),
    ("Mock_provider", re.compile(r'(?:MockWeatherProvider|MockMarketProvider|mock)', re.I)),
]

def run_audit():
    findings = {k: [] for k, _ in KEYWORDS}
    base_dir = os.path.abspath(".")
    
    for tdir in TARGET_DIRS:
        abs_tdir = os.path.join(base_dir, tdir)
        for root, dirs, files in os.walk(abs_tdir):
            for f in files:
                if not f.endswith((".py", ".js", ".html")):
                    continue
                fpath = os.path.join(root, f)
                relpath = os.path.relpath(fpath, base_dir).replace("\\", "/")
                
                # Check file
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as fp:
                        for idx, line in enumerate(fp, 1):
                            line_str = line.strip()
                            for name, pattern in KEYWORDS:
                                if pattern.search(line_str):
                                    findings[name].append({
                                        "file": relpath,
                                        "line": idx,
                                        "text": line_str[:120]
                                    })
                except Exception as e:
                    pass

    return findings

if __name__ == "__main__":
    res = run_audit()
    output_path = "backend/scripts/forensic_audit_findings.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    print("AUDIT COMPLETE")
    for k, v in res.items():
        print(f"{k}: {len(v)} occurrences")
