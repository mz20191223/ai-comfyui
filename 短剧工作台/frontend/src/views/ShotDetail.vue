<template>
  <div v-if="data" class="detail">
    <!-- 顶部条 -->
    <div class="head">
      <el-button v-if="!embedded" size="small" text @click="$router.back()">
        <el-icon><ArrowLeft /></el-icon>
      </el-button>
      <b class="mono" style="font-size: var(--fs-lg)">{{ shot.shot_code }}</b>
      <span class="shot-title">{{ shot.title || '—' }}</span>
      <span v-if="data.task_state.has_running" class="pill run">
        <span class="dot run"></span>生成中 {{ data.task_state.max_progress }}%
      </span>
      <span class="tiny muted">
        {{ detail.gen_mode || '—' }} · {{ detail.duration_sec || '—' }}s · {{ detail.resolution || '—' }}
      </span>
      <span class="spacer" style="flex: 1"></span>
      <el-button size="small" @click="reload"><el-icon><Refresh /></el-icon></el-button>
    </div>

    <div class="cols">
      <!-- 左：分镜图 -->
      <section class="pane">
        <PromptEditor
          ref="imageEditor"
          :model-value="detail.image_prompt || ''"
          target-kind="shot_image"
          :target-id="sid"
          :wizard-note="note.image_note"
          @open-wizard="openWizard"
          @reload="reload"
          @saved="reload"
        >
          <template #title>
            <span class="pane-title">① 分镜图</span>
            <span class="tiny muted">{{ detail.image_target_name || '未命名' }}</span>
          </template>
          <template #tools>
            <el-button size="small" text @click="openWizard">镜头设置</el-button>
            <el-button size="small" type="primary" :loading="busy.image" @click="gen('image')">调用生图接口</el-button>
            <el-button size="small" @click="dry('image')">预览请求体</el-button>
            <el-button size="small" @click="reload">刷新</el-button>
          </template>
        </PromptEditor>

        <div class="mt12">
          <RefSlots :refs="imageRefs" :shot-id="sid" side="image" :project-id="pid" @changed="reload" />
        </div>

        <div v-if="tsImage && ['submitted', 'running'].includes(tsImage.status)" class="gen-run mt12">
          <span class="pill run">{{ tsImage.label }}</span>
          <el-progress :percentage="tsImage.progress || 0" :stroke-width="8" style="flex: 1" />
        </div>
        <div v-else-if="tsImage && tsImage.status === 'failed'" class="gen-fail mt12">
          出图失败：{{ tsImage.fail_label || '接口错误' }}<template v-if="tsImage.message && tsImage.message !== (tsImage.fail_label || '接口错误')"> · {{ tsImage.message }}</template>
        </div>

        <div v-if="imageOutputs.length" class="mt12">
          <div class="mb8" style="display: flex; align-items: center; justify-content: space-between; gap: 8px">
            <span class="tiny muted">分镜图候选 · 点图看大图（可左右翻看全部）</span>
            <el-button size="small" @click="pickKeyframeFile">更换分镜图</el-button>
          </div>
          <div class="thumb-grid">
            <div v-for="(f, i) in imageOutputs" :key="f.path" class="thumb">
              <div class="thumb-box">
                <img
                  :src="thumbUrl(f.path, 200)"
                  loading="lazy"
                  title="点击看大图"
                  @click="openPreview(i)"
                />
              </div>
              <div class="cap ellipsis">
                {{ f.path.split(/[\\/]/).pop() }}<span v-if="isKeyframe(f)" class="tiny muted"> · 正式版</span>
              </div>
              <div class="thumb-bar">
                <button
                  v-if="!isKeyframe(f)"
                  type="button"
                  :title="`设为分镜图：它会被改成正式名 ${detailFields.image_target_name || '本镜分镜图'}；现有正式版先存档为 _1，不会丢`"
                  @click.stop="setKeyframe(f.path)"
                >
                  <el-icon><Star /></el-icon>
                </button>
                <button type="button" title="传给视频：放到视频参考图第 1 张" @click.stop="adopt(f.path)">
                  <el-icon><VideoCamera /></el-icon>
                </button>
                <button type="button" class="del" title="废弃：移入项目「废弃产物」目录（磁盘移动，不删除）" @click.stop="discard(f.path)">
                  <el-icon><Delete /></el-icon>
                </button>
              </div>
            </div>
          </div>
          <input
            ref="kfFile"
            type="file"
            accept="image/png,image/jpeg,image/webp"
            style="display: none"
            @change="onKeyframeFile"
          />
        </div>

        <ElImageViewer
          v-if="previewIndex >= 0"
          :url-list="previewList"
          :initial-index="previewIndex"
          :hide-on-click-modal="true"
          teleported
          @close="previewIndex = -1"
        />

        <el-dialog
          v-model="ffDialog"
          title="选择尾帧作为视频首帧"
          width="760px"
          append-to-body
          @open="loadTailSources"
        >
          <div class="row mb8" style="align-items: center">
            <span class="tiny muted" style="white-space: nowrap">来源镜头</span>
            <el-select
              v-model="srcShotId" size="small" filterable
              placeholder="选一个本镜之前的镜头" style="width: 340px"
            >
              <el-option
                v-for="s in srcShots" :key="s.id" :value="s.id"
                :label="`${s.shot_code} ${s.title || ''}`"
              >
                <span>{{ s.shot_code }}</span>
                <span class="tiny muted" style="margin-left: 8px">{{ s.title }}</span>
                <span class="tiny muted" style="float: right">
                  {{ s.videos.length }} 成片 · {{ s.tails.length }} 尾帧
                </span>
              </el-option>
            </el-select>
          </div>

          <template v-if="srcShot">
            <div v-if="srcShot.tails.length" class="thumb-grid mb12">
              <div
                v-for="t in srcShot.tails" :key="t.path"
                class="thumb pick" :title="`设为首帧：${t.name}`"
                @click="useTailFromDialog(t.path)"
              >
                <div class="thumb-box"><img :src="thumbUrl(t.path, 200)" loading="lazy" /></div>
                <div class="cap ellipsis">{{ t.name }}</div>
              </div>
            </div>
            <div v-if="srcShot.videos.length" class="mb12">
              <div v-for="v in srcShot.videos" :key="v.path" class="vid-row">
                <span class="mono ellipsis" style="flex: 1">{{ v.name }}</span>
                <span class="tiny muted">{{ fmtSize(v.size_bytes) }}</span>
                <el-button
                  size="small" type="primary" plain
                  :loading="extracting === v.path"
                  @click="doExtractFrom(v.path)"
                >抽尾帧</el-button>
              </div>
            </div>
            <div v-else class="tiny muted mb12">
              这镜在分镜视频目录里没有命名匹配的成片（找不到 {{ srcShot.shot_code }} 对应的视频文件）。
            </div>
          </template>
          <div v-else class="tiny muted mb12">本镜之前还没有可选的镜头。</div>

          <template v-if="(tailSources.other_tails || []).length">
            <div class="tiny muted mb8">尾帧目录里的其它尾帧 · 点图即设为首帧</div>
            <div class="thumb-grid mb12" style="max-height: 190px; overflow: auto">
              <div
                v-for="t in tailSources.other_tails" :key="t.path"
                class="thumb pick" :title="`设为首帧：${t.name}`"
                @click="useTailFromDialog(t.path)"
              >
                <div class="thumb-box"><img :src="thumbUrl(t.path, 200)" loading="lazy" /></div>
                <div class="cap ellipsis">{{ t.name }}</div>
              </div>
            </div>
          </template>

          <div v-if="tailSources.tail_dir" class="tiny muted mb8">
            尾帧落盘目录：<span class="mono">{{ tailSources.tail_dir }}</span>
            <span v-if="!tailSources.tail_dir_exists" style="color: #dc2626">
              · 目录不存在，请到项目设置里检查
            </span>
          </div>

          <div class="mt12">
            <el-button size="small" @click="pickFirstFrameLocal">从本地上传一张图</el-button>
            <span class="tiny muted" style="margin-left: 8px">存进本项目的分镜图目录，来源记作「手动上传」</span>
          </div>
          <template #footer>
            <el-button @click="ffDialog = false">关闭</el-button>
          </template>
        </el-dialog>
      </section>

      <!-- 中：视频 -->
      <section class="pane">
        <PromptEditor
          ref="videoEditor"
          v-model="videoPrompt"
          target-kind="shot_video"
          :target-id="sid"
          :wizard-note="note.video_note"
          @open-wizard="openWizard"
          @reload="reload"
          @saved="reload"
        >
          <template #title>
            <span class="pane-title">② 视频</span>
          </template>
          <template #tools>
            <el-button size="small" type="success" :loading="busy.video" @click="gen('video')">调用视频模型</el-button>
            <el-button size="small" @click="dry('video')">预览请求体</el-button>
            <el-dropdown size="small" @command="onVideoCmd">
              <el-button size="small">更多<el-icon><ArrowDown /></el-icon></el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="force">跳过素材校验强制生成</el-dropdown-item>
                  <el-dropdown-item command="tail">抽尾帧并回填下一镜</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </PromptEditor>

        <input ref="ffInput" type="file" accept="image/*" style="display: none" @change="onFirstFrameFile" />

        <div class="mt12">
          <div class="tiny muted mb8">视频参考图</div>
          <RefSlots :refs="videoRefs" :shot-id="sid" side="video" :project-id="pid" @changed="reload" @pick-first="openFfDialog">
            <template #first-ops>
              <button type="button" title="选择上一镜尾帧作为首帧" @click.stop="openFfDialog">
                <el-icon><Download /></el-icon>
              </button>
            </template>
          </RefSlots>
        </div>

        <div class="row mt12 vid-params">
          <div class="pf">
            <div class="pf-label">时长（秒）</div>
            <el-input-number v-model="detailFields.duration_sec" :min="1" :max="30" size="small"
              controls-position="right" style="width: 118px" @change="saveDetailField('duration_sec', detailFields.duration_sec)" />
          </div>
          <div class="pf">
            <div class="pf-label">分辨率</div>
            <el-input v-model="detailFields.resolution" size="small" style="width: 130px"
              @change="saveDetailField('resolution', detailFields.resolution)" placeholder="768p竖" />
          </div>
          <div class="pf">
            <div class="pf-label">seed（可空）</div>
            <el-input-number v-model="detailFields.seed" :controls="false" :precision="0" :min="0" size="small"
              style="width: 150px" placeholder="空＝每次重新随机"
              @change="saveDetailField('seed', detailFields.seed)" />
          </div>
        </div>
        <div class="tiny muted mt8">
          这三个会原样写进视频请求体（点「预览请求体」可核对）：分辨率留空则用项目默认；
          seed 留空＝每次都重新随机，填了就固定复现同一版。
        </div>

        <div v-if="tsVideo && ['submitted', 'running'].includes(tsVideo.status)" class="gen-run mt12">
          <span class="pill run">{{ tsVideo.label }}</span>
          <el-progress :percentage="tsVideo.progress || 0" :stroke-width="8" style="flex: 1" />
        </div>
        <div v-else-if="tsVideo && tsVideo.status === 'failed'" class="gen-fail mt12">
          出片失败：{{ tsVideo.fail_label || '接口错误' }}<template v-if="tsVideo.message && tsVideo.message !== (tsVideo.fail_label || '接口错误')"> · {{ tsVideo.message }}</template>
        </div>

        <div v-if="videoOutputs.length" class="mt12">
          <div class="tiny muted mb8">
            成片产物（{{ videoOutputs.length }} 条）
            <template v-if="pinnedVideo"> · 已指定：{{ baseName(pinnedVideo) }}</template>
            <template v-else> · 未指定，合成时自动挑</template>
          </div>
          <div class="vid-strip">
            <div v-for="f in videoOutputs" :key="f.path" class="vid-item">
              <div class="vid-box">
                <video :src="fileUrl(f.path)" controls preload="metadata"></video>
                <span v-if="f.is_final" class="vid-badge final">成片</span>
                <span v-else-if="f.source === 'dir'" class="vid-badge">目录</span>
              </div>
              <div class="tiny muted vid-path ellipsis" :title="f.path">{{ f.path }}</div>
              <!-- 操作跟「视频参考图」区同一套：22x22 小图标按钮，用途写在 title 里 -->
              <div class="vid-btns">
                <button v-if="f.pending" type="button" title="归档到分镜视频（顺手定为本镜成片）"
                  @click="acceptOutput(f.path)">
                  <el-icon><FolderAdd /></el-icon>
                </button>
                <button type="button" :class="{ on: f.is_final }"
                  :title="f.is_final ? '取消指定（合成回到自动挑片）' : '设为成片（合成固定用这条）'"
                  @click="toggleFinalVideo(f)">
                  <el-icon><StarFilled v-if="f.is_final" /><Star v-else /></el-icon>
                </button>
                <button type="button" title="抽尾帧并回填下一镜" @click="doExtractTail(f.path)">
                  <el-icon><Camera /></el-icon>
                </button>
                <button type="button" title="复制完整路径" @click="copyPath(f.path)">
                  <el-icon><DocumentCopy /></el-icon>
                </button>
                <button type="button" class="del" title="废弃（移入项目废弃产物目录，不删除）"
                  @click="discard(f.path)">
                  <el-icon><Delete /></el-icon>
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- 右：音频 / 校验 / 参数 -->
      <section class="pane">
        <div class="pane-head">
          <span>③ 音频与校验</span>
          <span class="spacer" style="flex:1"></span>
          <span v-if="audioReadyCount" class="pill brand">
            {{ audioReadyCount }} 段 · {{ audioTotalSec }}s
          </span>
        </div>

        <div v-if="!audioLines.length" class="card" style="margin:0 0 10px">
          <div class="tiny muted">本镜无台词</div>
          <div class="mt8">
            <el-button size="small" type="primary" @click="pickAudio(null)">
              选择音频文件
            </el-button>
          </div>
        </div>

        <div v-for="(ln, i) in audioLines" :key="ln.id" class="card" style="margin:0 0 10px">
          <div class="audio-head">
            <span class="pill brand mono">ref_audio_{{ i }}</span>
            <span class="tiny muted">{{ ln.role_name || '—' }}</span>
          </div>
          <div class="kv">
            <div class="k">台词</div><div class="v">「{{ ln.text || '（未填台词）' }}」</div>
            <div class="k">文件</div><div class="v mono tiny">{{ ln.audio_file || '（未挂音频）' }}</div>
            <div class="k">实测时长</div><div class="v">{{ ln.audio_measured_sec ?? '—' }} s</div>
            <div class="k">台词窗口</div>
            <div class="v">{{ ln.start_sec ?? '—' }} → {{ ln.end_sec ?? '—' }} s</div>
          </div>
          <div v-if="lineMissing(ln)" class="tiny mt8" style="color:#dc2626">
            ⚠ 这个文件找不到，请重新挂上音频
          </div>
          <audio
            v-if="ln.audio_resolved_path"
            :src="fileUrl(ln.audio_resolved_path)"
            controls
            style="width:100%;margin-top:8px"
          ></audio>
          <div class="mt8">
            <el-button size="small" type="primary" @click="pickAudio(ln)">
              {{ lineReady(ln) ? '更换音频' : '选择音频文件' }}
            </el-button>
            <el-button v-if="ln.audio_file" size="small" @click="clearAudio(ln)">
              摘掉音频
            </el-button>
            <el-button size="small" type="danger" plain @click="deleteLine(ln)">
              删除该段
            </el-button>
          </div>
        </div>

        <div class="card" style="margin:0 0 10px">
          <div>
            <el-button size="small" @click="doAudit">校验时长</el-button>
          </div>
          <div class="tiny muted mt8">
            音频在外部做好后挂到这里。本镜共 {{ audioReadyCount }} 段已挂音频，出片时会按顺序作为
            <span class="mono">ref_audio_0{{ audioReadyCount > 1 ? '、ref_audio_1…' : '' }}</span>
            交给视频模型（接口支持多段参考音频，一段音频一个槽）。
          </div>
          <div v-if="auditRows.length" class="mt8 tiny">
            <div v-for="(r, i) in auditRows" :key="i">
              <span class="mono">{{ r.ref }}</span>
              <span v-if="!r.exists" style="color:#dc2626"> ✗ 文件不存在：{{ r.file }}</span>
              <span v-else-if="r.short" style="color:#dc2626">
                ✗ 时长不足：可用 {{ r.span }}s ＜ 音频 {{ r.measured }}s
              </span>
              <span v-else style="color:#16a34a"> ✓ {{ r.measured }}s，窗口够用</span>
            </div>
          </div>
          <div v-if="auditProblems.length" class="mt8 tiny">
            <div v-for="(p, i) in auditProblems" :key="i" style="color:#dc2626">
              {{ p.message }} <span class="muted" v-if="p.suggestion">→ {{ p.suggestion }}</span>
            </div>
          </div>
        </div>

        <MediaPicker v-model="audioPicker" :project-id="pid" kind="audio" @picked="onAudioPicked" />

        <div class="card" style="margin:0">
          <h3>原始信息</h3>
          <div class="kv">
            <div class="k">集</div><div class="v">第 {{ data.episode.number }} 集</div>
            <div class="k">镜号</div><div class="v mono">{{ shot.shot_code }}</div>
            <div class="k">备注</div><div class="v tiny">{{ shot.notes || '—' }}</div>
          </div>
          <div v-if="data.issues.length" class="mt8">
            <div v-for="(i, k) in data.issues" :key="k" class="lint-item" :class="i.severity">
              <div class="msg">{{ i.message }}</div>
            </div>
          </div>
        </div>
      </section>
    </div>


    <el-dialog v-model="showWizard" title="镜头设置" width="760px" append-to-body>
      <div class="wz-body">
            <div class="wz-row">
              <span class="wz-label">景别</span>
              <el-select v-model="wiz.camera_shot" size="small" placeholder="未选" style="width:112px" clearable>
                <el-option v-for="o in opts.camera_shot" :key="o.value" :label="o.label" :value="o.value">
                  <span class="opt-row">
                    <img class="opt-img" :src="diagramUrl('size', o.value)" alt="" />
                    <span>{{ o.label }}</span>
                  </span>
                </el-option>
              </el-select>
              <span class="wz-label">视角</span>
              <el-select v-model="wiz.angle" size="small" placeholder="未选" style="width:118px" clearable>
                <el-option v-for="o in opts.angle" :key="o.value" :label="o.label" :value="o.value">
                  <span class="opt-row">
                    <img class="opt-img" :src="diagramUrl('angle', o.value)" alt="" />
                    <span>{{ o.label }}</span>
                  </span>
                </el-option>
              </el-select>
              <span class="wz-label">运镜</span>
              <el-select v-model="wiz.movement" size="small" placeholder="未选" style="width:110px" clearable>
                <el-option v-for="o in opts.movement" :key="o.value" :label="o.label" :value="o.value">
                  <span class="opt-row">
                    <MoveDiagram :movement="o.value" :w="20" :h="36" />
                    <span>{{ o.label }}</span>
                  </span>
                </el-option>
              </el-select>
            </div>

            <div class="wz-row" style="margin-top:8px">
              <span class="wz-label">主体位置</span>
              <div class="pos-grid">
                <button
                  v-for="o in opts.subject_position" :key="o.value" type="button"
                  class="pos-cell" :class="{ on: wiz.pos === o.value }"
                  @click="wiz.pos = wiz.pos === o.value ? '' : o.value"
                >{{ o.label }}</button>
              </div>
              <el-select v-model="wiz.dist" size="small" placeholder="远近" style="width:88px" clearable>
                <el-option v-for="o in opts.subject_distance" :key="o.value" :label="o.label" :value="o.value" />
              </el-select>
            </div>

            <div class="wz-preview">
              <div class="wz-figs">
                <figure v-if="wiz.camera_shot" class="wz-fig">
                  <img :src="diagramUrl('size', wiz.camera_shot)" alt="" />
                  <figcaption>{{ labelOf('camera_shot', wiz.camera_shot) }}</figcaption>
                </figure>
                <figure v-if="wiz.angle" class="wz-fig">
                  <img :src="diagramUrl('angle', wiz.angle)" alt="" />
                  <figcaption>{{ labelOf('angle', wiz.angle) }}</figcaption>
                </figure>
                <figure v-if="wiz.movement" class="wz-fig">
                  <MoveDiagram :movement="wiz.movement" :w="72" :h="128" />
                  <figcaption>{{ labelOf('movement', wiz.movement) }}</figcaption>
                </figure>
                <div v-if="!wiz.camera_shot && !wiz.angle && !wiz.movement" class="wz-fig-empty">
                  选景别 / 视角 / 运镜看示意图
                </div>
              </div>
              <div class="wz-out">
                <div class="wz-line">
                  <span class="wz-tag">分镜图</span>
                  <span class="mono">{{ note.image_note || '—' }}</span>
                </div>
                <div class="wz-line">
                  <span class="wz-tag move">视频</span>
                  <span class="mono">{{ note.video_note || '—' }}</span>
                </div>
                <div class="tiny muted" style="margin-top:6px">
                  景别/视角/运镜三张示意图：景别与视角是生成图，运镜是俯视机位示意图。
                  点「写入并注入提示词」后，分镜图句自动进 image_prompt、机位运镜句自动进 video_prompt。
                  重复写入会替换上次那句，不会往下堆。
                </div>
              </div>
            </div>

            <div class="actions" style="margin-top:8px">
              <el-button size="small" type="primary" @click="saveWizard">写入并注入提示词</el-button>
              <el-button size="small" text @click="resetWizard">清空选择</el-button>
              <span v-if="lastApply" class="tiny muted" style="margin-left:6px">{{ lastApply }}</span>
            </div>

            <div v-if="mvWarn.pending" class="wz-warn">
              <div>
                <b>运镜没写进视频提示词。</b>
                正文里已经有一句手写的运镜，避免同一份提示词出现两个互相矛盾的运镜，我没有动它。
              </div>
              <div class="mono tiny" style="margin-top:4px">已有：{{ mvWarn.existing }}</div>
              <div class="mono tiny">待并入：{{ mvWarn.pending }}</div>
              <el-button size="small" text @click="copyPending">复制待并入的运镜句</el-button>
            </div>
      </div>
    </el-dialog>

    <el-dialog v-model="showDry" title="请求体预览（未真正发送）" width="760px" append-to-body>
      <div class="tiny muted mb8">
        按编辑器里当前的文本渲染（含未保存的改动）。真正生成时用的是最后一次「保存」的内容。
      </div>
      <pre class="prompt" style="max-height: 520px">{{ dryJson }}</pre>
    </el-dialog>
  </div>
  <div v-else class="empty">加载中…</div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox, ElImageViewer } from 'element-plus'
