#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cop_digest_verify.py —— CoP 摘要（cop-digest.md）完整性 / 锚点校验

为什么需要它
------------
digest 的行号锚点是「**静默失效**」设计：`references/sources/EU-CoP-Transparency-Code-of-Practice.txt`
一旦重新抽取或重新下载，全部锚点失效且不会报错，报告里逐字引用的定位会悄悄指错地方。
这类校验只能靠代码，人工看不出来。

检查项
------
- **C-01 源指纹**：digest 头部登记的 MD5 / 行数 / 字节数与 sources txt 实际值比对（不符即锚点整体失效）。
- **C-02 完整性**：Section 1 应含 17 个 Measure、Section 2 应含 6 个 Measure ＋ 2 个 Commitment 级条款。
- **C-03 锚点区间**：每条 `锚点：L起–L止` 须在 [1, 总行数] 内且起 ≤ 止。
- **C-04 锚点指向**：锚点区间内应能定位到该单元的英文标题（版式层清洗后子串匹配）。
- **C-05 关键节点**：2027-02-02、200 token、Annex 1 三款图标等抽查项存在。
- **C-06 禁用词**：复用 lint_terms 词表扫描 digest 中文措辞。
- **C-07 固定注册表**：25项ID、必填字段、原文锚点及三个关键展开标记与正文单元一致。

用法
----
    python cop_digest_verify.py [--root <skill根>]

退出码：0=通过；1=有 E；2=仅 W。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lint_terms import RULES  # noqa: E402  （与报告术语门禁共用一张词表，不另抄一份）

UNIT_RE = re.compile(r"^\*\*(?P<id>M\d\.\d)\s+(?P<title>[^*]*)\*\*")
COMMIT_RE = re.compile(r"^###\s+(?P<id>S2-C\d)\s+(?P<title>.+)$")
ANCHOR_RE = re.compile(r"锚点：L(\d+)\s*[–\-~]\s*L?(\d+)")
REGISTRY_ANCHOR_RE = re.compile(r"^L(\d+)\s*[–\-~]\s*L?(\d+)$")
MD5_RE = re.compile(r"MD5\s+([0-9a-fA-F]{32})")
LINES_RE = re.compile(r"/\s*([\d,]+)\s*行")
BYTES_RE = re.compile(r"txt\s*([\d,]+)\s*字节")

EXPECT_S1 = {"M1.1", "M1.2", "M1.3", "M1.4", "M2.1", "M2.2", "M2.3", "M2.4",
             "M3.1", "M3.2", "M3.3", "M3.4", "M3.5", "M4.1", "M4.2", "M4.3", "M4.4"}
EXPECT_S2 = {"M1.1", "M1.2", "M1.3", "M2.1", "M2.2", "M2.3"}
EXPECT_S2_COMMIT = {"S2-C3", "S2-C4"}

KEY_NODES = ["2027-02-02", "200 token", "AI+GENERATED", "AI+MODIFIED"]
REGISTRY_START = "<!-- COP_CASE_REGISTRY_JSON_START -->"
REGISTRY_END = "<!-- COP_CASE_REGISTRY_JSON_END -->"
REGISTRY_FIELDS = {
    "id", "section", "actor", "art50_anchor", "applicability", "signatory_effect", "level",
    "will_required", "expansion_required", "required_points", "modality",
    "recommendation_theme", "source_anchor",
}
EXPECTED_REGISTRY_IDS = {
    *(f"S1-C1-M1.{n}" for n in range(1, 5)),
    *(f"S1-C2-M2.{n}" for n in range(1, 5)),
    *(f"S1-C3-M3.{n}" for n in range(1, 6)),
    *(f"S1-C4-M4.{n}" for n in range(1, 5)),
    *(f"S2-C1-M1.{n}" for n in range(1, 4)),
    *(f"S2-C2-M2.{n}" for n in range(1, 4)),
    "S2-C3", "S2-C4",
}
CRITICAL_EXPANSION_IDS = {"S1-C1-M1.1", "S1-C1-M1.2", "S1-C3-M3.4"}


def clean_layout(text: str) -> str:
    """版式层清洗（与构建规则第二节一致）：去空白、拼接单词内断行、去连字断词。"""
    text = text.replace("- ", "").replace("-\n", "").replace("\n", "")
    text = re.sub(r"\s+", "", text)
    return text.lower()


