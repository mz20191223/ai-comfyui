#!/usr/bin/env bash
# hai_c1_ssh.sh —— 本机侧（方案③）：通过 SSH 把 setup 脚本传到 HAI 并远程执行。
# 用法:
#   bash hai_c1_ssh.sh <user@host> [ssh_port] [identity_file]
# 例:
#   bash hai_c1_ssh.sh root@1.2.3.4 22
#   bash hai_c1_ssh.sh root@1.2.3.4 22 ~/.ssh/hai_key.pem
#
# 流程: scp 传 hai_c1_setup.sh -> ssh 远程跑(含无外网关机闸门) -> 提示给 ComfyUI 地址
set -e
TARGET="$1"
PORT="${2:-22}"
KEY="${3:-}"
HERE="$(cd "$(dirname "$0")" && pwd)"

if [ -z "$TARGET" ]; then
  echo "用法: bash hai_c1_ssh.sh <user@host> [port] [identity_file]"
  exit 1
fi

SSH_OPT=("-p" "$PORT")
SCP_OPT=("-P" "$PORT")
if [ -n "$KEY" ]; then
  SSH_OPT+=("-i" "$KEY")
  SCP_OPT+=("-i" "$KEY")
fi

echo "== 1/2 scp setup 脚本到 $TARGET =="
scp "${SCP_OPT[@]}" "$HERE/hai_c1_setup.sh" "$TARGET:/root/hai_c1_setup.sh"

echo "== 2/2 SSH 远程执行 setup（含 hf-mirror 连通闸门，无外网会提示关机）=="
ssh "${SSH_OPT[@]}" "$TARGET" "bash /root/hai_c1_setup.sh"

echo
echo "== setup 结束 =="
echo "若上面提示【关机】，请直接关 HAI，别烧钱；"
echo "若正常拉完权重并重启，请把 ComfyUI 公网地址(http://<IP>:6889) 给本机助手，"
echo "本机跑: python hai_c1.py --host http://<IP>:6889  出 9 宫格。"
