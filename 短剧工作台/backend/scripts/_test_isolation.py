"""跨项目隔离测试：不碰真实数据（全部在临时项目里做，测完删干净）。

验证两件事：
1. 别的项目的资产 → 挂到本项目镜头里，必须被拒（400）
2. 本项目自己的资产 → 正常挂上（200）
"""
from __future__ import annotations

import sqlite3
import sys

import httpx

DB = r"D:\Aicomfyui\短剧工作台\data\studio.db"
BASE = "http://127.0.0.1:8770/api"

c = httpx.Client(base_url=BASE, timeout=30)


def ok(label: str, cond: bool) -> bool:
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    return cond


def main() -> int:
    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA foreign_keys=ON")

    created_projects: list[int] = []
    results: list[bool] = []

    print("=== 1. 建两个临时项目 ===")
    r = c.post("/projects", json={"name": "__隔离测试项目A__"})
    if r.status_code >= 300:
        print("  建项目失败：", r.status_code, r.text[:200])
        return 1
    pa = r.json()["id"]
    created_projects.append(pa)
    pb = c.post("/projects", json={"name": "__隔离测试项目B__"}).json()["id"]
    created_projects.append(pb)
    print(f"  项目A={pa}  项目B={pb}")

    print("=== 2. 在项目A里建临时集 + 镜头 ===")
    cur = conn.execute("INSERT INTO episodes(project_id, number) VALUES(?, ?)", (pa, 999))
    ea = cur.lastrowid
    cur = conn.execute(
        "INSERT INTO shots(episode_id, shot_code) VALUES(?, ?)", (ea, "__TEST__")
    )
    sa = cur.lastrowid
    conn.commit()
    print(f"  集={ea}  镜头={sa}")

    print("=== 3. 两个项目各建一个资产 ===")
    ra = c.post(f"/projects/{pa}/assets", json={"name": "__测试角色A__", "asset_type": "character"})
    rb = c.post(f"/projects/{pb}/assets", json={"name": "__测试角色B__", "asset_type": "character"})
    aa = ra.json()["id"]
    ab = rb.json()["id"]
    print(f"  资产A(属项目A)={aa}  资产B(属项目B)={ab}")

    print("=== 4. 项目B 的资产挂到 项目A 的镜头（必须被拒）===")
    r = c.post(
        f"/shots/{sa}/refs",
        json={"target_side": "video", "slot_index": 0, "file_name": "x.jpg", "asset_id": ab},
    )
    print(f"  HTTP {r.status_code}  {r.text[:160]}")
    results.append(ok("跨项目引用被拒绝", r.status_code == 400))

    n = conn.execute(
        "SELECT COUNT(*) FROM shot_asset_links WHERE shot_id=?", (sa,)
    ).fetchone()[0]
    results.append(ok("被拒后没有落库（0 条链接）", n == 0))

    print("=== 5. 项目A 自己的资产挂到 项目A 的镜头（必须放行）===")
    r = c.post(
        f"/shots/{sa}/refs",
        json={"target_side": "video", "slot_index": 0, "file_name": "x.jpg", "asset_id": aa},
    )
    print(f"  HTTP {r.status_code}")
    results.append(ok("同项目引用放行", r.status_code == 200))

    n = conn.execute(
        "SELECT COUNT(*) FROM shot_asset_links WHERE shot_id=?", (sa,)
    ).fetchone()[0]
    results.append(ok("同项目引用已落库（1 条）", n == 1))

    print("=== 6. 资产列表按项目隔离 ===")
    la = c.get(f"/projects/{pa}/assets").json()
    lb = c.get(f"/projects/{pb}/assets").json()
    results.append(ok("项目A 只看到自己的 1 个测试资产", len(la) == 1 and la[0]["id"] == aa))
    results.append(ok("项目B 只看到自己的 1 个测试资产", len(lb) == 1 and lb[0]["id"] == ab))

    print("=== 7. 资产详情带所属项目 ===")
    d = c.get(f"/assets/{aa}").json()
    results.append(ok("资产详情含 project_name", d.get("project_name") == "__隔离测试项目A__"))

    print("=== 8. 清理临时数据 ===")
    for pid in created_projects:
        c.delete(f"/projects/{pid}")
    conn.close()

    conn = sqlite3.connect(DB)
    left = {
        "projects": conn.execute(
            "SELECT COUNT(*) FROM projects WHERE name LIKE '__隔离测试%'"
        ).fetchone()[0],
        "episodes": conn.execute("SELECT COUNT(*) FROM episodes WHERE id=?", (ea,)).fetchone()[0],
        "shots": conn.execute("SELECT COUNT(*) FROM shots WHERE id=?", (sa,)).fetchone()[0],
        "assets": conn.execute(
            "SELECT COUNT(*) FROM assets WHERE id IN (?,?)", (aa, ab)
        ).fetchone()[0],
        "links": conn.execute(
            "SELECT COUNT(*) FROM shot_asset_links WHERE shot_id=?", (sa,)
        ).fetchone()[0],
    }
    conn.close()
    print("  残留：", left)
    results.append(ok("临时数据全部清干净", all(v == 0 for v in left.values())))

    print("=== 9. 真实数据未受影响 ===")
    conn = sqlite3.connect(DB)
    real = conn.execute("SELECT COUNT(*) FROM shots").fetchone()[0]
    links = conn.execute("SELECT COUNT(*) FROM shot_asset_links").fetchone()[0]
    assets = conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0]
    conn.close()
    print(f"  镜头 {real} / 资产 {assets} / 引用槽 {links}")
    results.append(ok("镜头数仍为 87", real == 87))
    results.append(ok("资产数仍为 30", assets == 30))

    print()
    print(f"结果：{sum(results)}/{len(results)} 通过")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
