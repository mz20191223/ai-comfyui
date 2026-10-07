# -*- coding: utf-8 -*-
"""临时自检：复查 provider / 模型 / 密钥池落点。"""
import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
con = sqlite3.connect(r"D:\Aicomfyui\短剧工作台\data\studio.db")
con.row_factory = sqlite3.Row

for sql, tag in [
    ("SELECT id,name,key,base_url,enabled FROM providers", "providers"),
    ("SELECT id,name,key,category,model_name,mode,enabled FROM models WHERE category='llm'", "llm 模型"),
    ("SELECT id,provider_id,alias,enabled,status,substr(api_key,1,12) AS k FROM provider_credentials", "密钥池"),
    ("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name", "全部表"),
]:
    print("===", tag, "===")
    try:
        for r in con.execute(sql):
            print("  ", dict(r))
    except Exception as e:
        print("   查询失败:", e)