import { Camera, Delete, DocumentCopy, Download, FolderAdd, Star, StarFilled, VideoCamera } from '@element-plus/icons-vue'
import { api, fileUrl, thumbUrl } from '../api'
import PromptEditor from '../components/PromptEditor.vue'
import RefSlots from '../components/RefSlots.vue'
import MediaPicker from '../components/MediaPicker.vue'
import MoveDiagram from '../components/MoveDiagram.vue'

// 既能当独立页面用（从路由取 pid/sid），也能被看板以弹窗形式内嵌（传 props）
const props = defineProps({
  shotId: { type: Number, default: 0 },
  projectId: { type: Number, default: 0 },
  embedded: { type: Boolean, default: false },
})

const route = useRoute()
const pid = props.projectId || Number(route.params.pid)
const sid = props.shotId || Number(route.params.sid)

const data = ref(null)
const detailFields = ref({})
const busy = ref({ image: false, video: false })
const auditResult = ref(null)
const showDry = ref(false)
const dryJson = ref('')
const imageEditor = ref(null)
const videoEditor = ref(null)
const audioPicker = ref(false)
// 这次选的音频要挂给哪一行台词（null = 本镜还没有台词行，后端会新建一行）
const pickLineId = ref(null)
let timer = null

const shot = computed(() => data.value?.shot || {})
const detail = computed(() => data.value?.detail || {})
const imageRefs = computed(() => data.value?.image_refs || [])
const videoRefs = computed(() => data.value?.video_refs || [])
// 一个镜头可挂多段音频：每条台词行 = 一段参考音频，按行序依次为 ref_audio_0/1/…
const audioLines = computed(() => data.value?.dialog_lines || [])
const audioTotalSec = computed(
  () =>
    Math.round(audioLines.value.reduce((s, l) => s + (l.audio_measured_sec || 0), 0) * 1000) / 1000,
)
// 已挂音频的段数（= 出片时实际会作为 ref_audio 传出去的条数）
const audioReadyCount = computed(() => audioLines.value.filter((l) => l.audio_file).length)
// 该行音频是否真的落盘可用（决定按钮说「选择」还是「更换」）
function lineReady(ln) {
  return !!ln?.audio_file && !!ln?.audio_exists
}
function lineMissing(ln) {
  return !!ln?.audio_file && !ln?.audio_exists
}
// 校验结果按行展开：ref_audio_N 的序号由台词行顺序决定，不自己另编
const auditRows = computed(() => {
  const list = auditResult.value?.audios || []
  const dur = detail.value.duration_sec
  return list.map((a) => {
    const idx = audioLines.value.findIndex((l) => l.id === a.line_id)
    const span =
      a.measured_sec != null && dur ? Math.round((dur - (a.start_sec ?? 0)) * 1000) / 1000 : null
    return {
      ref: idx >= 0 ? `ref_audio_${idx}` : `行 ${a.line_id}`,
      file: a.file,
      exists: a.exists,
      measured: a.measured_sec,
      span,
      short: span != null && a.measured_sec != null && span < a.measured_sec,
    }
  })
})
const auditProblems = computed(() => auditResult.value?.problems || [])
const tasks = computed(() => data.value?.tasks || [])
const issues = computed(() => data.value?.issues || [])

