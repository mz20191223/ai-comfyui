#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""给全站所有「操作」列打上 op-col 类（表头 + 单元格），用于统一居中。
幂等：已经带 class-name="op-col" 的列跳过。
"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

VIEWS = r"D:\Aicomfyui\短剧工作台\frontend\src\views"
CSS = r"D:\Aicomfyui\短剧工作台\frontend\src\styles.css"

COL_RE = re.compile(r'(<el-table-column)([^>]*?label="操作"[^>]*?)(/?>)')

CSS_BLOCK = """/* 操作列：表头文字与按钮组一起居中（宽列里左对齐会显得悬空） */
.el-table .op-col .cell { text-align: center; }
.el-table .op-col .cell .op-row { justify-content: center; }
"""


def patch_views() -> None:
    total = 0
    for name in sorted(os.listdir(VIEWS)):
        if not name.endswith(".vue"):
            continue
        path = os.path.join(VIEWS, name)
        raw = open(path, encoding="utf-8", newline="").read()
        crlf = "\r\n" if "\r\n" in raw else "\n"
        text = raw.replace("\r\n", "\n")
        hits = [m for m in COL_RE.finditer(text) if 'class-name="op-col"' not in m.group(2)]
        if not hits:
            continue
        new = COL_RE.sub(
            lambda m: (m.group(0) if 'class-name="op-col"' in m.group(2)
                       else f'{m.group(1)} class-name="op-col" label-class-name="op-col"{m.group(2)}{m.group(3)}'),
            text,
        )
        # 注意 label-class-name="op-col" 里含 class-name="op-col" 子串，按前导空格计数
        got = new.count(' class-name="op-col"')
        assert got == len(hits), (name, got, len(hits))
        assert new.count('label="操作"') == text.count('label="操作"'), name
        open(path, "w", encoding="utf-8", newline="").write(new.replace("\n", crlf))
        print(f"  {name}: {len(hits)} 处")
        total += len(hits)
    print(f"共改 {total} 个操作列")


def patch_css() -> None:
    raw = open(CSS, encoding="utf-8", newline="").read()
    crlf = "\r\n" if "\r\n" in raw else "\n"
    text = raw.replace("\r\n", "\n")
    if ".op-col" in text:
        print("  styles.css: 已有 .op-col 规则，跳过")
        return
    anchor = ".op-row .el-button + .el-button { margin-left: 2px; }"
    assert anchor in text, "找不到 .op-row 锚点"
    text = text.replace(anchor, anchor + "\n" + CSS_BLOCK, 1)
    open(CSS, "w", encoding="utf-8", newline="").write(text.replace("\n", crlf))
    print("  styles.css: 已加 .op-col 居中规则")


if __name__ == "__main__":
    patch_views()
    patch_css()
