#!/bin/bash
cd /d/Aicomfyui/cloud
REPO=krisheetu/ComfyUI_Qwen-Image
for base in \
  "https://ghfast.top/https://github.com" \
  "https://gh-proxy.com/https://github.com" \
  "https://gitclone.com/github.com" \
  "https://mirror.ghproxy.com/https://github.com" \
  "https://kgithub.com" ; do
  url="$base/$REPO"
  echo ">> trying $url"
  rm -rf _krisheetu_mirror
  if git clone --depth 1 "$url" _krisheetu_mirror 2>&1 | tail -2 ; then
    if [ -f _krisheetu_mirror/qwen_image_nodes.py ]; then
      echo "SUCCESS via $base"
      tar czf _krisheetu_mirror.tar.gz _krisheetu_mirror
      echo "PACKED _krisheetu_mirror.tar.gz"
      exit 0
    fi
  fi
done
echo "ALL_MIRRORS_FAILED"
