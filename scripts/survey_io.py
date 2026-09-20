#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""survey_io.py —— survey_audit.json 的统一读取（单一事实来源）

定位
----
`references/survey-audit-schema.md` 定义的结构化答案契约，过去由 `resolve_triggers.py`
与 `build_skeleton.py` **各实现一遍**，两份实现已经分叉：前者只认扁平结构、不校验
schema、不判空，后者两种都收。分叉的后果在 2026-09-15「案例16-18 矛盾注入轮」被读源码
发现（V2-01）：按文档样例（元数据外壳＋`answers` 嵌套）落盘时，前者把整篇文档当答案用，
10 行触发判成 1 行，答案级校验静默通过，退出码 0。

本模块是该契约的**唯一读取入口**，引擎与骨架生成器共用，使「文档与实现不一致」在结构上
不可能再发生。

静默失败的两道闸
----------------
1. **结构校验**：顶层须为对象；`schema` 若存在须为 `survey_audit/2` 或兼容读取的 `survey_audit/1`；按嵌套或扁平解包后，
   答案键集合必须至少含一个已识别键（`A*` / `B*` / `SB1000_status`）。否则抛
   `AuditFormatError`，由调用方转退出码 2。
2. **编码容错**：一律以 `utf-8-sig` 读取。Windows PowerShell 5.1 的
   `Set-Content -Encoding UTF8` 会写 BOM，用 `utf-8` 读取会解析失败（V2-02）。

两条契约都收
------------
- 嵌套（文档样例）：`{"schema": …, "report": …, "session_date": …, "answers": {…}, "history": […]}`；
- 扁平（PowerShell 顺手写出的形状）：把答案键直接放在顶层。

嵌套是文档所定的形状，扁平是既有资产的形状，两者都收，避免为迁就实现去改文档。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

CURRENT_SCHEMA_ID = "survey_audit/2"
LEGACY_SCHEMA_ID = "survey_audit/1"
SUPPORTED_SCHEMA_IDS = frozenset({LEGACY_SCHEMA_ID, CURRENT_SCHEMA_ID})
# 兼容旧调用方；新文件应写入 CURRENT_SCHEMA_ID。
SCHEMA_ID = LEGACY_SCHEMA_ID

# 元数据键：不属于答案，解包时不混入答案空间
META_KEYS = frozenset({"schema", "report", "session_date", "history", "answers"})

# 已识别答案键（用于「读到了答案」与「答案为空」的区分）
KNOWN_KEYS = frozenset(
    {
        "A1", "A2", "A3", "A3_functions", "A3_modalities", "A3_detection", "A4a", "A4b", "A4c", "A4a_details", "A5", "A6", "A7",
        "B1_1", "B1_2", "B1_3", "B1_4", "B1_hardware",
        "B2", "B3a", "B3a_details",
        "B4_1", "B4_2", "B4_2a", "B4_2b", "B4_2c", "B4_2c_details",
        "B5a", "B5b", "B5b_interactive",
        "B6", "B7", "B8_1", "B8_2", "B8_3", "B8_4", "B9", "B10_current_practices", "B11_cop",
        "SB1000_status",
    }
)

# 答案键的形态（供未列入 KNOWN_KEYS 的增量题使用：A 组另有 A8/A9、B 组另有 B10 等）：
# 字母 A/B **后紧跟数字**（如 A8／B10／B4_2a）。**不得用裸前缀 `startswith(("A","B"))`**——
# 那会把 Author／Batch 一类元数据键也计入答案键（2026-09-19 收紧为 `^[AB]\d`）。
_ANSWER_KEY_RE = re.compile(r"^[AB]\d")
_KEY_PREFIX_EXCEPTIONS = frozenset({"schema", "report", "answers"})


class AuditFormatError(ValueError):
    """survey_audit.json 无法按契约读取（结构不符、答案为空、编码/解析失败）。"""


class AuditBundle(dict):
    """向后兼容的答案字典，同时保留审计元数据。"""

    def __init__(self, answers: dict, *, metadata: dict, history: list, migrations: list[str]):
        super().__init__(answers)
        self.answers = self
        self.metadata = metadata
        self.history = history
        self.migrations = migrations


