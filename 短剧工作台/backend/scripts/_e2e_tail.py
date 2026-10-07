"""端到端演练：拿真实 mp4 跑通「抽尾帧 → 登记本镜 last → 回填下一镜首帧」。

只新增文件（0102_tail.jpg 当前不存在），不覆盖任何已有素材。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import hooks_service  # noqa: E402
from app.core import db  # noqa: E402

VIDEO = Path(r"D:\Aicomfyui\minimax3创作内容\重制版\分镜视频\0102.mp4")
SHOT_ID = 89          # 第1集 镜头2
NEXT_ID = 90          # 第1集 镜头3

print(f"源视频：{VIDEO}")
print(f"存在  ：{VIDEO.exists()}")
print()

print("--- 测试前状态 ---")
for sid, tag in ((SHOT_ID, "镜头2"), (NEXT_ID, "镜头3")):
    rows = db.query("SELECT frame_type, file_name FROM shot_frames WHERE shot_id=?", (sid,))
    print(f"  {tag} 帧记录: {[(r['frame_type'], r['file_name']) for r in rows] or '无'}")

print()
print("--- 执行 extract_and_register_tail ---")
try:
    res = hooks_service.extract_and_register_tail(SHOT_ID, VIDEO, link_to_next=True)
    for k, v in res.items():
        print(f"  {k}: {v}")
except Exception as e:  # noqa: BLE001
    import traceback

    print("  失败:", e)
    traceback.print_exc()

print()
print("--- 测试后状态 ---")
for sid, tag in ((SHOT_ID, "镜头2"), (NEXT_ID, "镜头3")):
    rows = db.query("SELECT frame_type, file_name, source, note FROM shot_frames WHERE shot_id=?", (sid,))
    print(f"  {tag}:")
    for r in rows:
        print(f"     {r['frame_type']:<6} {r['file_name']:<20} {r['source']:<12} {r['note']}")

print()
print("--- 新生成的尾帧文件 ---")
tail = Path(r"D:\Aicomfyui\minimax3创作内容\重制版\分镜图\视频尾帧\0102_tail.jpg")
print(f"  {tail}  存在={tail.exists()}"
      + (f"  {tail.stat().st_size} 字节" if tail.exists() else ""))
