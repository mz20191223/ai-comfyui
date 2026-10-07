# -*- coding: utf-8 -*-
"""14a 补入"多图接口（接口A）"备用填法——用户主力接口，与首尾帧专用接口二选一"""
import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DOC = r"D:\Aicomfyui\minimax3创作内容\deepseek分镜\第1集_中文视频提示词_核对版.md"

BLOCK = '''### 【备用】14a 走多图接口（接口A）时的填法

> 与上方首尾帧专用接口**二选一**。若你更习惯一直用的多图接口，按本节提交。
> prompt 主体不变，只改 3 处：

1. **首行加一句**（多图接口无模式开关，靠这句声明首尾帧）：
   `How the reference pictures align with the target video — Picture 1 (from Shot 1) aligns with the 0.00-second mark of the target video; Picture 2 (from Shot 1) aligns with the 4.00-second mark of the target video.`
2. **素材声明加两行**：
   - `Audio 1：权限魅影登场台词音色参考（阴冷低沉带气声：**呵呵呵呵……这么晚了，还不走？**——笑引子+带笑低语，一气呵成）`
   - `Image 3：过客_角色参考图_GPT版.jpg —— 仅用于锁定过客的发型、体型与衣着`
3. **硬约束④ 替换**为：
   `④ **本镜声音=Audio 1（音色与情绪严格按其生成）**——结构"笑引子+带笑低语"一体：先低沉带气声的"呵呵呵呵……"（1.2s 起），随即压成**"这么晚了，还不走？"**（2.2s 起），整段一气呵成、中间不断开、不拆成两段；此后不再出现任何其他人声；`
   并把 1.2–3.6 秒两段的"画面保持寂静无人声（后期叠加）"改回 `声音：**权限魅影（只闻其声，不见其人）："呵呵呵呵……"**` / `"这么晚了，还不走？"`。

**参数（多图接口）：**
```json
{
  "prompt": "（按上方 3 处改动后的 API prompt 整段）",
  "duration": 4,
  "resolution": "768p竖",
  "ref_audio_0": "第1集_镜头14a_权限魅影_这么晚了还不走.mp3",
  "ref_image_0": "0114a.jpg",
  "ref_image_1": "0114a_end.jpg",
  "ref_image_2": "过客_角色参考图_GPT版.jpg"
}
```
- ref_image_0=首帧、ref_image_1=尾帧（**靠首行对齐句生效，末帧不保证等于它**）、ref_image_2=过客形象锁定
- 本接口**有 ref_audio**，台词可由模型按音色生成进成片；若生成的人声不像或台词不准，仍走后期叠 mp3 兜底
- 多图接口能传 3 张图，所以 Image 3（过客角色参考）可以带上——这是它相对首尾帧专用接口的唯一优势

---

'''

t = open(DOC, encoding='utf-8').read()
anchor = '## 镜头14b｜'
i = t.find(anchor)
assert i != -1
# 回退到 anchor 之前的 '---\n\n'
pre = t.rfind('---\n\n', 0, i)
assert pre != -1
t = t[:pre] + BLOCK + t[pre:]
open(DOC, 'w', encoding='utf-8').write(t)
print('OK backup block inserted')