const imagePrompt = computed({
  get: () => detail.value.image_prompt || '',
  set: () => {},
})
const videoPrompt = computed({
  get: () => detail.value.video_prompt || '',
  set: () => {},
})

// 以下音频状态已按行处理，见上方 audioLines / lineReady / lineMissing

// ---- 镜头设置向导 ----
const opts = ref({})
const showWizard = ref(false)
const wiz = reactive({ angle: '', camera_shot: '', pos: '', dist: '', movement: '' })
// 后端返回的「将要注入的句子」——措辞的唯一事实源在 wizard_service，前端不自己拼
const note = ref({ image_note: '', video_note: '' })
const lastApply = ref('')
// 正文里有手写运镜时的提醒（不覆盖手写内容）
const mvWarn = ref({ pending: '', existing: '' })

function labelOf(group, value) {
  if (!value) return ''
  const hit = (opts.value[group] || []).find((o) => o.value === value)
  return hit ? hit.label : value
}

// 示意图：景别 size_XX / 视角 angle_XX（Agnes 生成 → WebP 瘦身，放 public/shot-diagrams）
// 原图在 assets-src/shot-diagrams；WebP 比同尺寸 PNG 小约 10 倍（8.2MB → 0.17MB）
function diagramUrl(kind, value) {
  if (!value) return ''
  return `/shot-diagrams/${kind}_${value}.webp`
}