def verify(root: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    digest_path = root / "references" / "cop-digest.md"
    source_path = root / "references" / "sources" / "EU-CoP-Transparency-Code-of-Practice.txt"
    for p in (digest_path, source_path):
        if not p.exists():
            return [f"C-00 文件缺失：{p}"], []

    digest = digest_path.read_text(encoding="utf-8", errors="replace")
    raw = source_path.read_bytes()
    src_text = raw.decode("utf-8", errors="replace")
    total_lines = len(src_text.splitlines())
    cleaned_src = clean_layout(src_text)

    # ---- C-01 源指纹 ----
    m = MD5_RE.search(digest)
    if not m:
        errors.append("C-01 digest 头部未登记 MD5")
    else:
        actual = hashlib.md5(raw).hexdigest()
        if m.group(1).lower() != actual:
            errors.append(f"C-01 MD5 不符：头部 {m.group(1)} / 实际 {actual} → 全部行号锚点失效，须重建 digest")
    if (lm := LINES_RE.search(digest)) and lm.group(1) != f"{total_lines:,}":
        warnings.append(f"C-01 行数登记 {lm.group(1)} / 实际 {total_lines}（差 {total_lines - int(lm.group(1).replace(',', ''))}）")
    if (bm := BYTES_RE.search(digest)) and bm.group(1) != f"{len(raw):,}":
        warnings.append(f"C-01 字节数登记 {bm.group(1)} / 实际 {len(raw):,}")

    # ---- 分节 ----
    lines = digest.splitlines()
    s1_start = s2_start = -1
    for i, line in enumerate(lines):
        if line.startswith("#") and "Section 1" in line and s1_start < 0:
            s1_start = i
        elif line.startswith("#") and "Section 2" in line and s1_start >= 0 and s2_start < 0:
            s2_start = i
    if s1_start < 0 or s2_start < 0:
        errors.append("C-02 未能定位 Section 1 / Section 2 分节标题")
        return errors, warnings

    # ---- 单元与锚点 ----
    units: dict[str, dict] = {}
    current: str | None = None
    for i, line in enumerate(lines):
        m_unit = UNIT_RE.match(line)
        m_commit = COMMIT_RE.match(line)
        if m_unit:
            section = "S1" if i < s2_start else "S2"
            current = f"{section}:{m_unit.group('id')}"
            title = m_unit.group("title")
            eng = re.findall(r"（([A-Za-z][^）]*)）", title)
            units[current] = {"line": i + 1, "anchor": None, "eng": eng[-1] if eng else ""}
            continue
        if m_commit:
            current = f"S2:{m_commit.group('id')}"
            units[current] = {"line": i + 1, "anchor": None, "eng": ""}
            continue
        if current and "锚点" in line:
            a = ANCHOR_RE.search(line)
            if a:
                units[current]["anchor"] = (int(a.group(1)), int(a.group(2)))

    # ---- C-02 完整性 ----
    s1_ids = {k.split(":", 1)[1] for k in units if k.startswith("S1:")}
    s2_ids = {k.split(":", 1)[1] for k in units if k.startswith("S2:")}
    if missing := sorted(EXPECT_S1 - s1_ids):
        errors.append(f"C-02 Section 1 缺 Measure：{'、'.join(missing)}")
    if missing := sorted(EXPECT_S2 - s2_ids):
        errors.append(f"C-02 Section 2 缺 Measure：{'、'.join(missing)}")
    if missing := sorted(EXPECT_S2_COMMIT - s2_ids):
        errors.append(f"C-02 缺 Commitment 级条款：{'、'.join(missing)}")

    # ---- C-03 / C-04 锚点 ----
    for key, info in units.items():
        anchor = info["anchor"]
        if not anchor:
            warnings.append(f"C-03 {key} 未登记锚点（第 {info['line']} 行）")
            continue
        start, end = anchor
        if not (1 <= start <= end <= total_lines):
            errors.append(f"C-03 {key} 锚点 {start}–{end} 越界（总行数 {total_lines}）")
            continue
        if info["eng"]:
            probe = clean_layout("\n".join(lines_for(src_text, start, end)))
            needle = re.sub(r"\s+", "", info["eng"]).lower()
            if needle[:40] not in probe:
                warnings.append(f"C-04 {key} 锚点 {start}–{end} 内未定位到英文标题「{info['eng'][:40]}」")

    # ---- C-05 关键节点 ----
    for node in KEY_NODES:
        if node not in digest:
            warnings.append(f"C-05 关键节点「{node}」未在 digest 中出现（构建规则第五节抽查项）")

    # ---- C-07 固定个案适用与覆盖注册表 ----
    if REGISTRY_START not in digest or REGISTRY_END not in digest:
        errors.append("C-07 digest 缺少固定注册表边界")
    else:
        payload = digest.split(REGISTRY_START, 1)[1].split(REGISTRY_END, 1)[0].strip()
        payload = re.sub(r"^```json\s*", "", payload)
        payload = re.sub(r"\s*```$", "", payload)
        try:
            registry = json.loads(payload)
        except json.JSONDecodeError as exc:
            errors.append(f"C-07 注册表JSON无效：{exc}")
        else:
            if registry.get("schema") != "cop_case_registry/1":
                errors.append("C-07 注册表schema应为 cop_case_registry/1")
            records = registry.get("records")
            if not isinstance(records, list):
                errors.append("C-07 注册表records须为数组")
            else:
                ids = [record.get("id") for record in records if isinstance(record, dict)]
                if len(ids) != len(set(ids)):
                    errors.append("C-07 注册表存在重复ID")
                if missing := sorted(EXPECTED_REGISTRY_IDS - set(ids)):
                    errors.append("C-07 注册表缺少规则：" + "、".join(missing))
                if extra := sorted(set(ids) - EXPECTED_REGISTRY_IDS):
                    errors.append("C-07 注册表含未知规则：" + "、".join(extra))
                for index, record in enumerate(records):
                    if not isinstance(record, dict):
                        errors.append(f"C-07 records[{index}]须为对象")
                        continue
                    record_id = record.get("id", f"records[{index}]")
                    if missing_fields := sorted(REGISTRY_FIELDS - set(record)):
                        errors.append(f"C-07 {record_id} 缺字段：" + "、".join(missing_fields))
                    anchor = REGISTRY_ANCHOR_RE.search(str(record.get("source_anchor", "")))
                    if not anchor or not (1 <= int(anchor.group(1)) <= int(anchor.group(2)) <= total_lines):
                        errors.append(f"C-07 {record_id} source_anchor无效")
                    elif record_id in EXPECTED_REGISTRY_IDS:
                        if record_id in EXPECT_S2_COMMIT:
                            unit_key = f"S2:{record_id}"
                        else:
                            section, _commitment, measure = record_id.split("-", 2)
                            unit_key = f"{section}:{measure}"
                        body_anchor = units.get(unit_key, {}).get("anchor")
                        registry_anchor = (int(anchor.group(1)), int(anchor.group(2)))
                        if body_anchor and body_anchor != registry_anchor:
                            errors.append(
                                f"C-07 {record_id} source_anchor与正文不一致："
                                f"{registry_anchor[0]}-{registry_anchor[1]} / {body_anchor[0]}-{body_anchor[1]}"
                            )
                    if not isinstance(record.get("required_points"), list) or not record.get("required_points"):
                        errors.append(f"C-07 {record_id} required_points须为非空数组")
                    if record_id in CRITICAL_EXPANSION_IDS and not record.get("expansion_required"):
                        errors.append(f"C-07 {record_id} 必须标 expansion_required=true")

    # ---- C-06 禁用词 ----
    # digest 是纯文本、不适用报告的分节/声明区语境，故按词表原样全文扫描。
    for rule in RULES:
        if rule.pattern.search(digest):
            errors.append(
                f"C-06 digest 出现禁用词「{rule.display}」→「{rule.better}」（{rule.basis}）"
            )

    return errors, warnings


def lines_for(text: str, start: int, end: int) -> list[str]:
    return text.splitlines()[start - 1 : end]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="cop-digest 完整性/锚点校验")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    args = parser.parse_args(argv)

    errors, warnings = verify(Path(args.root))
    print(f"=== cop_digest_verify：{args.root} ===")
    for e in errors:
        print(f"[E] {e}")
    for w in warnings:
        print(f"[W] {w}")
    print(f"--- E 级 {len(errors)} 项 / W 级 {len(warnings)} 项 ---")
    if errors:
        return 1
    return 2 if warnings else 0


if __name__ == "__main__":
    raise SystemExit(main())
