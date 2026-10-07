"""数据质量抽查：提示词/参考图/解析结果是否齐全。"""
import sqlite3
from pathlib import Path

DB = Path(r"D:\Aicomfyui\短剧工作台\data\studio.db")
con = sqlite3.connect(str(DB))
con.row_factory = sqlite3.Row
q = con.execute


def show(t):
    print("\n" + "=" * 62)
    print(t)
    print("=" * 62)


show("提示词完整度（按集）")
for r in q(
    """SELECT s.episode_id,
              COUNT(*) AS total,
              SUM(CASE WHEN d.image_prompt IS NULL OR TRIM(d.image_prompt)='' THEN 1 ELSE 0 END) AS no_img,
              SUM(CASE WHEN d.video_prompt  IS NULL OR TRIM(d.video_prompt)='' THEN 1 ELSE 0 END) AS no_vid,
              SUM(CASE WHEN d.hard_constraints IS NULL OR d.hard_constraints IN ('','[]') THEN 1 ELSE 0 END) AS no_hc,
              SUM(CASE WHEN d.action_beats IS NULL OR d.action_beats IN ('','[]') THEN 1 ELSE 0 END) AS no_beat
         FROM shots s LEFT JOIN shot_details d ON d.shot_id = s.id
        GROUP BY s.episode_id ORDER BY s.episode_id"""
):
    print(
        f"  第{r['episode_id']}集 共{r['total']:>3} 镜 | 缺分镜图提示词 {r['no_img']:>3}"
        f" | 缺视频正文 {r['no_vid']:>3} | 无硬约束 {r['no_hc']:>3} | 无时序拍点 {r['no_beat']:>3}"
    )

show("缺分镜图提示词的镜头（前 25）")
rows = q(
    """SELECT s.id, s.episode_id, s.shot_code,
              (SELECT COUNT(*) FROM shot_asset_links l WHERE l.shot_id=s.id) AS links
         FROM shots s LEFT JOIN shot_details d ON d.shot_id=s.id
        WHERE d.image_prompt IS NULL OR TRIM(d.image_prompt)=''
        ORDER BY s.episode_id, s.sort_order LIMIT 25"""
).fetchall()
if not rows:
    print("  （无）")
for r in rows:
    print(f"  第{r['episode_id']}集 {r['shot_code']:<10} (id={r['id']}, 资产链接 {r['links']})")
print(f"  合计 {len(rows)} 条（限制显示 25）")

show("提示词完整度总览")
r = q(
    """SELECT COUNT(*) total,
              SUM(CASE WHEN d.image_prompt IS NULL OR TRIM(d.image_prompt)='' THEN 1 ELSE 0 END) no_img,
              SUM(CASE WHEN d.video_prompt  IS NULL OR TRIM(d.video_prompt)='' THEN 1 ELSE 0 END) no_vid,
              SUM(CASE WHEN d.video_prompt_prefix IS NULL OR TRIM(d.video_prompt_prefix)='' THEN 1 ELSE 0 END) no_pfx
         FROM shots s LEFT JOIN shot_details d ON d.shot_id=s.id"""
).fetchone()
print(f"  共 {r['total']} 镜 | 缺分镜图提示词 {r['no_img']} | 缺视频正文 {r['no_vid']} | 缺接口首行 {r['no_pfx']}")

show("参考图槽位（资产链接 = 参考图来源）")
r = q("SELECT COUNT(*) c FROM shot_asset_links").fetchone()
print(f"  资产↔镜头 链接总数: {r['c']}")
for r in q(
    "SELECT target_side, COUNT(*) c FROM shot_asset_links GROUP BY target_side ORDER BY c DESC"
):
    print(f"    侧别 {r['target_side']}: {r['c']}")
for r in q(
    "SELECT ref_version, COUNT(*) c FROM shot_asset_links GROUP BY ref_version ORDER BY c DESC"
):
    print(f"    引用版本 {r['ref_version']}: {r['c']}")

show("实拍帧（shot_frames）")
for r in q("SELECT frame_type, source, COUNT(*) c FROM shot_frames GROUP BY frame_type, source"):
    print(f"  {r['frame_type']:<8} {r['source']:<12} {r['c']}")

show("台词与音频")
for r in q(
    """SELECT s.episode_id, COUNT(*) c,
              SUM(CASE WHEN l.audio_file IS NULL OR l.audio_file='' THEN 1 ELSE 0 END) noaudio,
              SUM(CASE WHEN l.audio_measured_sec IS NULL THEN 1 ELSE 0 END) nomeasure
         FROM shot_dialog_lines l JOIN shots s ON s.id=l.shot_id GROUP BY s.episode_id"""
):
    print(f"  第{r['episode_id']}集 {r['c']} 条 | 缺音频文件 {r['noaudio']} | 缺实测时长 {r['nomeasure']}")

show("健康问题分布")
for r in q(
    """SELECT issue_type, severity, COUNT(*) c FROM health_issues
        WHERE resolved=0 GROUP BY issue_type, severity ORDER BY c DESC LIMIT 20"""
):
    print(f"  {r['issue_type']:<26} {r['severity']:<8} {r['c']}")
r = q("SELECT COUNT(*) c FROM health_issues WHERE resolved=1").fetchone()
print(f"  （已解决 {r['c']} 条）")

show("资产覆盖")
for r in q("SELECT asset_type, COUNT(*) c FROM assets GROUP BY asset_type"):
    print(f"  {r['asset_type']:<12} {r['c']}")
for r in q(
    """SELECT a.name, (SELECT COUNT(*) FROM asset_images i WHERE i.asset_id=a.id) c
         FROM assets a WHERE c=0 ORDER BY a.name"""
):
    print(f"  无图资产: {r['name']}")

con.close()