let noteSeq = 0
async function refreshNote() {
  const seq = ++noteSeq
  try {
    const r = await api.wizardNote(sid, {
      camera_shot: wiz.camera_shot || '',
      angle: wiz.angle || '',
      movement: wiz.movement || '',
      subject_position: wiz.pos ? (wiz.dist ? `${wiz.pos}·${wiz.dist}` : wiz.pos) : '',
    })
    if (seq === noteSeq) note.value = r
  } catch (e) {
    /* 忽略：预览失败不影响写入 */
  }
}

watch(() => [wiz.camera_shot, wiz.angle, wiz.movement, wiz.pos, wiz.dist], refreshNote)

const cameraLine = computed(() => detail.value.camera_note || '')

function resetWizard() {
  wiz.angle = ''
  wiz.camera_shot = ''
  wiz.pos = ''
  wiz.dist = ''
  wiz.movement = ''
  lastApply.value = ''
  mvWarn.value = { pending: '', existing: '' }
  refreshNote()
}

function copyPending() {
  if (!mvWarn.value.pending) return
  navigator.clipboard.writeText(mvWarn.value.pending)
  ElMessage.success('已复制，粘到视频提示词里替换或合并那句手写运镜')
}

function openWizard() {
  syncWizardFromDetail()
  refreshNote()
  showWizard.value = true
}

