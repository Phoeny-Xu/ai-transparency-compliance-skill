#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验 CoP 个案适用矩阵、报告展开和落地建议之间的闭环。

本脚本不替代法律判断。适用性由报告编写者逐项分类；脚本仅验证分类完整、
报告覆盖标记完整，以及全部已触发义务均映射到至少一个落地建议主题。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from survey_io import AuditFormatError, load_audit  # noqa: E402


REGISTRY_START = "<!-- COP_CASE_REGISTRY_JSON_START -->"
REGISTRY_END = "<!-- COP_CASE_REGISTRY_JSON_END -->"
MATRIX_SCHEMA = "cop_case_matrix/1"
REGISTRY_SCHEMA = "cop_case_registry/1"
SECTIONS = {"Section 1", "Section 2"}
STATUSES = {"已签署", "计划签署", "未签署", "不确定"}
CLASSIFICATIONS = {"applicable", "conditional", "not_applicable", "to_verify"}
ACTIVE = {"applicable", "conditional"}

ITEM_MARKER_RE = re.compile(
    r"<!--\s*cop:item\s+id=(?P<id>[^\s]+)\s+points=(?P<points>[^\s>]*)\s*-->", re.I
)
RECOMMENDATION_MARKER_RE = re.compile(
    r"<!--\s*cop:recommendation\s+theme=(?P<theme>[^\s]+)\s+duties=(?P<duties>[^\s>]*)\s*-->",
    re.I,
)
FOOTNOTE_DEF_RE = re.compile(r"^\[\^(?P<label>[^\]]+)\]:\s*(?P<body>.+)$", re.MULTILINE)
VISIBLE_MEASURE_FIELDS = {
    "层级": re.compile(r"(?:^|\n)\s*-\s*\*\*层级\*\*\s*[：:]"),
    "要求内容": re.compile(r"(?:^|\n)\s*-\s*\*\*要求内容\*\*\s*[：:]"),
    "技术与操作要点": re.compile(
        r"(?:^|\n)\s*-\s*\*\*技术(?:与|/)?操作要点\*\*\s*[：:]"
    ),
}
RECOMMENDATION_FIELDS = {
    name: re.compile(rf"(?:^|\n)\s*-\s*\*\*?{name}\*\*?\s*[：:]")
    for name in ("覆盖义务", "控制目标", "实施动作", "责任分工", "优先级与节点", "验收证据")
}
VAGUE_ACTION_RE = re.compile(r"持续关注|加强管理|完善机制|做好合规|及时跟进|强化意识")


def read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法读取 JSON：{path}（{exc}）") from exc
    if not isinstance(data, dict):
        raise ValueError(f"JSON 顶层须为对象：{path}")
    return data


def load_registry(root: Path) -> dict:
    path = root / "references" / "cop-digest.md"
    text = path.read_text(encoding="utf-8")
    if REGISTRY_START not in text or REGISTRY_END not in text:
        raise ValueError("cop-digest.md 缺少 CoP 个案适用与覆盖注册表边界")
    payload = text.split(REGISTRY_START, 1)[1].split(REGISTRY_END, 1)[0].strip()
    payload = re.sub(r"^```json\s*", "", payload)
    payload = re.sub(r"\s*```$", "", payload)
    data = json.loads(payload)
    if data.get("schema") != REGISTRY_SCHEMA:
        raise ValueError(f"未知注册表 schema：{data.get('schema')!r}")
    return data


def _csv(value: str) -> set[str]:
    if not value or value == "-":
        return set()
    return {item for item in value.split(",") if item}


def report_markers(text: str) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    items: dict[str, set[str]] = {}
    for match in ITEM_MARKER_RE.finditer(text):
        items.setdefault(match.group("id"), set()).update(_csv(match.group("points")))
    recommendations: dict[str, set[str]] = {}
    for match in RECOMMENDATION_MARKER_RE.finditer(text):
        recommendations.setdefault(match.group("theme"), set()).update(_csv(match.group("duties")))
    return items, recommendations


def _preceding_block(text: str, position: int, *, heading: bool = False) -> str:
    if heading:
        starts = [match.start() for match in re.finditer(r"(?m)^###\s+", text[:position])]
        start = starts[-1] if starts else 0
    else:
        matches = list(ITEM_MARKER_RE.finditer(text, 0, position))
        start = matches[-1].end() if matches else 0
    return text[start:position]


def _footnote_definitions(text: str) -> dict[str, str]:
    return {match.group("label"): match.group("body").strip() for match in FOOTNOTE_DEF_RE.finditer(text)}


