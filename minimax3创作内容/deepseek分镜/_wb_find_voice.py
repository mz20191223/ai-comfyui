import re, os

md_path = r'D:\Aicomfyui\minimax3创作内容\deepseek分镜\第1集_中文视频提示词_核对版.md'
s = open(md_path, encoding='utf-8').read()

print('===== md 中 过客 附近的声音/音色描述 =====')
for m in re.finditer('过客', s):
    ctx = s[max(0, m.start()-160):m.end()+160]
    if any(k in ctx for k in ['voice', '音色', '嗓音', '声音', 'says', '低沉', '冷',
                               '年轻', '磁性', '沙哑', '清', '沉', '声', '男', '语气']):
        snippet = ctx.replace('\n', ' ')
        print('...', snippet, '...')
        print('---')

print()
print('===== md 中 周野 / 黎舟 出现处（声音相关） =====')
for name in ['周野', '黎舟']:
    print(f'-- {name} 共出现 {len(re.findall(name, s))} 次 --')
    for m in re.finditer(name, s):
        ctx = s[max(0, m.start()-120):m.end()+120]
        if any(k in ctx for k in ['voice', '音色', '声音', 'says', '男', '声']):
            print('   ...', ctx.replace('\n', ' '), '...')
