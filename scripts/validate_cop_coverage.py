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
