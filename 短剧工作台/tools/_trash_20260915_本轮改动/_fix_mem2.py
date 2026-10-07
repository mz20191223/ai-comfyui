# -*- coding: utf-8 -*-
"""重写被 shell 反引号破坏的「九、看板瘦身」日志块。"""
import shutil, sys

P = r'C:\Users\Administrator\WorkBuddy\2026-08-27-16-21-46\.workbuddy\memory\2026-09-16.md'
MARK = '## 九、看板瘦身 + 详情改弹窗（2026-09-16 中午）'

GOOD = '''## 九、看板瘦身 + 详情改弹窗（2026-09-16 中午）

- 看板列删除：**参考图列、问题列**。
- 行内「出图 / 出片」快捷按钮**去掉**（避免误点花钱）；操作列只剩「详情」，列宽 200 -> 90。
  连带删掉 ShotBoard 里已无用的 quickGen() 函数。
- **点详情不再跳二级页面**：看板新增 `showDetail` / `detailShot` 两个 ref + 一个大弹窗
  （width 94% / top 4vh / close-on-click-modal=false / destroy-on-close / @closed 时 load 刷新列表），
  内嵌 ShotDetail 组件；整行点击与「详情」按钮都走 `openDetail(row)`。
- **ShotDetail 改造为可嵌入式**：新增 props `shotId` / `projectId` / `embedded`；
  pid / sid 优先取 props，缺省回落 route.params（所以原来的 /p/:pid/shot/:sid 路由仍能直接用）；
  embedded 为真时隐藏「返回」按钮。旧路由保留，当直链备份。
- **嵌套弹窗必须 append-to-body**：外层弹窗体设了 overflow:auto，内层弹窗若不 append-to-body
  会被裁切 / 层级错乱。已给这 4 类补上：ShotDetail 的镜头设置弹窗 + 请求体预览弹窗、
  MediaPicker 的 el-dialog、RefSlots 的两个 el-dialog、PromptEditor 的版本历史 el-drawer。
- 构建通过（vite build exit=0，built in 11.64s）。
'''

txt = open(P, encoding='utf-8').read()
i = txt.find(MARK)
if i < 0:
    print('!! 未找到待替换块')
    sys.exit(1)
head = txt[:i].rstrip('\n') + '\n\n'
open(P, 'w', encoding='utf-8').write(head + GOOD)
shutil.copy2(P, r'D:\Aicomfyui\项目记忆与日志\2026-09-16.md')
print('已修正并同步')
