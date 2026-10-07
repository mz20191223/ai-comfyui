"""一次性补丁：ShotDetail.vue + api/index.js 清理就绪态与确认闸门的残留。"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(r"D:/Aicomfyui/短剧工作台/frontend/src")


def patch(rel: str, pairs: list[tuple[str, str]]) -> bool:
    p = ROOT / rel
    t = p.read_text(encoding="utf-8")
    ok = True
    for old, new in pairs:
        n = t.count(old)
        if n != 1:
            print(f"  ✗ 命中 {n} 次（应为 1）：{old.strip().splitlines()[0][:70]}")
            ok = False
            continue
        t = t.replace(old, new, 1)
        print(f"  ✓ {old.strip().splitlines()[0][:70]}")
    if ok:
        p.write_text(t, encoding="utf-8")
    else:
        print("  !! 未写回")
    return ok


DETAIL = [
    # 标题改成只读展示，去掉可编辑输入框
    ("const titleEdit = ref('')\n", ""),
    ("  titleEdit.value = data.value.shot.title || ''\n", ""),
    (
        "async function saveTitle(v) {\n"
        "  await api.patchShot(sid, { shot: { title: v } })\n"
        "  ElMessage.success('已保存')\n"
        "}\n"
        "\n",
        "",
    ),
    # 确认本镜闸门整体移除
    (
        "async function confirmShot() {\n"
        "  await api.confirmShot(sid)\n"
        "  ElMessage.success('已确认本镜')\n"
        "  reload()\n"
        "}\n"
        "\n",
        "",
    ),
]

API = [
    ("  confirmShot: (id) => http.post(`/shots/${id}/confirm`),\n", ""),
    ("  unconfirmShot: (id) => http.post(`/shots/${id}/unconfirm`),\n", ""),
    ("  candidateAction: (sid, cid, data) => http.post(`/shots/${sid}/candidates/${cid}`, data),\n", ""),
]


def main() -> None:
    ok = True
    print("views/ShotDetail.vue")
    ok &= patch("views/ShotDetail.vue", DETAIL)
    print("api/index.js")
    ok &= patch("api/index.js", API)
    print()
    print("全部通过" if ok else "!! 有未命中项")


if __name__ == "__main__":
    main()