_LIST_FIELDS = frozenset({
    "A3", "A3_functions", "A3_modalities", "A6", "B1_1", "B1_2", "B4_2a", "B5a", "B5b",
    "B10_current_practices",
})
_DICT_FIELDS = frozenset({"A4a", "A4b", "B2"})
_STRUCTURED_FIELDS = frozenset({"A4c", "A4a_details", "B3a_details", "B4_2c_details", "B11_cop"})
_BOOL_FIELDS = frozenset({"A3_detection", "B1_hardware", "B5b_interactive"})
_STRING_FIELDS = frozenset(KNOWN_KEYS) - _LIST_FIELDS - _DICT_FIELDS - _BOOL_FIELDS
_REQUIRED_CORE = frozenset({"A2", "A3", "A6"})
_JURISDICTIONS = frozenset({"中国大陆", "中国", "CN", "欧盟", "EU", "加州", "CA", "美国加州"})
_A4A_VALUES = frozenset({"0", "趋零", "0/趋零", "<1万", "1-10万", "10-100万", "100万-1000万", "1000万+", "不确定"})
_A4B_VALUES = frozenset({"主动提供", "被动可达", "不确定"})
_A3_FUNCTION_VALUES = frozenset({"生成", "检测", "分析"})
_A3_MODALITY_VALUES = frozenset({"文本", "图像", "音频", "视频", "虚拟场景", "3D", "数字人/虚拟人", "数字人 / 虚拟人"})
_B3A_VALUES = frozenset({"≤100万", "<=100万", ">100万", "不确定"})
_YES_NO_UNKNOWN = frozenset({"是", "否", "不确定"})
_CONTACT_FACTOR_VALUES = frozenset({
    "境内实体", "境内推广", "语言界面", "境内商店上架", "境内支付",
    "当地实体", "当地推广", "当地语言界面", "当地商店上架", "当地支付",
    "加州实体", "面向加州推广", "加州可及商店上架", "加州支付",
    "无", "未发现该因素", "尚未核实", "不确定",
})
_DETAIL_KEYS = {
    "A4a_details": {"metric", "scope", "period", "unique", "raw_value", "source", "notes"},
    "B3a_details": {"metric", "scope", "period", "unique", "raw_value", "source", "notes"},
    "B4_2c_details": {
        "monthly_values", "recipient_users", "creator_or_collaborator_users", "scope",
        "deduplication_method", "threshold_interpretation", "source", "notes",
    },
}
_ENUMS = {
    "B1_3": _YES_NO_UNKNOWN,
    "B1_4": _YES_NO_UNKNOWN,
    "B4_2": _YES_NO_UNKNOWN,
    "B4_2b": _YES_NO_UNKNOWN,
    "B4_2c": frozenset({"≤100万", "<=100万", "100万-200万", ">200万", "不确定"}),
    "B6": _YES_NO_UNKNOWN,
    "B7": _YES_NO_UNKNOWN,
    "B8_1": _YES_NO_UNKNOWN,
    "B8_2": _YES_NO_UNKNOWN,
    "B8_4": frozenset({"是", "否", "部分完成", "不适用", "不确定"}),
    "B9": _YES_NO_UNKNOWN,
    "SB1000_status": frozenset({"待签署", "已签署", "否决", "超期自动生效"}),
}


def _normalise_scalar(value: object) -> object:
    if isinstance(value, str):
        text = value.strip()
        if text in {"不清楚", "不确定（按最严口径）", "不确定(按最严口径)"}:
            return "不确定"
        if text == "<=100万":
            return "≤100万"
        return text
    return value


def _validate_history(history: object) -> list:
    if history is None:
        return []
    if not isinstance(history, list):
        raise AuditFormatError("history: expected array")
    required = {"question", "old", "new", "at", "reason"}
    for index, item in enumerate(history):
        if not isinstance(item, dict):
            raise AuditFormatError(f"history[{index}]: expected object")
        missing = sorted(required - set(item))
        if missing:
            raise AuditFormatError(f"history[{index}]: missing {'、'.join(missing)}")
        if not all(isinstance(item[key], str) for key in required):
            raise AuditFormatError(f"history[{index}]: question/old/new/at/reason must be strings")
    return history


