@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion
:: ============================================================
:: download_tier1.bat — 一键下载 Tier1 全部模型（本地预下载）
::
:: 用法：双击本文件，或在 PowerShell/CMD 里运行
:: 所有文件下载到 D:\Aicomfyui\models\ 对应子目录
:: 下载完按 PRE_DOWNLOAD.md 指引上传到 HAI
::
:: 总大小约 9.4 GB，建议在网络好的时候跑
:: ============================================================

set "BASE=D:\Aicomfyui\models"
set "LOG=%BASE%\download.log"

echo ============================================
echo   Tier1 模型预下载（HAI 开机前准备）
echo   目标目录: %BASE%
echo   日志文件: %LOG%
echo ============================================
echo.

:: 创建子目录
for %%d in (checkpoints loras vae animatediff) do (
    if not exist "%BASE%\%%d" mkdir "%BASE%\%%d"
)

:: 记录开始时间
date /t >> "%LOG%" 2>nul
time /t >> "%LOG%" 2>nul
echo [开始] Tier1 预下载 >> "%LOG%"

:: ---- 1) SDXL 基座 (6.5GB) ----
echo.
echo [1/5] SDXL 基座模型 sd_xl_base_1.0.safetensors (~6.5GB)
echo      来源: HuggingFace stabilityai/stable-diffusion-xl-base-1.0
if exist "%BASE%\checkpoints\sd_xl_base_1.0.safetensors" (
    echo      ✅ 已存在，跳过
    echo [1/5] SKIP 已存在 >> "%LOG%"
) else (
    echo      下载中...
    curl -L -o "%BASE%\checkpoints\sd_xl_base_1.0.safetensors" ^
        "https://hf-mirror.com/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors" ^
        --progress-bar -C - -w "\n      HTTP %%{http_code} | 耗时 %%{time_total}s\n"
    if !errorlevel! equ 0 (
        echo      ✅ 下载完成
        echo [1/5] OK >> "%LOG%"
    ) else (
        echo      ❌ 下载失败！请检查网络后重新运行本脚本（支持断点续传）
        echo [1/5] FAIL error=!errorlevel! >> "%LOG%"
    )
)

:: ---- 2) Pixar LoRA (137MB) ----
echo.
echo [2/5] 皮克斯风格 LoRA Canopus-Pixar-Art.safetensors (~137MB)
echo      来源: HuggingFace prithivMLmods/Canopus-Pixar-Art
if exist "%BASE%\loras\Canopus-Pixar-Art.safetensors" (
    echo      ✅ 已存在，跳过
    echo [2/5] SKIP 已存在 >> "%LOG%"
) else (
    echo      下载中...
    curl -L -o "%BASE%\loras\Canopus-Pixar-Art.safetensors" ^
        "https://hf-mirror.com/prithivMLmods/Canopus-Pixar-Art/resolve/main/Canopus-Pixar-Art.safetensors" ^
        --progress-bar -C - -w "\n      HTTP %%{http_code} | 耗时 %%{time_total}s\n"
    if !errorlevel! equ 0 (
        echo      ✅ 下载完成
        echo [2/5] OK >> "%LOG%"
    ) else (
        echo      ❌ 下载失败！请检查网络后重新运行本脚本（支持断点续传）
        echo [2/5] FAIL error=!errorlevel! >> "%LOG%"
    )
)

:: ---- 3) SDXL VAE fix (335MB) ----
echo.
echo [3/5] SDXL VAE sdxl_vae_fp16fix.safetensors (~335MB)
echo      来源: HuggingFace madebyollin/sdxl-vae-fp16-fix
if exist "%BASE%\vae\sdxl_vae_fp16fix.safetensors" (
    echo      ✅ 已存在，跳过
    echo [3/5] SKIP 已存在 >> "%LOG%"
) else (
    echo      下载中...
    curl -L -o "%BASE%\vae\sdxl_vae_fp16fix.safetensors" ^
        "https://hf-mirror.com/madebyollin/sdxl-vae-fp16-fix/resolve/main/sdxl_vae_fp16fix.safetensors" ^
        --progress-bar -C - -w "\n      HTTP %%{http_code} | 耗时 %%{time_total}s\n"
    if !errorlevel! equ 0 (
        echo      ✅ 下载完成
        echo [3/5] OK >> "%LOG%"
    ) else (
        echo      ❌ 下载失败！可重新运行（支持断点续传）
        echo [3/5] FAIL error=!errorlevel! >> "%LOG%"
    )
)

