import ast
import os

findings = []

for root, dirs, files in os.walk("backend/app"):
    for f in files:
        if f.endswith(".py"):
            filepath = os.path.join(root, f)
            with open(filepath, "r", encoding="utf-8") as pyf:
                content = pyf.read()
            try:
                tree = ast.parse(content, filename=filepath)
            except Exception as e:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler):
                    has_logging = False
                    is_pass = False
                    returns_default = False
                    for b in node.body:
                        if isinstance(b, ast.Pass):
                            is_pass = True
                        elif isinstance(b, ast.Return):
                            if b.value is None or (isinstance(b.value, ast.Constant) and b.value.value in [None, "", False, {}, []]):
                                returns_default = True
                        elif isinstance(b, ast.Expr) and isinstance(b.value, ast.Call):
                            call_str = ast.unparse(b.value)
                            if "log" in call_str or "print" in call_str:
                                has_logging = True

                    exc_name = ast.unparse(node.type) if node.type else "bare except"
                    is_swallowed = (is_pass or returns_default) and not has_logging
                    findings.append({
                        "file": os.path.relpath(filepath, "backend").replace("\\", "/"),
                        "line": node.lineno,
                        "type": exc_name,
                        "is_pass": is_pass,
                        "returns_default": returns_default,
                        "has_logging": has_logging,
                        "is_swallowed": is_swallowed
                    })

print(f"Total exception handlers analyzed: {len(findings)}")
swallowed = [f for f in findings if f["is_swallowed"]]
print(f"Total silently swallowed: {len(swallowed)}")
print("-" * 80)
for s in sorted(swallowed, key=lambda x: (x["file"], x["line"])):
    print(f"{s['file']}:{s['line']} | {s['type']} | pass={s['is_pass']}, return_default={s['returns_default']}, logged={s['has_logging']}")

print("\n" + "=" * 80)
print("ALL HANDLERS (LOGGED & UNLOGGED) IN AGENTS & API:")
print("=" * 80)
for s in sorted(findings, key=lambda x: (x["file"], x["line"])):
    if "api" in s["file"] or "agent" in s["file"]:
        print(f"{s['file']}:{s['line']} | {s['type']} | pass={s['is_pass']}, return_default={s['returns_default']}, logged={s['has_logging']}")
