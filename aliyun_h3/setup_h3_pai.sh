#!/bin/bash
# MiniMax H3 + Flux 一键安装 v2（PAI-DSW / A10 24G）— 修复：大小走 API、升级走 reset
set -u
LOG=/tmp/setup_h3_pai.log
exec > >(tee -a "$LOG") 2>&1
C=/root/ComfyUI; M=$C/models; MS=https://modelscope.cn/models; HMR=https://hf-mirror.com
echo "== [1/6] env =="; nvidia-smi|head -10||exit 1; df -h /|tail -1; python3 -V; pkill -f "ComfyUI/main.py" 2>/dev/null
echo "== [2/6] upgrade =="; cd $C||exit 1; git fetch --depth=1 origin master 2>&1|tail -1; git reset --hard FETCH_HEAD 2>&1|tail -1; git log -1 --oneline; pip install -q -r requirements.txt 2>&1|tail -3; echo "ComfyUI OK"
echo "== [3/6] download =="
mkdir -p $M/diffusion_models $M/text_encoders $M/vae $M/unet $M/clip $M/loras
# 从 modelscope API 拿文件真实大小（CDN 不返回 Content-Range，只能走 API）
gs(){ curl -s --max-time 30 "https://modelscope.cn/api/v1/models/$1/repo/files?Revision=master&Recursive=true" | python3 -c "import json,sys; d=json.load(sys.stdin); f=[x for x in d.get('Data',{}).get('Files',[]) if x.get('Path')=='$2']; print(f[0]['Size'] if f else '')"; }
# 并行分片：$1=url $2=out $3=nthreads $4=total
dp(){ local u=$1 o=$2 n=$3 t=$4 i k m; k=1; m=$o.tmp; rm -f $m
  for((i=0;i<n;i++));do local lo=$((i*t/n)) hi=$(((i+1)*t/n-1)) ex=$((hi-lo+1))
    [ -f $o.part.$i ]&&[ "$(stat -c%s $o.part.$i 2>/dev/null||echo 0)" -ge $((ex-64)) ]&&continue
    ( for r in 1 2 3; do curl -s -L -r $lo-$hi --retry 3 --speed-time 45 --speed-limit 1024 --max-time 3600 -o $o.part.$i $u
        [ "$(stat -c%s $o.part.$i 2>/dev/null||echo 0)" -ge $((ex-64)) ]&&break; rm -f $o.part.$i; sleep 2; done ) &
  done; wait
  for((i=0;i<n;i++));do local sz=$(stat -c%s $o.part.$i 2>/dev/null||echo 0); local ex=$(((i+1)*t/n-i*t/n)); [ $sz -lt $((ex-64)) ]&&k=0; done
  [ $k -eq 0 ]&&{ echo "[WARN] 分片仍有失败,整体作废回退"; rm -f $o.part.*; return 1; }
  for((i=0;i<n;i++));do cat $o.part.$i>>$m; done; rm -f $o.part.*; mv $m $o; }
# 主下载：$1=ms_repo $2=ms_path $3=hf_url $4=out
dl(){ local repo=$1 path=$2 hf=$3 out=$4 w=$(gs $repo $path)
  if [ -f $out ]&&[ -n "$w" ]&&[ "$(stat -c%s $out)" = "$w" ];then echo "[skip] $(basename $out)"; return; fi
  echo "[dl] $(basename $out) $((w/1048576))MB"
  if [ -z "$w" ];then echo "[WARN] 大小未知,走hf单连接"; curl -s -L -C - --retry 8 --speed-time 60 --speed-limit 1024 --max-time 14400 -o $out $hf; return; fi
  dp "$MS/$repo/resolve/master/$path" "$out" 16 "$w" && echo "[OK] $(basename $out)" || { echo "[fb] hf-mirror单连接"; curl -s -L -C - --retry 8 --speed-time 60 --speed-limit 1024 --max-time 14400 -o $out $hf; [ "$(stat -c%s $out)" = "$w" ]&&echo "[OK] $(basename $out)"||echo "[WARN] $(basename $out) 大小异常"; }; }
H=Comfy-Org/MiniMax-H3; HM=$HMR/$H/resolve/main
dl $H diffusion_models/minimax_h3_fl2va_pruned_int8_convrot.safetensors $HM/diffusion_models/minimax_h3_fl2va_pruned_int8_convrot.safetensors $M/diffusion_models/minimax_h3_fl2va_pruned_int8_convrot.safetensors
dl $H text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors $HM/text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors $M/text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors
dl $H vae/minimax_h3_video_vae_fp16.safetensors $HM/vae/minimax_h3_video_vae_fp16.safetensors $M/vae/minimax_h3_video_vae_fp16.safetensors
dl $H vae/minimax_h3_audio_vae_fp32.safetensors $HM/vae/minimax_h3_audio_vae_fp32.safetensors $M/vae/minimax_h3_audio_vae_fp32.safetensors
echo "== [3.5] H3 四件套完成,先启动 ComfyUI(不用等Flux) =="
cd $C; nohup python3 main.py --listen 0.0.0.0 --port 8188 >/tmp/comfy_run.log 2>&1 & sleep 12
curl -s -o /dev/null -w "%{http_code}" http://localhost:8188/system_stats|grep -q 200&&echo "[OK] ComfyUI 已启动: http://localhost:8188 (可先玩T2V)"||echo "[WARN] tail -50 /tmp/comfy_run.log"
echo "== [3.6] 继续下载 Flux 组 =="
F=AI-ModelScope/FLUX.1-dev-gguf; FM=$HMR/city96/FLUX.1-dev-gguf/resolve/main
dl $F flux1-dev-Q4_K_S.gguf $FM/flux1-dev-Q4_K_S.gguf $M/unet/flux1-dev-Q4_K_S.gguf
T=AI-ModelScope/flux_text_encoders; TM=$HMR/comfyanonymous/flux_text_encoders/resolve/main
dl $T t5xxl_fp8_e4m3fn.safetensors $TM/t5xxl_fp8_e4m3fn.safetensors $M/text_encoders/t5xxl_fp8_e4m3fn.safetensors
dl $T clip_l.safetensors $TM/clip_l.safetensors $M/text_encoders/clip_l.safetensors
S=AI-ModelScope/FLUX.1-schnell
dl $S ae.safetensors $HMR/black-forest-labs/FLUX.1-schnell/resolve/main/ae.safetensors $M/vae/ae.safetensors
echo "== [4/6] reuse =="
for f in unet/qwen-image-edit-2511-Q4_K_M.gguf LLM/qwen2.5-14b-instruct-q4_k_m-00001-of-00003.gguf clip/Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf clip/mmproj-F16.gguf loras/qwen-image-edit-2511-multiple-angles-lora.safetensors; do [ -f $M/$f ]&&echo "[ok] $f"||echo "[miss] $f"; done
echo "== [5/6] disk =="; df -h /|tail -1; ls -lh $M/diffusion_models $M/text_encoders $M/vae $M/unet 2>/dev/null
echo "== [6/6] 确认 ComfyUI 存活 =="; curl -s -o /dev/null -w "%{http_code}
" http://localhost:8188/system_stats
echo "===== DONE ====="