const ACTION_TXT = { inserted: '已插入', replaced: '已替换上次那句', removed: '已移除上次那句', unchanged: '无变化' }

async function saveWizard() {
  if (!wiz.camera_shot && !wiz.angle) return ElMessage.warning('至少选一个景别或视角')
  const r = await api.applyWizard(sid, {
    camera_shot: wiz.camera_shot || '',
    angle: wiz.angle || '',
    movement: wiz.movement || '',
    subject_position: wiz.pos ? (wiz.dist ? `${wiz.pos}·${wiz.dist}` : wiz.pos) : '',
  })
  note.value = { image_note: r.image.note, video_note: r.video.note }
  mvWarn.value = {
    pending: r.video.pending_movement || '',
    existing: r.video.existing_movement || '',
  }
  lastApply.value = `分镜图 ${ACTION_TXT[r.image.action] || r.image.action}；视频 ${ACTION_TXT[r.video.action] || r.video.action}`
  if (mvWarn.value.pending) {
    ElMessage.warning('已注入机位句；视频正文里已有手写运镜，运镜句没有自动写入，请看下方提醒')
  } else if (r.image.size_mentions && r.image.size_mentions.length) {
    ElMessage.warning(`已注入。提醒：分镜图正文里本来就写有「${r.image.size_mentions.join('、')}」，请核对是否和新写入的景别冲突`)
  } else {
    ElMessage.success('已写入镜头字段，并注入两份提示词')
  }
  await reload()
}


// ---- 视频首帧（ref_image_0）：选择尾帧作首帧的弹层 ----
// 入口是参考图第 1 张下方的小图标。弹层先选「来源镜头」（只列本镜之前的），
// 该镜已有尾帧就点图直接用；没抽过就用它的成片现抽一张，抽完直接回填本镜首帧。
const tailInfo = ref({})
const ffDialog = ref(false)
const tailSources = ref({})
const srcShotId = ref(null)
const extracting = ref('')

const srcShots = computed(() => tailSources.value.shots || [])
const srcShot = computed(() => srcShots.value.find((s) => s.id === srcShotId.value) || null)

function openFfDialog() {
  ffDialog.value = true
}

async function loadTailSources() {
  try {
    const d = await api.tailSources(sid)
    tailSources.value = d || {}
    const list = d?.shots || []
    // 默认停在上一镜；已选过且仍在列表里就保留用户的选择
    const keep = list.find((s) => s.id === srcShotId.value)
    srcShotId.value = keep ? keep.id : (d?.prev_shot_id || list[0]?.id || null)
  } catch (e) {
    tailSources.value = {}
    srcShotId.value = null
  }
}

function fmtSize(n) {
  if (!n) return ''
  return n >= 1048576 ? `${(n / 1048576).toFixed(1)} MB` : `${Math.round(n / 1024)} KB`
}

async function doExtractFrom(videoPath) {
  const s = srcShot.value
  if (!s) return
  extracting.value = videoPath
  try {
    const r = await api.extractTailFrom(sid, { source_shot_id: s.id, video_path: videoPath })
    ElMessage.success(`已抽好尾帧并设为本镜视频首帧：${r.file_name}`)
    ffDialog.value = false
    await reload()
  } catch (e) {
    /* 已提示 */
  } finally {
    extracting.value = ''
  }
}

async function useTailFromDialog(path) {
  ffDialog.value = false
  await onUseTail(path)
}

async function onUseTail(path) {
  if (!path) return
  const name = String(path).split(/[\\/]/).pop()
  const cur = tailInfo.value.current
  try {
    await ElMessageBox.confirm(
      `把「${name}」设为本镜首帧？` +
        (cur && cur.file_name ? `\n会覆盖当前的 ref_image_0：${cur.file_name}` : ''),
      '确认', { type: 'warning' },
    )
  } catch {
    return
  }
  try {
    const r = await api.usePrevTail(sid, { path, prev_shot_code: tailInfo.value.prev?.shot_code })
    ElMessage.success(`已设为首帧：${r.file_name}`)
  } finally {
    await reload()
  }
}

// ---- 首帧：自己上传一张图（不等生成；来源可以是任何地方）----
const ffInput = ref(null)

function pickFirstFrameLocal() {
  ffInput.value.value = ''
  ffInput.value.click()
}

async function onFirstFrameFile(e) {
  const f = e.target.files && e.target.files[0]
  if (!f) return
  if (!/^image\//.test(f.type || '')) {
    ElMessage.warning('首帧只支持图片文件（jpg / png / webp）')
    if (ffInput.value) ffInput.value.value = ''
    return
  }
  const cur = tailInfo.value.current
  const fd = new FormData()
  fd.append('file', f, f.name)
  try {
    if (cur && cur.file_name) {
      await ElMessageBox.confirm(
        `把「${f.name}」设为本镜视频首帧？\n会覆盖当前的 ref_image_0：${cur.file_name}`,
        '确认', { type: 'warning' },
      )
    }
    const r = await api.uploadFirstFrame(sid, fd)
    ElMessage.success(`已上传并设为首帧：${r.file_name}`)
    ffDialog.value = false
  } catch (err) {
    /* 用户取消或已提示 */
  } finally {
    if (ffInput.value) ffInput.value.value = ''
    await reload()
  }
}