:: ---- 4) AnimateDiff SDXL motion model (2.2GB) ----
echo.
echo [4/5] AnimateDiff 动画模块 mm_sdxl_v10_beta.ckpt (~2.2GB)
echo      来源: HuggingFace guoyww/AnimateDiff
if exist "%BASE%\animatediff\mm_sdxl_v10_beta.ckpt" (
    echo      ✅ 已存在，跳过
    echo [4/5] SKIP 已存在 >> "%LOG%"
) else (
    echo      下载中...
    curl -L -o "%BASE%\animatediff\mm_sdxl_v10_beta.ckpt" ^
        "https://hf-mirror.com/guoyww/AnimateDiff/resolve/main/mm_sdxl_v10_beta.ckpt" ^
        --progress-bar -C - -w "\n      HTTP %%{http_code} | 耗时 %%{time_total}s\n"
    if !errorlevel! equ 0 (
        echo      ✅ 下载完成
        echo [4/5] OK >> "%LOG%"
    ) else (
        echo      ❌ 下载失败！可重新运行（支持断点续传）
        echo [4/5] FAIL error=!errorlevel! >> "%LOG%"
    )
)

:: ---- 5) VideoHelperSuite 插件 (git clone) ----
echo.
echo [5/5] VideoHelperSuite 插件 (代码 ~2MB)
echo      来源: GitHub Kosinkadink/ComfyUI-VideoHelperSuite
set "PLUGDIR=D:\Aicomfyui\custom_nodes"
if not exist "%PLUGDIR%" mkdir "%PLUGDIR%"
if exist "%PLUGDIR%\ComfyUI-VideoHelperSuite\.git" (
    echo      ✅ 已 clone，跳过
    echo [5/5] SKIP 已存在 >> "%LOG%"
) else (
    echo      git clone 中...
    cd /d "%PLUGDIR%" && git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git
    if !errorlevel! equ 0 (
        echo      ✅ clone 完成
        echo [5/5] OK >> "%LOG%"
    ) else (
        echo      ❌ clone 失败！请检查 git 是否安装
        echo [5/5] FAIL error=!errorlevel! >> "%LOG%"
    )
)

:: ---- 汇总 ----
echo.
echo ============================================
echo   下载汇总
echo ============================================
for %%f in ("%BASE%\checkpoints\sd_xl_base_1.0.safetensors") do (
    if exist %%~sf (echo   SDXL 基座:     %%~zf) else (echo   SDXL 基座:     ❌ 缺失)
)
for %%f in ("%BASE%\loras\Canopus-Pixar-Art.safetensors") do (
    if exist %%~sf (echo   Pixar LoRA:    %%~zf) else (echo   Pixar LoRA:    ❌ 缺失^⚠️ 需手动)
)
for %%f in ("%BASE%\vae\sdxl_vae_fp16fix.safetensors") do (
    if exist %%~sf (echo   SDXL VAE:      %%~zf) else (echo   SDXL VAE:      ❌ 缺失)
)
for %%f in ("%BASE%\animatediff\mm_sdxl_v10_beta.ckpt") do (
    if exist %%~sf (echo   动画模块:      %%~zf) else (echo   动画模块:      ❌ 缺失)
)
if exist "%PLUGDIR%\ComfyUI-VideoHelperSuite\.git" (
    echo   VHS 插件:      ✅ 已就绪
) else (
    echo   VHS 插件:      ❌ 缺失
)
echo ============================================
echo.
echo 完整说明见 PRE_DOWNLOAD.md
echo 全部就绪后开机 HAI → 上传 → 重启 ComfyUI → 发地址给我
echo.
time /t >> "%LOG%" 2>nul
echo ---------------------------------------- >> "%LOG%"

pause
