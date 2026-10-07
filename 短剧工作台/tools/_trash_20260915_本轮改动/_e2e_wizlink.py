# -*- coding: utf-8 -*-
"""受控实验：备份镜头90 → 调真实接口注入 → （浏览器验证）→ 还原。

只用 apply-wizard 这个用户真实入口，不手改提示词正文。
"""
import sqlite3, json, os, sys, io, urllib.request
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

DB = r"D:\Aicomfyui\短剧工作台\data\studio.db"
BAK = r"D:\Aicomfyui\短剧工作台\tools\_shot90_backup.json"
SID = 90

action = sys.argv[1] if len(sys.argv) > 1 else "backup"

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row

if action == "backup":
    row = con.execute("SELECT * FROM shot_details WHERE shot_id=?", (SID,)).fetchone()
    if row is None:
        print("!! 没有 shot_details 行")
        sys.exit(1)
    data = {k: row[k] for k in row.keys()}
    ep = con.execute(
        "SELECT s.id, s.title, s.episode_id, e.project_id FROM shots s "
        "JOIN episodes e ON e.id=s.episode_id WHERE s.id=?", (SID,)).fetchone()
    data["__meta"] = dict(ep) if ep else {}
    with open(BAK, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print("已备份 →", BAK)
    print("  image_prompt 长度:", len(data["image_prompt"] or ""))
    print("  video_prompt 长度:", len(data["video_prompt"] or ""))
    print("  camera_shot/angle/movement/subject_position:",
          repr(data["camera_shot"]), repr(data["angle"]), repr(data["movement"]), repr(data["subject_position"]))
    print("  所属:", data["__meta"])
    print("  正文里是否已含旧 note:", (data["wiz_image_note"] or "") in (data["image_prompt"] or ""))

elif action == "apply":
    body = json.dumps({
        "camera_shot": "CU", "angle": "HIGH_ANGLE",
        "movement": "", "subject_position": "右上",
    }).encode("utf-8")
    req = urllib.request.Request(
        "http://127.0.0.1:8770/api/shots/%d/apply-wizard" % SID,
        data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        r = urllib.request.urlopen(req, timeout=10)
        res = json.loads(r.read().decode("utf-8"))
        print("HTTP", r.status)
        print(json.dumps(res, ensure_ascii=False, indent=1)[:900])
    except urllib.error.HTTPError as e:
        print("HTTPError", e.code, e.read().decode("utf-8", "replace")[:500])

elif action == "restore":
    if not os.path.exists(BAK):
        print("!! 没有备份，不能还原")
        sys.exit(1)
    with open(BAK, encoding="utf-8") as f:
        data = json.load(f)
    data.pop("__meta", None)
    cols = ", ".join("%s=?" % k for k in data)
    con.execute("UPDATE shot_details SET %s WHERE shot_id=?" % cols,
                list(data.values()) + [SID])
    con.commit()
    chk = con.execute("SELECT image_prompt, video_prompt, wiz_image_note, wiz_video_note "
                      "FROM shot_details WHERE shot_id=?", (SID,)).fetchone()
    same = (chk["image_prompt"] == data["image_prompt"] and chk["video_prompt"] == data["video_prompt"]
            and chk["wiz_image_note"] == data["wiz_image_note"]
            and chk["wiz_video_note"] == data["wiz_video_note"])
    print("已还原镜头90，逐字一致:", same)
    print("  image_prompt 长度:", len(chk["image_prompt"] or ""))
    print("  video_prompt 长度:", len(chk["video_prompt"] or ""))
    print("  wiz_image_note:", repr(chk["wiz_image_note"]))
    print("  wiz_video_note:", repr(chk["wiz_video_note"]))
else:
    print("用法: backup | apply | restore")