// 分镜图目录里属于本镜的图（正式名 + _1/_2 存档）：手动放进目录的、被「更换/采用」
// 顶下来存档的，任务结果里都不会有，靠目录扫描补齐（后端 keyframe-candidates）。
const dirKeyframes = ref([])
const kfFile = ref(null)

function normPath(p) {
  return String(p || '').split('\\').join('/').toLowerCase()
}

// 候选 = 任务生成结果 ∪ 目录扫描，按路径合并去重
const imageOutputs = computed(() => {
  const out = outputsOf('image_generation')
  const seen = new Set(out.map((x) => normPath(x.path)))
  for (const f of dirKeyframes.value) {
    if (!f.path || seen.has(normPath(f.path))) continue
    seen.add(normPath(f.path))
    out.push(f)
  }
  return out
})
// 成片候选：后端把「任务产物 ∪ 分镜视频目录」合并好，并标出哪条是当前指定的成片
const videoCand = ref([])
const pinnedVideo = ref('')
const videoOutputs = computed(() => videoCand.value)
const tsImage = computed(() => data.value?.task_state?.image)
const tsVideo = computed(() => data.value?.task_state?.video)

// 分镜图候选大图预览
const previewIndex = ref(-1)
const previewList = computed(() => imageOutputs.value.map((f) => fileUrl(f.path)))
function openPreview(i) {
  previewIndex.value = i
}

// 成片产物只收视频、分镜图候选只收图片：任务结果里偶尔会混进同一份产物的另一条
// 登记（接口A 的 result_images 与 result_videos 是同一个 jsonpath，同一段视频会
// 被登记成 image + video 两条），只按后缀过滤，同一段视频就不会出现两次。
const VIDEO_EXT_RE = /\.(mp4|mov|webm|mkv|avi)$/i
const IMAGE_EXT_RE = /\.(jpg|jpeg|png|webp|gif|bmp)$/i

function outputsOf(kind) {
  const wantVideo = kind === 'video_generation'
  const out = []
  for (const t of tasks.value) {
    if (t.task_kind !== kind || t.status !== 'succeeded') continue
    const res = typeof t.result === 'string' ? safeJson(t.result) : t.result
    for (const f of res?.files || []) {
      if (!f.path || f.discarded || out.find((x) => x.path === f.path)) continue
      if (wantVideo ? !VIDEO_EXT_RE.test(f.path) : !IMAGE_EXT_RE.test(f.path)) continue
      out.push(f)
    }
  }
  return out
}
function safeJson(s) {
  try { return JSON.parse(s) } catch { return null }
}

function syncWizardFromDetail() {
  const d = detail.value || {}
  const sp = d.subject_position || ''
  const [pos, dist] = sp.includes('·') ? sp.split('·') : [sp, '']
  wiz.angle = d.angle || ''
  wiz.camera_shot = d.camera_shot || ''
  wiz.pos = pos || ''
  wiz.dist = dist || ''
  wiz.movement = d.movement || ''
  refreshNote()
}

async function reload() {
  data.value = await api.shot(sid)
  detailFields.value = {
    duration_sec: data.value.detail.duration_sec,
    resolution: data.value.detail.resolution,
    seed: data.value.detail.seed,
    gen_mode: data.value.detail.gen_mode,
    image_target_name: data.value.detail.image_target_name,
  }
  // 向导展开时不动用户的选择，避免 5s 轮询把没保存的输入冲掉
  if (!showWizard.value) syncWizardFromDetail()
  try {
    tailInfo.value = await api.prevTailCandidates(sid)
  } catch (e) {
    tailInfo.value = {}
  }
  // 目录里属于本镜的图（正式名 + _1/_2 存档）
  try {
    dirKeyframes.value = (await api.keyframeCandidates(sid)).items || []
  } catch (e) {
    dirKeyframes.value = []
  }
  // 成片候选（任务产物 ∪ 目录里的重出/归档变体）与当前指定的成片
  try {
    const vc = await api.videoCandidates(sid)
    videoCand.value = vc.candidates || []
    pinnedVideo.value = vc.final_video_path || ''
  } catch (e) {
    videoCand.value = []
    pinnedVideo.value = ''
  }
}

async function saveDetailField(k, v) {
  await api.patchShot(sid, { detail: { [k]: v } })
  ElMessage.success('已保存')
}

async function gen(kind) {
  busy.value[kind] = true
  try {
    await api.generate(sid, { kind })
    ElMessage.success('任务已提交，进度见任务中心')
    setTimeout(reload, 1500)
  } catch (e) {
    /* 已提示 */
  } finally {
    busy.value[kind] = false
  }
}

async function dry(kind) {
  // 预览按「编辑器里此刻的文本」渲染（含尚未保存的改动）；
  // 否则你刚录进去的文案还没保存，预览读的是库里的旧值，看着就像"没带上"。
  const editor = kind === 'image' ? imageEditor.value : videoEditor.value
  const draft = editor?.currentText?.()
  const payload = { kind }
  if (typeof draft === 'string') payload.overrides = { prompt: draft }
  const r = await api.dryRun(sid, payload)
  dryJson.value = JSON.stringify(r.preview, null, 2)
  showDry.value = true
}

function pickAudio(ln) {
  pickLineId.value = ln?.id ?? null
  audioPicker.value = true
}

async function onAudioPicked(path) {
  try {
    const payload = { file_name: path }
    if (pickLineId.value) payload.line_id = pickLineId.value
    const r = await api.setShotAudio(sid, payload)
    const sec = r.measured_sec ? `实测 ${r.measured_sec}s` : '未能测出时长'
    ElMessage.success(`已挂上音频（${sec}）`)
    auditResult.value = r.audit || null
    await reload()
  } catch (e) {
    /* 已提示 */
  } finally {
    pickLineId.value = null
  }
}

async function clearAudio(ln) {
  const tip = ln?.text ? `摘掉「${ln.text}」这一段的音频？` : '摘掉本镜的音频素材？'
  await ElMessageBox.confirm(tip, '确认', { type: 'warning' })
  await api.clearShotAudio(sid, ln?.id)
  auditResult.value = null
  ElMessage.success(ln?.text ? '已摘掉这一段音频' : '已摘掉音频')
  reload()
}