def _normalise_answers(raw: dict) -> tuple[dict, list[str]]:
    """归一化旧皮肤并严格校验答案键、类型和值域。"""
    answers = dict(raw)
    migrations: list[str] = []
    unknown = sorted(k for k in answers if k not in KNOWN_KEYS and k != "session_date")
    if unknown:
        raise AuditFormatError(
            "未知答案键：" + "、".join(unknown) + "。请按 references/survey-audit-schema.md 的题号映射落盘"
        )

    # v1 A6 曾允许单个字符串；显式迁移，避免字符串按字符迭代造成法域漏触发。
    if isinstance(answers.get("A6"), str):
        answers["A6"] = [answers["A6"]]
        migrations.append("A6 scalar -> array")

    # v1 A3 是模态数组；v2 将功能和模态拆开，同时保留 A3 兼容镜像。
    if "A3_modalities" not in answers and "A3" in answers:
        if not isinstance(answers["A3"], list):
            raise AuditFormatError("answers.A3: expected array, got " + type(answers["A3"]).__name__)
        answers["A3_modalities"] = list(answers["A3"])
        if "A3_functions" not in answers:
            if answers.get("A3_detection") is True and answers.get("A1") == "不适用":
                answers["A3_functions"] = ["检测"]
                answers["A3_modalities"] = []
            else:
                answers["A3_functions"] = ["生成"] if answers["A3"] else []
                if answers.get("A3_detection") is True:
                    answers["A3_functions"].append("检测")
        migrations.append("A3 legacy modalities -> A3_modalities/A3_functions")
    if "A3" not in answers and "A3_modalities" in answers:
        functions = answers.get("A3_functions") or []
        is_generation = any(item in {"生成", "生成式", "生成内容"} for item in functions)
        answers["A3"] = answers["A3_modalities"] if is_generation else []
        migrations.append("A3_modalities -> A3 compatibility mirror")

    for key, value in list(answers.items()):
        if key == "session_date":
            if not isinstance(value, str) or not value.strip():
                raise AuditFormatError("answers.session_date: expected non-empty string")
            answers[key] = value.strip()
        elif key in _LIST_FIELDS:
            if not isinstance(value, list):
                raise AuditFormatError(f"answers.{key}: expected array, got {type(value).__name__}")
            if not all(isinstance(item, str) for item in value):
                raise AuditFormatError(f"answers.{key}: array items must be strings")
            answers[key] = [_normalise_scalar(item) for item in value]
        elif key in _STRUCTURED_FIELDS:
            if not isinstance(value, dict):
                raise AuditFormatError(f"answers.{key}: expected object, got {type(value).__name__}")
            if key == "B11_cop":
                bad = sorted(set(value) - {"status", "sections"})
                if bad:
                    raise AuditFormatError(f"answers.B11_cop: unknown field(s): {'、'.join(bad)}")
                status = _normalise_scalar(value.get("status"))
                sections = value.get("sections", [])
                if status not in {"已签署", "计划签署", "未签署", "不确定"}:
                    raise AuditFormatError(f"answers.B11_cop.status: invalid value {status!r}")
                if not isinstance(sections, list) or not all(isinstance(item, str) for item in sections):
                    raise AuditFormatError("answers.B11_cop.sections: expected string array")
                sections = [_normalise_scalar(item) for item in sections]
                invalid = [item for item in sections if item not in {"Section 1", "Section 2"}]
                if invalid:
                    raise AuditFormatError(
                        "answers.B11_cop.sections: invalid value(s): " + "、".join(invalid)
                    )
                if len(sections) != len(set(sections)):
                    raise AuditFormatError("answers.B11_cop.sections: duplicate Section")
                if status in {"已签署", "计划签署"} and not sections:
                    raise AuditFormatError("answers.B11_cop.sections: 已签署/计划签署时至少选择一个Section")
                if status == "未签署" and sections:
                    raise AuditFormatError("answers.B11_cop.sections: 未签署时须为空数组")
                answers[key] = {"status": status, "sections": sections}
                continue
            answers[key] = value
        elif key in _DICT_FIELDS:
            if not isinstance(value, dict):
                raise AuditFormatError(f"answers.{key}: expected object, got {type(value).__name__}")
            if key == "B2":
                bad = sorted(set(value) - {"a", "b"})
                if bad:
                    raise AuditFormatError(f"answers.B2: unknown child key(s): {'、'.join(bad)}")
                if any(child not in value for child in ("a", "b")):
                    raise AuditFormatError("answers.B2: child keys a and b are required when B2 is present")
            answers[key] = {str(child): _normalise_scalar(item) for child, item in value.items()}
        elif key in _BOOL_FIELDS:
            if not isinstance(value, bool):
                raise AuditFormatError(f"answers.{key}: expected boolean, got {type(value).__name__}")
        elif key in _STRING_FIELDS:
            if not isinstance(value, str):
                raise AuditFormatError(f"answers.{key}: expected string, got {type(value).__name__}")
            answers[key] = _normalise_scalar(value)

    for key, allowed in _ENUMS.items():
        value = answers.get(key)
        if value is not None and value not in allowed:
            raise AuditFormatError(f"answers.{key}: value {value!r} not in allowed set ({'、'.join(sorted(allowed))})")
    if "A6" in answers:
        invalid = [value for value in answers["A6"] if value not in _JURISDICTIONS]
        if invalid:
            raise AuditFormatError(f"answers.A6: unknown jurisdiction value(s): {'、'.join(invalid)}")
    if "A3_functions" in answers:
        invalid = [value for value in answers["A3_functions"] if value not in _A3_FUNCTION_VALUES]
        if invalid:
            raise AuditFormatError(f"answers.A3_functions: invalid value(s): {'、'.join(invalid)}")
    if "A3_modalities" in answers:
        invalid = [value for value in answers["A3_modalities"] if value not in _A3_MODALITY_VALUES]
        if invalid:
            raise AuditFormatError(f"answers.A3_modalities: invalid value(s): {'、'.join(invalid)}")
        if answers.get("A3_functions") and "生成" not in answers["A3_functions"] and answers["A3_modalities"]:
            raise AuditFormatError("answers.A3_modalities: non-empty output modalities require A3_functions to include 生成")
    if "A4a" in answers:
        invalid = [f"{jur}={value}" for jur, value in answers["A4a"].items() if value not in _A4A_VALUES]
        if invalid:
            raise AuditFormatError("answers.A4a: invalid band(s): " + "、".join(invalid))
    if "A4b" in answers:
        invalid = [f"{jur}={value}" for jur, value in answers["A4b"].items() if value not in _A4B_VALUES]
        if invalid:
            raise AuditFormatError("answers.A4b: invalid access mode(s): " + "、".join(invalid))
    if "A4c" in answers:
        for jur, factors in answers["A4c"].items():
            if not isinstance(factors, list) or not all(isinstance(item, str) for item in factors):
                raise AuditFormatError(f"answers.A4c[{jur}]: expected string array")
            invalid = [item for item in factors if item not in _CONTACT_FACTOR_VALUES]
            if invalid:
                raise AuditFormatError(f"answers.A4c[{jur}]: invalid factor(s): {'、'.join(invalid)}")
    for key, allowed in _DETAIL_KEYS.items():
        if key not in answers:
            continue
        value = answers[key]
        if key == "A4a_details":
            for jur, detail in value.items():
                if jur not in _JURISDICTIONS:
                    raise AuditFormatError(f"answers.A4a_details: unknown jurisdiction {jur!r}")
                if not isinstance(detail, dict):
                    raise AuditFormatError(f"answers.A4a_details[{jur}]: expected object")
                bad = sorted(set(detail) - allowed)
                if bad:
                    raise AuditFormatError(f"answers.A4a_details[{jur}]: unknown field(s): {'、'.join(bad)}")
            continue
        bad = sorted(set(value) - allowed)
        if bad:
            raise AuditFormatError(f"answers.{key}: unknown field(s): {'、'.join(bad)}")
        if key == "B4_2c_details":
            for field in ("monthly_values", "recipient_users", "creator_or_collaborator_users"):
                if field in value and not isinstance(value[field], list):
                    raise AuditFormatError(f"answers.{key}.{field}: expected array")
        for field, field_value in value.items():
            if field in {"monthly_values", "recipient_users", "creator_or_collaborator_users"}:
                continue
            if not isinstance(field_value, (str, int, float, bool)) and field_value is not None:
                raise AuditFormatError(f"answers.{key}.{field}: expected scalar value")
    if "B3a" in answers and answers["B3a"] not in _B3A_VALUES:
        raise AuditFormatError(f"answers.B3a: invalid band {answers['B3a']!r}")

    missing = sorted(_REQUIRED_CORE - set(answers))
    if missing:
        raise AuditFormatError("缺少核心答案：" + "、".join(missing) + "（至少需要 A2、A3、A6，未执行触发判断）")
    return answers, migrations


