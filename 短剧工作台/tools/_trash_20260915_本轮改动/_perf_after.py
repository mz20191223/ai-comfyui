"""改后复测：等后端起来再打一遍看板与全站主要接口（临时脚本）"""
import json
import time
import urllib.request

OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
BASE = "http://127.0.0.1:8770/api"

# 等后端就绪
t0 = time.perf_counter()
while True:
    try:
        with OP.open(BASE + "/projects", timeout=5) as r:
            r.read()
        print(f"后端就绪（等待 {time.perf_counter()-t0:.1f}s）\n")
        break
    except Exception as e:
        if time.perf_counter() - t0 > 60:
            raise SystemExit(f"后端 60s 未就绪: {e}")
        time.sleep(0.7)


def timed(path, label, method="GET"):
    t0 = time.perf_counter()
    try:
        req = urllib.request.Request(BASE + path, method=method,
                                     data=b"{}" if method == "POST" else None,
                                     headers={"Content-Type": "application/json"})
        with OP.open(req, timeout=180) as r:
            raw = r.read()
        ms = (time.perf_counter() - t0) * 1000
        try:
            obj = json.loads(raw)
            n = len(obj) if isinstance(obj, list) else "-"
        except Exception:
            n = "?"
        print(f"{ms:8.1f} ms  {label:<40} {len(raw)/1024:7.1f} KB  条数 {n}")
        return ms
    except Exception as e:
        print(f"{'ERR':>8}     {label:<40} {type(e).__name__}: {e}")
        return None


print("=== 看板页首屏（改动目标） ===")
timed("/projects", "GET /projects")
timed("/projects/1/episodes", "GET /projects/1/episodes")
for ep in (1, 2, 3):
    timed(f"/episodes/{ep}/shots", f"GET /episodes/{ep}/shots")

print("\n=== 二次调用（连接已复用） ===")
for ep in (1, 2, 3):
    timed(f"/episodes/{ep}/shots", f"GET /episodes/{ep}/shots (2nd)")

print("\n=== 其它页面主接口 ===")
timed("/projects/1/overview", "GET /projects/1/overview")
timed("/projects/1/episodes/1/production-plan", "GET production-plan")
timed("/episodes/1/lint", "POST /episodes/1/lint", "POST")
timed("/tasks?limit=50", "GET /tasks")
timed("/projects/1/health", "GET /projects/1/health")
timed("/projects/1/assets", "GET /projects/1/assets")
timed("/projects/1/prompt-stats", "GET /projects/1/prompt-stats")
timed("/shots/113", "GET /shots/113")

print("\n=== 三次连打，看是否稳定 ===")
for i in range(3):
    timed("/episodes/1/shots", f"GET /episodes/1/shots (run {i+3})")