def _source_matches(record: dict, source: str) -> bool:
    item_id = str(record.get("id", ""))
    match = re.fullmatch(r"S([12])-C(\d+)-M([\d.]+)", item_id)
    if not match:
        return False
    section, commitment, measure = match.groups()
    if not re.search(rf"Section\s*{section}(?!\d)|第\s*{section}\s*部分", source, re.I):
        return False
    if not re.search(rf"(?:Commitment|承诺)\s*C?{commitment}(?!\d)", source, re.I):
        return False
    if not re.search(rf"(?:Measure|措施)\s*M?{re.escape(measure)}(?![\d.])", source, re.I):
        return False
    compact = re.sub(r"\s+", "", source).replace("（", "(").replace("）", ")")
    for anchor in record.get("art50_anchor", []):
        paragraph = re.search(r"50\((\d+)\)", str(anchor))
        if paragraph and not (
            f"50({paragraph.group(1)})" in compact
            or f"第50条第{paragraph.group(1)}款" in compact
        ):
            return False
    return True


def validate(
    root: Path,
    matrix: dict,
    report_text: str,
    audit_path: Path | None = None,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        registry = load_registry(root)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [f"COV-00 注册表不可读：{exc}"], []

    if matrix.get("schema") != MATRIX_SCHEMA:
        errors.append(f"COV-01 matrix schema 应为 {MATRIX_SCHEMA}")

    signatory = matrix.get("signatory")
    if not isinstance(signatory, dict):
        errors.append("COV-02 signatory 须为对象")
        signatory = {}
    status = signatory.get("status")
    sections = signatory.get("sections", [])
    if status not in STATUSES:
        errors.append(f"COV-02 signatory.status 值无效：{status!r}")
    if not isinstance(sections, list) or any(section not in SECTIONS for section in sections):
        errors.append("COV-02 signatory.sections 只能包含 Section 1/Section 2")
        sections = []
    if status in {"已签署", "计划签署"} and not sections:
        errors.append("COV-02 已签署/计划签署时须明确涉及的 Section")
    if status == "未签署" and sections:
        errors.append("COV-02 未签署时 signatory.sections 应为空")

    relevant = matrix.get("relevant_sections")
    if not isinstance(relevant, list) or any(section not in SECTIONS for section in relevant):
        errors.append("COV-03 relevant_sections 只能包含 Section 1/Section 2")
        relevant = []

    records = registry.get("records")
    if not isinstance(records, list):
        return errors + ["COV-00 注册表 records 须为数组"], warnings
    registry_by_id = {record.get("id"): record for record in records if isinstance(record, dict)}
    expected = {rid for rid, record in registry_by_id.items() if record.get("section") in relevant}

    items = matrix.get("items")
    if not isinstance(items, list):
        errors.append("COV-04 items 须为数组")
        items = []
    case_by_id: dict[str, dict] = {}
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"COV-04 items[{index}] 须为对象")
            continue
        item_id = item.get("id")
        if item_id in case_by_id:
            errors.append(f"COV-04 重复规则：{item_id}")
        elif isinstance(item_id, str):
            case_by_id[item_id] = item
        else:
            errors.append(f"COV-04 items[{index}].id 缺失")

    missing = sorted(expected - set(case_by_id))
    extra = sorted(set(case_by_id) - expected)
    if missing:
        errors.append("COV-05 相关 Section 存在未分类规则：" + "、".join(missing))
    if extra:
        errors.append("COV-05 items 含非 relevant_sections 规则或未知规则：" + "、".join(extra))

    item_markers, recommendation_markers = report_markers(report_text)
    item_marker_matches = list(ITEM_MARKER_RE.finditer(report_text))
    recommendation_marker_matches = list(RECOMMENDATION_MARKER_RE.finditer(report_text))
    footnotes = _footnote_definitions(report_text)
    item_blocks: dict[str, list[str]] = {}
    for match in item_marker_matches:
        item_blocks.setdefault(match.group("id"), []).append(
            _preceding_block(report_text, match.start())
        )
    recommendation_blocks: dict[str, list[str]] = {}
    for match in recommendation_marker_matches:
        recommendation_blocks.setdefault(match.group("theme"), []).append(
            _preceding_block(report_text, match.start(), heading=True)
        )
    duties_to_themes: dict[str, set[str]] = {}
    for theme, duties in recommendation_markers.items():
        for duty in duties:
            duties_to_themes.setdefault(duty, set()).add(theme)

    for item_id in sorted(expected & set(case_by_id)):
        item = case_by_id[item_id]
        record = registry_by_id[item_id]
        classification = item.get("classification")
        if classification not in CLASSIFICATIONS:
            errors.append(f"COV-06 {item_id} classification 值无效：{classification!r}")
            continue
        if classification in {"conditional", "not_applicable", "to_verify"} and not str(item.get("reason", "")).strip():
            errors.append(f"COV-07 {item_id} 的 {classification} 状态缺少理由")
        if classification not in ACTIVE:
            continue

        blocks = item_blocks.get(item_id, [])
        if not blocks:
            errors.append(f"COV-15 {item_id} 缺少可见 Measure 块或 cop:item 标记")
        else:
            block = blocks[0]
            absent_fields = [name for name, pattern in VISIBLE_MEASURE_FIELDS.items() if not pattern.search(block)]
            if absent_fields:
                errors.append(f"COV-15 {item_id} 可见字段缺失：" + "、".join(absent_fields))

            references = [
                label for label in re.findall(r"\[\^([^\]]+)\]", block)
                if label.startswith(("cop_src_", "cop_s1_", "cop_s2_"))
            ]
            if not references:
                errors.append(f"COV-16 {item_id} 缺少专用 CoP 来源脚注")
            elif not any(label in footnotes and _source_matches(record, footnotes[label]) for label in references):
                errors.append(f"COV-16 {item_id} 的 CoP 来源脚注与 Section/Commitment/Measure/Art. 50 锚点不匹配")

            # 2026-09-27 修：原 `r"\*\*M([\d.]+)\b"` 在「**M2.1内部合规流程**」这类
            # 排版归一化后的写法上失效——`\b` 要求 "1" 后是非 word 字符，而中文属 \w，
            # 回溯后只捕到 "2."，误报 COV-18「标题错位为 M2.」。改为取完整点分编号。
            title_measure = re.search(r"\*\*M(\d+(?:\.\d+)*)", block)
            expected_measure = item_id.rsplit("M", 1)[-1]
            if title_measure and title_measure.group(1) != expected_measure:
                errors.append(f"COV-18 {item_id} 的可见 Measure 标题错位为 M{title_measure.group(1)}")

        theme = item.get("recommendation_theme") or record.get("recommendation_theme")
        if not isinstance(theme, str) or not theme.strip():
            errors.append(f"COV-08 {item_id} 缺少 recommendation_theme")
        elif theme not in duties_to_themes.get(item_id, set()):
            errors.append(f"COV-09 {item_id} 未映射到落地建议主题 {theme}")

        if record.get("will_required"):
            if item_id not in item_markers:
                errors.append(f"COV-10 {item_id} 属 will/commit+will，报告缺少 cop:item 覆盖标记")
            elif record.get("expansion_required"):
                required_points = set(record.get("required_points", []))
                absent = sorted(required_points - item_markers[item_id])
                if absent:
                    errors.append(f"COV-11 {item_id} 关键展开点缺失：" + "、".join(absent))

    obligations = matrix.get("triggered_obligations")
    if not isinstance(obligations, list):
        errors.append("COV-12 triggered_obligations 须为数组（可含三地全部已触发义务）")
        obligations = []
    seen_obligations: set[str] = set()
    for index, obligation in enumerate(obligations):
        if not isinstance(obligation, dict) or not str(obligation.get("id", "")).strip():
            errors.append(f"COV-12 triggered_obligations[{index}] 缺少 id")
            continue
        duty_id = obligation["id"]
        if duty_id in seen_obligations:
            errors.append(f"COV-12 重复已触发义务：{duty_id}")
        seen_obligations.add(duty_id)
        theme = obligation.get("recommendation_theme")
        if not isinstance(theme, str) or not theme.strip():
            errors.append(f"COV-12 {duty_id} 缺少 recommendation_theme")
        elif theme not in duties_to_themes.get(duty_id, set()):
            errors.append(f"COV-13 已触发义务 {duty_id} 未映射到落地建议主题 {theme}")

    for item_id, blocks in sorted(item_blocks.items()):
        if len(blocks) > 1:
            errors.append(f"COV-18 同一 Measure 重复出现：{item_id}")

    visible_body = FOOTNOTE_DEF_RE.sub("", report_text)
    visible_body = re.sub(r"<!--.*?-->", "", visible_body, flags=re.S)
    # 2026-09-27 修：原 `CoP\b` 在「来源：CoP措施」这类中英紧邻写法上不成立
    # （中文属 \w，`\b` 失败）→ 该禁用句在排版归一化后静默漏检。改为只排除后接拉丁数字的情形。
    if re.search(r"来源\s*[：:]\s*(?:《?AI生成内容透明度行为准则|CoP(?![A-Za-z0-9])|准则第)", visible_body, re.I):
        errors.append("COV-17 正文残留 CoP 来源句；来源应由专用脚注承载")

    registered_themes = {
        str(record.get("recommendation_theme"))
        for record in records
        if isinstance(record, dict) and record.get("recommendation_theme")
    }
    registered_themes.update(
        str(obligation.get("recommendation_theme"))
        for obligation in obligations
        if isinstance(obligation, dict) and obligation.get("recommendation_theme")
    )
    for theme, blocks in sorted(recommendation_blocks.items()):
        if theme not in registered_themes:
            errors.append(f"COV-21 未注册的落地建议主题键：{theme}")
        if len(blocks) > 1:
            errors.append(f"COV-21 同一主要建议主题重复登记：{theme}")
        block = blocks[0]
        absent = [name for name, pattern in RECOMMENDATION_FIELDS.items() if not pattern.search(block)]
        if absent:
            errors.append(f"COV-19 建议主题 {theme} 缺少执行字段：" + "、".join(absent))
        action_match = re.search(
            r"(?:^|\n)\s*-\s*\*\*?实施动作\*\*?\s*[：:](.*?)(?=\n\s*-\s*\*\*|\Z)",
            block,
            re.S,
        )
        if action_match:
            action_text = action_match.group(1).strip()
            if VAGUE_ACTION_RE.search(action_text) and len(re.sub(r"\s+", "", action_text)) <= 40:
                warnings.append(f"COV-W-01 建议主题 {theme} 的实施动作疑似空泛，需人工复核")

    conditional_pairs: list[tuple[str, str]] = []
    for item_id, item in case_by_id.items():
        if item.get("classification") == "conditional":
            record = registry_by_id.get(item_id, {})
            theme = item.get("recommendation_theme") or record.get("recommendation_theme")
            if isinstance(theme, str):
                conditional_pairs.append((item_id, theme))
    for obligation in obligations:
        if isinstance(obligation, dict) and obligation.get("classification") == "conditional":
            conditional_pairs.append((str(obligation.get("id")), str(obligation.get("recommendation_theme", ""))))
    for duty_id, theme in conditional_pairs:
        blocks = recommendation_blocks.get(theme, [])
        block = blocks[0] if blocks else ""
        has_dependency = bool(re.search(r"\*\*?条件与依赖\*\*?\s*[：:]", block))
        has_fact_check = bool(re.search(r"核验|核实|确认|查明|验证|盘点", block))
        if not has_dependency or not has_fact_check:
            errors.append(f"COV-20 条件式义务 {duty_id} 的主题 {theme} 缺少条件与依赖或事实核验动作")

    for duty_id, themes in sorted(duties_to_themes.items()):
        if len(themes) > 1:
            errors.append(f"COV-21 义务 {duty_id} 登记了多个主要主题：" + "、".join(sorted(themes)))

    if audit_path is not None:
        try:
            audit = load_audit(audit_path)
            b11 = audit.get("B11_cop")
            if not isinstance(b11, dict):
                errors.append("COV-14 审计文件未采集 B11_cop")
            elif b11.get("status") != status or set(b11.get("sections", [])) != set(sections):
                errors.append("COV-14 个案矩阵 signatory 与 survey_audit.json 的 B11_cop 不一致")
        except AuditFormatError as exc:
            errors.append(f"COV-14 审计文件不可用：{exc}")

    return errors, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="校验 CoP 个案矩阵、报告覆盖与落地建议闭环")
    parser.add_argument("matrix", type=Path)
    parser.add_argument("report", type=Path)
    parser.add_argument("--audit", type=Path)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args(argv)
    try:
        matrix = read_json(args.matrix)
        report_text = args.report.read_text(encoding="utf-8-sig")
    except (OSError, ValueError) as exc:
        print(f"[E] COV-00 {exc}")
        return 1
    errors, warnings = validate(args.root, matrix, report_text, args.audit)
    print(f"=== validate_cop_coverage：{args.report} ===")
    for error in errors:
        print("[E] " + error)
    for warning in warnings:
        print("[W] " + warning)
    print(f"--- E 级 {len(errors)} 项 / W 级 {len(warnings)} 项 ---")
    if errors:
        return 1
    return 2 if warnings else 0


if __name__ == "__main__":
    raise SystemExit(main())
