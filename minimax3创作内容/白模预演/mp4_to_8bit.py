# -*- coding: utf-8 -*-
"""
MiniMax H3 出片入库前统一转码：10-bit H.264 (High 10) -> 8-bit H.264 (High) + yuv420p + faststart
用法：
  python mp4_to_8bit.py <输入.mp4> [输出.mp4]
不传输出时，默认在同级目录生成 <原名>_8bit.mp4（不覆盖原文件，避免触发绿盾"修改"判定）

原因：H3 偶尔返回 yuv420p10le / High 10 profile，Windows 自带播放器、部分
PotPlayer/剪映版本与旧设备解不了，表现为"播放不了 / 只有声音 / 绿屏"。
"""
import os, sys, subprocess, imageio_ffmpeg

EXE = imageio_ffmpeg.get_ffmpeg_exe()


def probe(src):
    r = subprocess.run([EXE, '-hide_banner', '-i', src],
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    out = r.stderr
    prof, pix = None, None
    for line in out.split('\n'):
        if 'Video:' in line:
            prof = 'High 10 (10-bit)' if 'High 10' in line else ('High (8-bit)' if 'High' in line else line.strip()[:40])
            for p in ['yuv420p10le', 'yuv420p', 'yuv444p', 'p010le']:
                if p in line:
                    pix = p
                    break
    return prof, pix


def convert(src, dst):
    cmd = [EXE, '-hide_banner', '-y', '-i', src,
           '-c:v', 'libx264', '-profile:v', 'high', '-pix_fmt', 'yuv420p',
           '-crf', '18', '-preset', 'medium',
           '-c:a', 'copy', '-movflags', '+faststart', dst]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if r.returncode != 0:
        print('转码失败：')
        print(r.stderr[-2000:])
        return False
    return True


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    src = sys.argv[1]
    if len(sys.argv) >= 3:
        dst = sys.argv[2]
    else:
        base, ext = os.path.splitext(src)
        dst = base + '_8bit' + ext
    if not os.path.exists(src):
        print('文件不存在:', src)
        return
    p0, x0 = probe(src)
    print('源文件 :', os.path.basename(src))
    print('  编码 :', p0, '/', x0)
    if x0 == 'yuv420p':
        print('  已是 8-bit，无需转码（若仍播不了，检查 moov atom / 文件完整性）')
    print('转码中...')
    if convert(src, dst):
        p1, x1 = probe(dst)
        print('输出 :', dst)
        print('  编码 :', p1, '/', x1)
        print('  大小 : %.1f MB (原 %.1f MB)' % (os.path.getsize(dst) / 1048576, os.path.getsize(src) / 1048576))
        print('完成')


if __name__ == '__main__':
    main()
