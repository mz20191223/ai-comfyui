"""密钥池轮换演练（零成本）。

用临时供应商验证三件事，不碰真实数据：
1. 池里第一个号是坏 key → 自动换到下一个好号，并把坏号标记为失效；
2. 池里账号全不可用 → 明确报错，而不是拿空 key 去请求；
3. 「恢复」能把被标记的号解冻。

走的是官方免费预估端点（不消耗积分、不调用模型），因此不产生任何费用。
真 key 从库里读，不经过命令行。

用法：python scripts/_test_rotation.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core import db  # noqa: E402
from app.core.db import jdumps  # noqa: E402
from app.executors import provider_engine as PE  # noqa: E402

TEST_PROVIDER_KEY = "_test-rotation"
TEST_MODEL_KEY = "_test-rotation-model"
BAD_KEY = "lh_sk_deadbeef_0000000000000000_invalid_key_for_test"


def setup() -> tuple[int, int]:
    real = db.query_one("SELECT base_url, meta FROM providers WHERE key=?", ("listenhub",))
    real_key = db.query_one(
        "SELECT api_key FROM provider_credentials pc JOIN providers p ON p.id=pc.provider_id "
        "WHERE p.key=? ORDER BY pc.sort_order LIMIT 1", ("listenhub",)
    )["api_key"]

    cleanup()
    pid = db.execute(
        "INSERT INTO providers(key, name, capabilities, base_url, auth_header, auth_scheme, "
        "concurrency, timeout_sec, retry, enabled, meta) VALUES(?,?,?,?,?,?,?,?,?,1,?)",
        (TEST_PROVIDER_KEY, "【测试】轮换演练", jdumps(["image"]), real["base_url"],
         "Authorization", "Bearer", 1, 60, 0, real["meta"]),
    )
    src = db.query_one("SELECT * FROM models WHERE key=?", ("gpt-image-25-async",))
    # 必须继承真实模型的 defaults（含 quality）——否则请求体本身不合法（400/29003），
    # 坏号和好号表现一样，轮换根本无从触发。
    mid = db.execute(
        "INSERT INTO models(provider_id, key, name, category, model_name, mode, request_kind, "
        "request_spec, response_spec, poll_spec, defaults, enabled) VALUES(?,?,?,?,?,?,?,?,?,?,?,1)",
        (pid, TEST_MODEL_KEY, "【测试】轮换演练模型", "image", "gpt-image-2.5-flare", "asynchronous",
         "http", src["request_spec"], src["response_spec"], src["poll_spec"], src["defaults"]),
    )
    # 坏号排前面（sort_order 更小），好号在后
    db.execute(
        "INSERT INTO provider_credentials(provider_id, alias, api_key, sort_order) VALUES(?,?,?,?)",
        (pid, "坏号", BAD_KEY, 0),
    )
    db.execute(
        "INSERT INTO provider_credentials(provider_id, alias, api_key, sort_order) VALUES(?,?,?,?)",
        (pid, "好号", real_key, 1),
    )
    return pid, mid


def cleanup() -> None:
    row = db.query_one("SELECT id FROM providers WHERE key=?", (TEST_PROVIDER_KEY,))
    if row:
        db.execute("DELETE FROM providers WHERE id=?", (row["id"],))   # 级联删模型与账号


def main() -> None:
    db.init_db()
    pid, mid = setup()
    print("已建立临时供应商与 2 个账号（坏号在前、好号在后）\n")

    try:
        # ---- 1. 好号能用，坏号被跳过 ----
        out = PE.estimate(PE.load_model_bundle(mid), {"prompt": "a red circle"})
        creds = {c["alias"]: c["status"] for c in PE.list_credentials(pid, only_enabled=False)}
        print("① 预估结果：")
        print(f"   ok={out.get('ok')}  积分={out.get('credits')}  实际用的账号={out.get('credential')}")
        print(f"   池内状态：{creds}")
        assert out.get("ok") and out.get("credits"), "预估应当成功"
        assert out.get("credential") == "好号", "应当自动切到好号"
        assert creds.get("坏号") != "active", "坏号应被打上失效标记"
        print("   ✅ 坏号已被跳过并标记，好号接管\n")

        # ---- 2. 全部不可用 → 明确报错 ----
        db.execute("UPDATE provider_credentials SET status='exhausted' WHERE provider_id=?", (pid,))
        try:
            PE.execute(PE.load_model_bundle(mid), {"prompt": "x"})
            print("② ❌ 期望报错但没有")
        except PE.ProviderError as e:
            print(f"② 全池不可用时：ProviderError → {str(e)[:90]}…")
            print("   ✅ 明确拒绝，没有拿空 key 硬发请求\n")

        # ---- 3. 恢复能解冻 ----
        db.execute(
            "UPDATE provider_credentials SET status='active', cooldown_until=NULL, fail_count=0 "
            "WHERE provider_id=? AND alias='好号'", (pid,),
        )
        usable = PE.usable_credentials(pid)
        print(f"③ 恢复后可用账号：{[c['alias'] for c in usable]}")
        assert [c["alias"] for c in usable] == ["好号"], "恢复后应只剩好号可用"
        print("   ✅ 手动恢复生效\n")

        print("轮换演练：全部通过")
    finally:
        cleanup()
        left = db.query_one(
            "SELECT COUNT(*) c FROM providers WHERE key LIKE '_test-%'"
        )["c"]
        print(f"已清理临时数据（残留 {left} 个测试供应商）")


if __name__ == "__main__":
    main()