// 删除一整段音频槽（连同该行台词；重新导入 md 可恢复）——用来把多段收敛成一段
async function deleteLine(ln) {
  const tip = ln?.text ? `删除「${ln.text}」这一整段音频槽？` : '删除这一整段音频槽？'
  await ElMessageBox.confirm(tip, '确认', { type: 'warning' })
  await api.deleteDialogLine(sid, ln.id)
  auditResult.value = null
  ElMessage.success('已删除该段')
  reload()
}

// 分镜图正式名（image_target_name，如 0114d.jpg）＝本镜「正式分镜图」，被视频首帧锚点
// 和提示词文档按文件名引用。候选区里文件名与它不同的是备用/存档版本，可以顶上去当正式版。
function baseName(p) {
  return String(p || '').split(/[\\/]/).pop()
}

function isKeyframe(f) {
  const want = String(detailFields.value.image_target_name || '').trim().toLowerCase()
  if (!want) return false
  return String(f.path || '').split(/[\\/]/).pop().toLowerCase() === want
}

async function setKeyframe(path) {
  const want = detailFields.value.image_target_name || '本镜分镜图'
  try {
    await ElMessageBox.confirm(
      `把「${baseName(path)}」设为正式分镜图？\n` +
      `会把它改成正式名 ${want}（下游引用不变）；现有正式版先存档为 _1，不会丢。`,
      '确认', { type: 'warning' },
    )
  } catch {
    return
  }
  const r = await api.setKeyframe(sid, path)
  ElMessage.success(
    r.archived_path ? `已采用；旧版存档为 ${baseName(r.archived_path)}` : '已采用为本镜正式分镜图',
  )
  reload()
}

// 更换正式分镜图：选本机的一张图灌进正式名（旧版自动存档 _1，不丢）
function pickKeyframeFile() {
  kfFile.value?.click()
}

async function onKeyframeFile(e) {
  const f = e.target.files && e.target.files[0]
  e.target.value = '' // 清空，同一个文件还能再选一次
  if (!f) return
  const want = detailFields.value.image_target_name || '本镜分镜图'
  try {
    await ElMessageBox.confirm(
      `用「${f.name}」替换正式分镜图 ${want}？\n` +
        '现有正式版会先存档为 _1（不会丢）；下游引用（视频首帧锚点、提示词里的文件名）保持不变。',
      '确认',
      { type: 'warning' },
    )
  } catch {
    return
  }
  const fd = new FormData()
  fd.append('file', f)
  const r = await api.replaceKeyframe(sid, fd)
  const tail = r.converted ? `（已按正式名格式转成 ${r.format_out}）` : ''
  ElMessage.success(
    r.archived_path
      ? `已替换；旧版存档为 ${baseName(r.archived_path)}${tail}`
      : `已替换为本镜正式分镜图${tail}`,
  )
  reload()
}

async function adopt(path) {
  await api.adoptImage(sid, { path, as_first_frame: true })
  ElMessage.success('已传给视频：它现在是右侧「视频参考图」的第 1 张')
  reload()
}

// 指定/取消本镜成片：合成按它取片（时间轴上手动换过的片段优先于它）
async function toggleFinalVideo(f) {
  const clearing = !!f.is_final
  await api.setFinalVideo(sid, clearing ? null : f.path)
  ElMessage.success(
    clearing ? '已取消指定，合成回到自动挑片' : `已设为本镜成片：${f.name || baseName(f.path)}`,
  )
  reload()
}

// 归档＝把它从工作台暂存区移进项目「分镜视频」，服务端顺手定为本镜成片
async function acceptOutput(path) {
  const r = await api.acceptOutput(sid, path)
  ElMessage.success(`已归档到分镜视频：${r.new_path.split(/[\\/]/).pop()}`)
  reload()
}

async function discard(path) {
  await ElMessageBox.confirm('把该产物移入项目「废弃产物」目录？（磁盘移动，不删除，可手动找回）', '确认', { type: 'warning' })
  const r = await api.discardOutput(sid, path)
  ElMessage.success(`已移入废弃目录：${r.new_path}`)
  reload()
}

async function doExtractTail(path) {
  const r = await api.extractTail(sid, { video_path: path, link_to_next: true })
  ElMessage.success(`尾帧已落盘：${r.tail_path.split(/[\\/]/).pop()}`)
  reload()
}

async function onVideoCmd(cmd) {
  if (cmd === 'force') {
    busy.value.video = true
    try {
      await api.generate(sid, { kind: 'video', force: true })
      ElMessage.success('已跳过素材校验提交')
      setTimeout(reload, 1500)
    } finally {
      busy.value.video = false
    }
  } else if (cmd === 'tail') {
    const v = videoOutputs.value[0]
    if (!v) return ElMessage.warning('还没有成片，先用任务中心或此处出片')
    await doExtractTail(v.path)
  }
}

async function doAudit() {
  const r = await api.audit(sid)
  auditResult.value = r.audio
  ElMessage.success('校验完成')
}

function copyPath(p) {
  navigator.clipboard.writeText(p)
  ElMessage.success('路径已复制')
}

onMounted(async () => {
  await reload()
  try {
    opts.value = await api.cameraOptions()
  } catch (e) {
    opts.value = {}
  }
  timer = setInterval(async () => {
    if (data.value?.task_state?.has_running) {
      try { await reload() } catch (e) { /* ignore */ }
    }
  }, 5000)
})
onUnmounted(() => timer && clearInterval(timer))
</script>

