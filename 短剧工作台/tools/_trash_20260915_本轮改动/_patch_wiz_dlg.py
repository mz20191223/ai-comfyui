"""把「镜头设置」从独立折叠卡改成弹窗（入口在提示词工具栏 + 正文里可点的镜头语言句）。"""
from __future__ import annotations

from pathlib import Path

P = Path(r"D:/Aicomfyui/短剧工作台/frontend/src/views/ShotDetail.vue")
t = P.read_text(encoding="utf-8")
orig = len(t)

# 1) 整块摘出 wizard card
i = t.index('        <div class="card wizard">')
j = t.index("        <PromptEditor", i)
card = t[i:j]
t = t[:i] + t[j:]
print(f"  ✓ 摘出独立卡（{len(card)} 字符）")

# 2) 从卡里取出 wz-body 的内部
BS = '<div v-if="showWizard" class="wz-body">'
bs = card.index(BS) + len(BS)
be_outer = card.rindex("</div>")
be = card.rindex("</div>", 0, be_outer)
inner = card[bs:be].rstrip()
print(f"  ✓ 提取面板内容（{len(inner)} 字符）")

# 3) 变成 el-dialog，插到其它弹窗前
dialog = (
    '\n    <el-dialog v-model="showWizard" title="镜头设置" width="760px">\n'
    '      <div class="wz-body">' + inner + "\n      </div>\n"
    "    </el-dialog>\n"
)
k = t.index("    <el-dialog v-model=\"showDry\"")
t = t[:k] + dialog + "\n" + t[k:]
print("  ✓ 生成 el-dialog")


def one(old: str, new: str, label: str) -> None:
    global t
    n = t.count(old)
    if n != 1:
        raise SystemExit(f"✗ {label}: 命中 {n} 次（应为 1），未写回")
    t = t.replace(old, new, 1)
    print(f"  ✓ {label}")


# 4) 分镜图编辑器：接上镜头语言句 + 工具栏入口，去掉片段库
one(
    '          target-kind="shot_image"\n'
    '          :target-id="sid"\n'
    '          :snippets="snippets"\n'
    '          @reload="reload"\n'
    '          @saved="reload"\n'
    "        />\n",
    '          target-kind="shot_image"\n'
    '          :target-id="sid"\n'
    '          :wizard-note="note.image_note"\n'
    '          @open-wizard="openWizard"\n'
    '          @reload="reload"\n'
    '          @saved="reload"\n'
    "        >\n"
    '          <template #tools>\n'
    '            <el-button size="small" text @click="openWizard">镜头设置</el-button>\n'
    "          </template>\n"
    "        </PromptEditor>\n",
    "分镜图编辑器接入",
)

# 5) 视频编辑器：运镜句同样可点
one(
    '          target-kind="shot_video"\n'
    '          :target-id="sid"\n'
    '          :snippets="snippets"\n'
    '          @reload="reload"\n',
    '          target-kind="shot_video"\n'
    '          :target-id="sid"\n'
    '          :wizard-note="note.video_note"\n'
    '          @open-wizard="openWizard"\n'
    '          @reload="reload"\n',
    "视频编辑器接入",
)

# 6) 片段库相关的变量与加载全部拿掉
one("const snippets = ref([])\n", "", "删 snippets 变量")
one("  snippets.value = await api.snippets(pid)\n", "", "删 snippets 加载")

# 7) toggleWizard → openWizard
one(
    "function toggleWizard() {\n"
    "  if (!showWizard.value) {\n"
    "    syncWizardFromDetail()\n"
    "    refreshNote()\n"
    "  }\n"
    "  showWizard.value = !showWizard.value\n"
    "}\n",
    "function openWizard() {\n"
    "  syncWizardFromDetail()\n"
    "  refreshNote()\n"
    "  showWizard.value = true\n"
    "}\n",
    "openWizard",
)

P.write_text(t, encoding="utf-8")
print(f"\n{orig} → {len(t)} 字符")
for kw in ("snippets", "toggleWizard"):
    print(f"残留 {kw}: {t.count(kw)}")
