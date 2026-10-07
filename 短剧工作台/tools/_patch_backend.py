BASE = r"D:\Aicomfyui\短剧工作台"

# ---------------- 1) script_service.py ----------------
sp = f"{BASE}\\backend\\app\\services\\script_service.py"
raw = open(sp, "rb").read()
has_crlf = b"\r\n" in raw
lines = raw.decode("utf-8").split("\n")
out = []
r1 = r2 = r3 = False
i = 0
while i < len(lines):
    ln = lines[i]
    # 改动1：outline 资产硬约束 -> 自由写
    if not r1 and "_asset_catalog(assets)" in ln:
        # 上一行（资产约束行，以 "【 开头）已在 out，移除之
        if out and out[-1].lstrip().startswith('"【'):
            out.pop()
        out.append('        "【出场资产（assets）】每个镜头都要写本镜出场的角色 / 场景 / 道具的中文名"')
        out.append('        "（从剧本逻辑里识别、自由写，例如 ["过客", "公司办公室"]）；"')
        out.append('        "资产图是后续才单独生成并登记进资产库的，这里只登记名字，不要去匹配已有资产。"')
        r1 = True
        i += 1
        continue
    # 改动2：write_episodes_shots 去掉 _write_links，改存 assets_text
    if not r2 and "links += _write_links(" in ln:
        del out[-3:]  # 删掉 has= / if not / links+= 三行
        for nl in [
            '            # 创作期只记录本镜出场资产中文名，不在此处匹配资产库（资产图后续才出）',
            '            db.execute(',
            '                "UPDATE shot_details SET assets_text=? WHERE shot_id=?",',
            '                (json.dumps(sh.get("assets") or [], ensure_ascii=False), sid),',
            '            )',
        ]:
            out.append(nl)
        r2 = True
        i += 1
        continue
    # 改动3：_shot_brief 资产名回退 assets_text
    if not r3 and ln.strip() == "names: list[str] = []":
        j = i
        while j < len(lines) and "本镜出场资产" not in lines[j]:
            j += 1
        del out[-(j - i + 1):]  # 删掉 names 块（含结束行）
        for nl in [
            '    names: list[str] = []',
            '    for r in links:',
            '        nm = _norm(r.get("asset_name"))',
            '        if nm and nm not in names:',
            '            names.append(nm)',
            '    # 链接为空（资产图尚未生成/绑定）时，回退到创作期登记的资产中文名',
            '    if not names:',
            '        raw = shot.get("assets_text")',
            '        if isinstance(raw, str) and raw.strip():',
            '            try:',
            '                arr = json.loads(raw)',
            '            except Exception:',
            '                arr = [raw]',
            '            if isinstance(arr, list):',
            '                for x in arr:',
            '                    nm = _norm(x)',
            '                    if nm and nm not in names:',
            '                        names.append(nm)',
            '    if names:',
            '        out.append("  本镜出场资产：" + "、".join(names))',
        ]:
            out.append(nl)
        r3 = True
        i = j + 1
        continue
    out.append(ln)
    i += 1

assert (r1, r2, r3) == (True, True, True), (r1, r2, r3)
text2 = "\n".join(out)
if has_crlf:
    text2 = text2.replace("\n", "\r\n")
open(sp, "wb").write(text2.encode("utf-8"))
print("script_service.py patched (crlf=%s, r1=%s r2=%s r3=%s)" % (has_crlf, r1, r2, r3))

# ---------------- 2) routers/scripts.py ----------------
rp = f"{BASE}\\backend\\app\\routers\\scripts.py"
raw = open(rp, "rb").read()
has_crlf = b"\r\n" in raw
text = raw.decode("utf-8")
old_r = (
    '            "image_target_name": d.get("image_target_name"),\n'
    '            "has_image_prompt": bool((d.get("image_prompt") or "").strip()),\n'
)
assert text.count(old_r) == 1, ("router anchor", text.count(old_r))
new_r = (
    '            "image_target_name": d.get("image_target_name"),\n'
    '            "assets_text": d.get("assets_text"),\n'
    '            "has_image_prompt": bool((d.get("image_prompt") or "").strip()),\n'
)
text = text.replace(old_r, new_r, 1)
if has_crlf:
    text = text.replace("\n", "\r\n")
open(rp, "wb").write(text.encode("utf-8"))
print("routers/scripts.py patched (crlf=%s)" % has_crlf)
