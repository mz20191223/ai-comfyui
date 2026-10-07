# -*- coding: utf-8 -*-
"""验证：删掉的接口 404、保留的接口仍通。"""
import json
import sys
import time
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = "http://127.0.0.1:8770/api"

for _ in range(20):
    try:
        urllib.request.urlopen(BASE + "/health", timeout=3)
        print("后端已启动")
        break
    except Exception:
        time.sleep(1.5)
else:
    print("后端未起来，日志尾部：")
    print(open(r"D:\Aicomfyui\短剧工作台\storage\_backend_start.log", encoding="utf-8", errors="replace").read()[-1200:])
    sys.exit(1)


def call(method, path, body=None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        r = urllib.request.urlopen(req, timeout=15)
        return r.status, json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:160]
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


print("\n=== 应当已删除（期望 404/405）===")
for m, p in [("POST", "/creation/episodes/1/production-plan"), ("POST", "/episodes/1/lint")]:
    s, d = call(m, p, {} if m == "POST" else None)
    ok = s in (404, 405)
    print("  %-4s %-42s -> %s %s" % (m, p, s, "✓ 已移除" if ok else "✗ 仍在！%s" % d))

print("\n=== 应当保留（期望 200）===")
checks = [
    ("POST", "/shots/1/lint", None),          # 单镜 lint
    ("GET", "/lint-rules?project_id=1", None),  # Lint 规则
    ("GET", "/lint-checkers", None),
    ("GET", "/creation/projects/1/pipeline", None),
    ("GET", "/projects/1/episodes", None),
]
for m, p, b in checks:
    s, d = call(m, p, b)
    print("  %-4s %-42s -> %s %s" % (m, p, s, "✓" if s == 200 else "✗ %s" % str(d)[:90]))
