# MiniMax H3 阿里云 PAI 部署 — 恢复清单（2026-08-05 12:00 停实例）

## 当前状态（停实例时）
- 实例：`dsw-bat131d8834b7fggc`（PAI-DSW，A10 24G，100G 系统盘）
- 已下载：fl2va 分片 ~785MB/21G（部分分片缺失，续传会补）；其余模型未下
- ComfyUI 已升级 HEAD `6f7cd7fc`；**pip 报错未解决**：`comfyui-frontend-package==1.48.6` 在 PyPI 不存在（超前 pin）
- 4 个工作流已生成：`D:\Aicomfyui\aliyun_h3\workflows\`（wf_01~04）
- 脚本：`/mnt/workspace/setup.sh`（8 线程续传版，云盘保留）

## 速度教训（铁律）
- PAI 上 modelscope/hf-mirror 单连接均 ~1.2MB/s；**8 线程 3.3MB/s（最优）**；16 线程 0.4MB/s（负优化，CDN 高并发惩罚）
- CDN 速度波动大：10:31 3.3MB/s → 10:50 1.2 → 12:00 0.25。**选择低峰时段（深夜/清晨）跑下载**
- 无官方加速通道（EAS 模型缓存=推理缓存非下载；OSS 内网仅自有 bucket）

## 下次开机恢复步骤
1. PAI 控制台开机实例（**勿点释放**）→ Web IDE → Terminal
2. 修 pip 版本 pin（二选一）：
   ```bash
   # A. 放宽版本（推荐）
   sed -i 's/comfyui-frontend-package==[0-9.]*/comfyui-frontend-package/' /root/ComfyUI/requirements.txt
   # 或 B. 装已发布版本
   pip install -q comfyui-frontend-package==1.47.12
   ```
3. 续跑安装脚本（已含续传逻辑，完整分片跳过）：
   ```bash
   bash /mnt/workspace/setup.sh
   ```
4. 下载完成（52.5G：H3 42.8G + Flux 9.7G）后：
   - 校验：`ls -lh /root/ComfyUI/models/diffusion_models /root/ComfyUI/models/text_encoders /root/ComfyUI/models/vae /root/ComfyUI/models/unet`
   - 部署工作流：本地 `D:\Aicomfyui\aliyun_h3\workflows\` 的 6 个文件（wf_01~04a/b/c）上传到 `/root/ComfyUI/user/default/workflows/`（JupyterLab 上传）→ ComfyUI 菜单 Workflow 可见
   - 访问 ComfyUI：Web IDE 里浏览器访问 `http://localhost:8188`（DSW 内端口，Web IDE 支持 /proxy/ 或控制台端口映射）
5. 验证链：① 扩写（wf_01）→ ② 角色图（wf_02）→ ③ 分镜图（wf_03）→ ④ 视频 I2V（wf_04b，分镜图做首帧）

## 关键文件
- 本地：`D:\Aicomfyui\aliyun_h3\`（setup_h3_pai.sh、gen_workflows.py、workflows/、README.md 半成品）
- 远端：`/mnt/workspace/setup.sh`（8线程版）
- 记忆：`.workbuddy/memory/2026-08-05.md`