def read_json(path: Path) -> dict:
    """以 utf-8-sig 读取 JSON 对象；任何失败都转成 AuditFormatError。"""
    p = Path(path)
    if not p.exists():
        raise AuditFormatError(f"文件不存在：{p}")
    try:
        text = p.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise AuditFormatError(f"无法读取文件：{p}（{exc}）") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AuditFormatError(
            f"JSON 解析失败：{p}（{exc.msg}，行 {exc.lineno} 列 {exc.colno}）"
        ) from exc
    if not isinstance(data, dict):
        raise AuditFormatError(f"顶层须为对象：{p}")
    return data


def _looks_like_answer_key(key: str) -> bool:
    if key in META_KEYS:
        return False
    if key in _KEY_PREFIX_EXCEPTIONS:
        return False
    return bool(_ANSWER_KEY_RE.match(key))


def recognised_keys(answers: dict) -> list[str]:
    """返回已识别的答案键（含未列入 KNOWN_KEYS 的增量题，如 A8/B10）。"""
    return sorted(k for k in answers if k in KNOWN_KEYS or _looks_like_answer_key(k))


def unwrap(data: dict, source: str = "survey_audit.json") -> AuditBundle:
    """按契约解包、迁移并校验，返回兼容 dict 接口的完整 AuditBundle。"""
    schema = data.get("schema")
    if schema and schema not in SUPPORTED_SCHEMA_IDS:
        raise AuditFormatError(f"未知 schema：{schema}（支持 {'、'.join(sorted(SUPPORTED_SCHEMA_IDS))}）")

    inner = data.get("answers")
    if inner is None:
        answers = {k: v for k, v in data.items() if k not in META_KEYS}
    elif isinstance(inner, dict):
        answers = dict(inner)
    else:
        raise AuditFormatError("answers 字段须为对象")

    if not answers:
        raise AuditFormatError(
            f"答案为空：{source}。若按嵌套结构落盘，请检查 answers 层是否漏填；"
            "若为扁平结构，请检查是否只有元数据而无答案键"
        )
    if not recognised_keys(answers):
        raise AuditFormatError(
            f"未识别到任何答案键：{source}。答案键应为 A×/B×/SB1000_status 形式"
            "（契约见 references/survey-audit-schema.md）"
        )

    if "session_date" not in answers and data.get("session_date"):
        answers["session_date"] = data["session_date"]
    answers, migrations = _normalise_answers(answers)
    history = _validate_history(data.get("history", []))
    metadata = {key: data[key] for key in ("schema", "report", "session_date") if key in data}
    metadata.setdefault("schema", schema or LEGACY_SCHEMA_ID)
    return AuditBundle(answers, metadata=metadata, history=history, migrations=migrations)


def load_audit(path: Path) -> AuditBundle:
    """读取并严格校验答案，失败由调用方转换为退出码 2。

    失败一律抛 AuditFormatError，调用方应转退出码 2，**不得**退化为「无答案即无矛盾」。
    """
    p = Path(path)
    return unwrap(read_json(p), source=str(p))
