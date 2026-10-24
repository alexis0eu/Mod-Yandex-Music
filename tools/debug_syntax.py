import sys

with open('src/renderer/mod-renderer.js', 'r', encoding='utf-8') as f:
    content = f.read()

stack = []
pairs = {')': '(', ']': '[', '}': '{'}
in_single_str = False
in_double_str = False
in_template_str = False
in_line_comment = False
in_block_comment = False
escaped = False

i = 0
n = len(content)
while i < n:
    ch = content[i]
    next_ch = content[i + 1] if i + 1 < n else ''

    if in_line_comment:
        if ch == '\n':
            in_line_comment = False
        i += 1
        continue
    if in_block_comment:
        if ch == '*' and next_ch == '/':
            in_block_comment = False
            i += 2
            continue
        i += 1
        continue
    if escaped:
        escaped = False
        i += 1
        continue
    if ch == '\\':
        escaped = True
        i += 1
        continue
    if not in_single_str and not in_double_str and not in_template_str:
        if ch == '/' and next_ch == '/':
            in_line_comment = True
            i += 2
            continue
        if ch == '/' and next_ch == '*':
            in_block_comment = True
            i += 2
            continue
    if ch == "'" and not in_double_str and not in_template_str:
        in_single_str = not in_single_str
        i += 1
        continue
    if ch == '"' and not in_single_str and not in_template_str:
        in_double_str = not in_double_str
        i += 1
        continue
    if ch == '`' and not in_single_str and not in_double_str:
        in_template_str = not in_template_str
        i += 1
        continue
    if in_single_str or in_double_str or in_template_str:
        i += 1
        continue

    if ch in '([{':
        stack.append((ch, i, content[:i].count('\n') + 1))
    elif ch in ')]}':
        if not stack:
            print('Empty stack on closing', ch, 'at', i)
            break
        top_ch, top_i, top_line = stack.pop()
        if top_ch != pairs[ch]:
            cur_line = content[:i].count('\n') + 1
            print(f'Mismatched: expected {top_ch} (from line {top_line}, pos {top_i}), got {ch} at line {cur_line}, pos {i}')
            print('Open snippet:', repr(content[max(0, top_i-30):top_i+30]))
            print('Close snippet:', repr(content[max(0, i-30):i+30]))
            break
    i += 1

print('Done debug syntax.')
