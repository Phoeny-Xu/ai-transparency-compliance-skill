#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""中英排版间距归一化（安全版）：只删空白，绝不删字符。

背景（2026-09-26 事故）：报告定稿后为落实「中文与英文/数字不加空格」而临时手写
`re.sub` 替换串，误写为只保留第二捕获组，一次性删除了 40 处紧邻 `§`／拉丁的汉字——
「符合§22757.1(d)」→「符§22757.1(d)」、「加州 SB 1000」→「加SB 1000」、
「校验 0E/0W」→「校0E/0W」、「措施 M3.4」→「措M3.4」。该损坏属**静默失效**：
`check_report.py`／`lint_terms.py` 无机器码覆盖，双绿不暴露。
本脚本把该步固化为安全工具——**只删除空白字符**，并在写盘前断言
「去掉空白后的字符序列完全不变」；断言失败一律拒绝写盘（退出码 2），
从机制上排除「替换串写错 → 误删汉字」这一类故障。

用法：
    python scripts/normalize_spacing.py <报告>.md            # dry-run，只报数（默认）
    python scripts/normalize_spacing.py <报告>.md --write    # 写盘（先备份 .pre_spacing_bak）

规则（对标用户排版规范「中文正文中英文/数字不加空格」）：
  1. 删除中文与拉丁字母／阿拉伯数字／`§` 之间的空格（双向）；
  2. 例外：序号标签后的空格保留（用户规范「序号例外」）——`**(N) `、行首 `- (N) `／`* (N) `
     以及行首 `(N) ` 三种写法均属此列，否则会粘成 `- (1)标记…`；
  3. 代码围栏（``` / ~~~）内的行不改动。
"""
from __future__ import annotations

import argparse
import io
import os
import re
import sys
from typing import List, Tuple

CJK = r'\u4e00-\u9fff'
LATIN = r'A-Za-z0-9\u00a7'

# 一趟合并匹配：①中文+空格+拉丁/§  ②拉丁/§/右括号+空格+中文
BOUNDARY = re.compile(f'([{CJK}])([ \\t]+)([{LATIN}])|([{LATIN})])([ \\t]+)([{CJK}])')
LABEL_TAIL = re.compile(r'(?:\*\*|\s|^)\(\d{1,3}\)$')   # **(1) / - (1) / 行首 (1) 之后属序号例外
FENCE = re.compile(r'^\s*(```|~~~)')


def boundary_replacement(m: 're.Match[str]', line: str) -> str:
    """边界命中处的替换策略：**只丢空格、保留两侧字符**。

    这是本脚本的安全核心——历史事故正是把此处写成「只返回第二捕获组」。
    测试以 monkeypatch 装回该错误策略，验证 `normalize_spacing` 的字符级断言会拦截。
    """
    if m.group(1) is not None:                       # 中文 → 拉丁/§
        return m.group(1) + m.group(3)
    if LABEL_TAIL.search(line[:m.start(4) + 1]):     # 序号标签例外：保留空格
        return m.group(0)
    return m.group(4) + m.group(6)                   # 拉丁/§/） → 中文


def _apply_line(line: str, samples: List[Tuple[str, str]]) -> str:
    def _repl(m: 're.Match[str]') -> str:
        keep = boundary_replacement(m, line)
        if keep != m.group(0):
            lo = max(0, m.start() - 16)
            hi = min(len(line), m.end() + 8)
            samples.append((line[lo:hi], line[lo:m.start()] + keep + line[m.end():hi]))
        return keep

    return BOUNDARY.sub(_repl, line)


def normalize_spacing(text: str) -> Tuple[str, List[Tuple[str, str]]]:
    """返回（新文本, 变更样本）。只删除空白，不触碰任何非空白字符。"""
    out_lines: List[str] = []
    samples: List[Tuple[str, str]] = []
    in_fence = False

    for line in text.split('\n'):
        if FENCE.match(line):
            in_fence = not in_fence
            out_lines.append(line)
            continue
        if in_fence:
            out_lines.append(line)
            continue
        out_lines.append(_apply_line(line, samples))

    new_text = '\n'.join(out_lines)
    # 硬约束：只允许删除空白，非空白字符序列必须逐字不变
    if re.sub(r'\s+', '', new_text) != re.sub(r'\s+', '', text):
        raise AssertionError('归一化改动了非空白字符——拒绝写盘（疑似替换串写错）')
    return new_text, samples


def main() -> int:
    ap = argparse.ArgumentParser(description='中英排版间距归一化（安全版，只删空白）')
    ap.add_argument('report', help='待处理的 Markdown 文件')
    ap.add_argument('--write', action='store_true', help='写盘（默认 dry-run）')
    ap.add_argument('--quiet', action='store_true', help='只输出计数')
    args = ap.parse_args()

    with open(args.report, encoding='utf-8') as f:
        text = f.read()

    try:
        new_text, samples = normalize_spacing(text)
    except AssertionError as exc:
        print(f'[2] 断言失败：{exc}')
        return 2

    if args.quiet:
        print(f'{args.report}：待删除空格 {len(samples)} 处')
    else:
        print(f'=== normalize_spacing：{os.path.basename(args.report)} ===')
        for before, after in samples[:12]:
            print(f'  − {before}   →   {after}')
        if len(samples) > 12:
            print(f'  …（其余 {len(samples) - 12} 处同型）')
        print(f'--- 合计 {len(samples)} 处；模式：{"dry-run（未写盘）" if not args.write else "已写盘"} ---')

    if not args.write:
        return 0

    backup = args.report + '.pre_spacing_bak'
    with open(backup, 'w', encoding='utf-8', newline='') as f:
        f.write(text)
    with open(args.report, 'w', encoding='utf-8', newline='') as f:
        f.write(new_text)
    print(f'已写盘；备份：{os.path.basename(backup)}')
    leftovers = len(re.findall(f'[{CJK}][ \\t]+[{LATIN}]', new_text))
    print(f'复核：残留「汉字+空格+拉丁/§」 {leftovers} 处（应为 0）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