<style scoped>
.detail { height: 100%; display: flex; flex-direction: column; }
.head {
  display: flex; align-items: center; gap: 8px; padding: 8px 16px;
  background: #fff; border-bottom: 1px solid var(--border); flex: 0 0 auto;
}
.cols { flex: 1; display: flex; flex-direction: column; overflow-y: auto; }
.pane {
  flex: 0 0 auto; min-width: 0; padding: 12px 16px 18px;
  border-bottom: 1px solid var(--border);
}
.pane:last-child { border-bottom: none; padding-bottom: 48px; background: #fbfbfc; }
.pane-head {
  display: flex; align-items: center; gap: 6px; font-size: var(--fs-base); font-weight: 600;
  margin-bottom: 10px; padding-bottom: 6px; border-bottom: 1px solid var(--border);
}
.pane-title { font-size: var(--fs-base); font-weight: 600; margin-right: 4px; }
/* 每行台词 = 一段参考音频（一个镜头可挂多段） */
.audio-head { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
.actions { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.beat { display: flex; gap: 8px; margin-bottom: 6px; align-items: flex-start; }
.beat .tiny { line-height: 1.6; }
.cons { margin: 0; padding-left: 18px; font-size: var(--fs-sm); line-height: 1.7; }
.cons li { margin-bottom: 4px; }
.task-row { display: flex; align-items: center; gap: 6px; padding: 4px 0; border-bottom: 1px dashed #eef0f4; }
/* 成片产物：每条宽度＝视频本身宽度（不再撑满面板），多条横向顺排、超宽自动换行 */
.vid-strip { display: flex; flex-wrap: wrap; gap: 14px; align-items: flex-start; }
.vid-item {
  display: flex; flex-direction: column; align-items: stretch;
  width: 168px; padding: 8px; border: 1px solid var(--border);
  border-radius: 8px; background: #fff;
}
.vid-box { position: relative; }
.vid-item video { display: block; width: 100%; height: auto; border-radius: 6px; background: #000; }
/* 状态标（成片/目录）压在画面左上角，不占一行、也不把卡片撑宽 */
.vid-badge {
  position: absolute; left: 4px; top: 4px; height: 16px; line-height: 16px; padding: 0 5px;
  border-radius: 3px; font-size: 10px; color: #fff; background: rgba(0, 0, 0, 0.55);
  pointer-events: none;
}
.vid-badge.final { background: var(--el-color-primary); }
.vid-path { margin-top: 6px; }
/* 操作与「视频参考图」区一致：一排 22x22 小图标按钮，不再用整行文字按钮把卡片撑高 */
.vid-btns { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 6px; }
.vid-btns button {
  display: inline-flex; align-items: center; justify-content: center;
  width: 22px; height: 22px; padding: 0; border-radius: 4px;
  border: 1px solid var(--border); background: #fff; color: #5b6478;
  font-size: 14px; cursor: pointer; line-height: 1;
}
.vid-btns button:hover { border-color: var(--el-color-primary); color: var(--el-color-primary); }
.vid-btns button.on { border-color: var(--el-color-warning); color: var(--el-color-warning); background: #fffaf0; }
.vid-btns button.del { color: #c0392b; }
.vid-btns button.del:hover { border-color: #c0392b; background: #fdecec; }

/* 生成进度 / 失败原因（内联在分镜图、视频区里） */
.gen-run { display: flex; align-items: center; gap: 10px; }
.gen-fail {
  padding: 6px 10px; border-radius: 6px; font-size: var(--fs-mini);
  background: #fdecec; color: #c0392b;
}
/* 候选操作：悬停只留给「点图看大图」，操作固定在图片下方一排小图标 */
.thumb { position: relative; }
.thumb-box { position: relative; border-radius: 6px; overflow: hidden; }
.thumb-box img { display: block; width: 100%; cursor: zoom-in; }
.thumb-bar { display: flex; gap: 4px; margin-top: 4px; padding: 0 6px 6px; }
.thumb-bar button {
  display: inline-flex; align-items: center; justify-content: center;
  width: 22px; height: 22px; padding: 0; border-radius: 4px;
  border: 1px solid var(--border); background: #fff; color: #5b6478;
  font-size: 14px; cursor: pointer; line-height: 1;
}
.thumb-bar button:hover { border-color: var(--el-color-primary); color: var(--el-color-primary); }
.thumb-bar button.del { color: #c0392b; }
.thumb-bar button.del:hover { border-color: #c0392b; background: #fdecec; }

.wizard { margin: 0 0 10px; }
.wz-head { display: flex; align-items: center; cursor: pointer; padding: 2px 0; }
.wz-head b { font-size: var(--fs-base); }
.wz-body { margin-top: 8px; border-top: 1px solid var(--border); padding-top: 10px; }
.wz-row { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.wz-label { font-size: var(--fs-mini); color: #8a93a8; }
.pos-grid { display: grid; grid-template-columns: repeat(3, 44px); grid-auto-rows: 25px; gap: 3px; }
.pos-cell {
  border: 1px solid var(--border); background: #fff; border-radius: 4px;
  font-size: var(--fs-mini); cursor: pointer; padding: 0; color: #5b6478;
}
.pos-cell.on { border-color: #6b4423; background: #f6efe7; color: #6b4423; font-weight: 600; }
.wz-out { background: #f7f8fa; border-radius: 6px; padding: 8px 10px; flex: 1; min-width: 0; }
.wz-preview { display: flex; gap: 10px; align-items: flex-start; margin-top: 10px; }
.wz-preview > svg { flex: 0 0 auto; border-radius: 4px; }
.wz-figs { display: flex; gap: 6px; flex: 0 0 auto; }
.wz-fig { margin: 0; width: 72px; text-align: center; }
.wz-fig img {
  width: 72px; height: 128px; object-fit: cover; display: block;
  border: 1px solid var(--border); border-radius: 4px; background: #fff;
}
.wz-fig figcaption { font-size: var(--fs-mini); color: #5b6478; margin-top: 2px; }
.wz-fig > svg { display: block; width: 72px; height: 128px; border-radius: 4px; }
.wz-fig-empty {
  width: 150px; height: 128px; display: flex; align-items: center; justify-content: center;
  border: 1px dashed var(--border); border-radius: 4px; font-size: var(--fs-mini); color: #a9b0c0;
  text-align: center; padding: 0 10px; line-height: 1.5;
}
.wz-warn {
  margin-top: 8px; padding: 8px 10px; border-radius: 6px;
  background: #fff8ec; border: 1px solid #f0d9b0; color: #7a5410;
  font-size: var(--fs-mini); line-height: 1.6;
}
.opt-row { display: flex; align-items: center; gap: 8px; }
.opt-row > svg {
  flex: 0 0 auto; border-radius: 2px; background: #fff;
  border: 1px solid #e6e9ef;
}
/* 下拉项里的示意图：小尺寸竖图，行高固定 34px 内不撑破 */
.opt-img {
  flex: 0 0 auto; width: 20px; height: 34px; object-fit: cover;
  border: 1px solid #e6e9ef; border-radius: 2px; background: #fff; display: block;
}
.wz-line { display: flex; gap: 8px; align-items: baseline; padding: 2px 0; font-size: var(--fs-mini); }
.wz-line .mono { word-break: break-all; }
.wz-tag { flex: 0 0 42px; font-size: var(--fs-mini); color: #5b6478; }
.wz-tag.move { color: #a86a10; }
.lnk { color: #6b4423; cursor: pointer; }

/* 选尾帧弹层：候选瓦片整块可点（点图即设首帧，光标别用 zoom-in 误导），成片每行一个「抽尾帧」 */
.thumb.pick { cursor: pointer; }
.thumb.pick .thumb-box img { cursor: pointer; }
.thumb.pick:hover .thumb-box { outline: 2px solid var(--el-color-primary); outline-offset: 1px; }
.vid-row {
  display: flex; align-items: center; gap: 10px;
  padding: 6px 8px; border: 1px solid var(--border); border-radius: 6px; margin-bottom: 6px;
}
.mb12 { margin-bottom: 12px; }

/* 视频参数三个字段：带小标签，否则只有 placeholder，看不出是什么 */
.vid-params { align-items: flex-end; }
.pf-label { font-size: var(--fs-mini); color: #8a93a8; margin-bottom: 2px; }
</style>
