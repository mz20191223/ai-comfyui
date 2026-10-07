import os

base = r'D:\Aicomfyui\minimax3创作内容\重制版\音频'
print('音频目录存在:', os.path.isdir(base))
if os.path.isdir(base):
    files = sorted(os.listdir(base))
    print('总文件数:', len(files))
    print()
    print('===== 含 过客/周野/黎舟 的音频 =====')
    for f in files:
        if any(k in f for k in ['过客', '周野', '黎舟']):
            print('  ', f, os.path.getsize(os.path.join(base, f)))
    print()
    print('===== 含 客/野/舟/男 的音频(前40) =====')
    cnt = 0
    for f in files:
        if any(k in f for k in ['客', '野', '舟', '男']):
            print('  ', f)
            cnt += 1
            if cnt >= 40:
                break
