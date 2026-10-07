"""给 frontend/src/api/index.js 加结构化出稿与按集提示词接口（带断言，兼容 CRLF）。"""
from __future__ import annotations

import io

P = r"D:\Aicomfyui\短剧工作台\frontend\src\api\index.js"
src = io.open(P, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in src else "\n"

anchor = "  previewEpisode: (pid, data) => http.post(`/projects/${pid}/scripts/preview-episode`, data)," + nl
assert src.count(anchor) == 1, ("锚点不唯一", src.count(anchor))

add = nl.join([
    "  // 结构化出稿：一次产出「集结构 + 每集镜头清单」（不含提示词）",
    "  generateOutline: (pid, data) => http.post(`/projects/${pid}/scripts/outline`, data),",
    "  previewOutline: (pid, data) => http.post(`/projects/${pid}/scripts/outline/preview`, data),",
    "  applyOutline: (pid, data) => http.post(`/projects/${pid}/scripts/apply-outline`, data),",
    "  // 按集出双份提示词（分镜图 + 视频），素材声明由工作台自动拼",
    "  shotList: (eid) => http.get(`/episodes/${eid}/shot-list`),",
    "  genShotPrompts: (eid, data) => http.post(`/episodes/${eid}/shot-prompts`, data || {}),",
    "  previewShotPrompts: (eid, data) => http.post(`/episodes/${eid}/shot-prompts/preview`, data || {}),",
    "  applyShotPrompts: (eid, data) => http.post(`/episodes/${eid}/shot-prompts/apply`, data),",
    "",
]) + nl

src = src.replace(anchor, anchor + add)
io.open(P, "w", encoding="utf-8", newline="").write(src)
got = io.open(P, encoding="utf-8", newline="").read()
for k in ("generateOutline", "previewOutline", "applyOutline", "shotList",
          "genShotPrompts", "previewShotPrompts", "applyShotPrompts"):
    assert got.count(k + ":") == 1, (k, got.count(k + ":"))
print("api/index.js 已加 7 个方法，换行符", repr(nl))
