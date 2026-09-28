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
1. **结构校验**：顶层须为对象；`schema` 若存在须为 `survey_audit/3` 或兼容读取的 `survey_audit/1`、`survey_audit/2`；按嵌套或扁平解包后，
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

CURRENT_SCHEMA_ID = "survey_audit/3"
LEGACY_SCHEMA_ID = "survey_audit/1"
LEGACY_SCHEMA_IDS = frozenset({LEGACY_SCHEMA_ID, "survey_audit/2"})
SUPPORTED_SCHEMA_IDS = LEGACY_SCHEMA_IDS | {CURRENT_SCHEMA_ID}
# 对外别名始终表示当前写入版本；历史读取兼容由 LEGACY_SCHEMA_IDS 单独维护。
SCHEMA_ID = CURRENT_SCHEMA_ID

# 元数据键：不属于答案，解包时不混入答案空间
META_KEYS = frozenset({"schema", "report", "session_date", "history", "answers"})

# 已识别答案键（用于「读到了答案」与「答案为空」的区分）
KNOWN_KEYS = frozenset(
    {
        "A1", "A2", "A3", "A3_functions", "A3_modalities", "A3_detection", "A4a", "A4b", "A4c", "A4a_details", "A5", "A6", "A7",
        "A8_report_language", "A8_footnote_original_text",
        "B1_1", "B1_2", "B1_3", "B1_4", "B1_hardware",
        "B2", "B3a", "B3a_details",
        "B4_1", "B4_2", "B4_2a", "B4_2b", "B4_2c", "B4_2c_details",
        "B5a", "B5b", "B5b_interactive", "B5b_chat_status", "B5b_other_chat_confirmed", "chat_confirmed",
        "B6", "B6_deepfake", "B7", "B8_1", "B8_2", "B8_3", "B8_4", "B9", "B10_current_practices", "B11_cop",
        "B12", "B12_companion_status", "B12_human_misidentification_status", "B13", "B13_gate",
        "scale_facts", "AB1609_status", "AB1609_recheck",
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
_DICT_FIELDS = frozenset({"A4a", "A4b"})
_STRUCTURED_FIELDS = frozenset({
    "A4c", "A4a_details", "B3a_details", "B4_2c_details", "B11_cop",
    "B12", "B13", "AB1609_recheck",
})
_BOOL_FIELDS = frozenset({"A3_detection", "B1_hardware", "B5b_interactive", "B5b_other_chat_confirmed"})
_STRING_FIELDS = frozenset(KNOWN_KEYS) - _LIST_FIELDS - _DICT_FIELDS - _BOOL_FIELDS
_REQUIRED_CORE = frozenset({"A2", "A3", "A6"})
_JURISDICTIONS = frozenset({"中国大陆", "中国", "CN", "欧盟", "EU", "加州", "CA", "美国加州"})
_A4A_VALUES = frozenset({"0", "趋零", "0/趋零", "<1万", "1-10万", "10-100万", "100万-1000万", "1000万+", "不确定"})
_A4B_VALUES = frozenset({"主动提供", "被动可达", "不确定"})
_A3_FUNCTION_VALUES = frozenset({"生成", "检测", "分析"})
_A3_MODALITY_VALUES = frozenset({"文本", "图像", "音频", "视频", "虚拟场景", "3D", "数字人/虚拟人", "数字人 / 虚拟人"})
_B3A_VALUES = frozenset({"≤100万", "<=100万", ">100万", "不确定"})
_YES_NO_UNKNOWN = frozenset({"是", "否", "不确定"})
_B2_RELATIONSHIPS = frozenset({"自研", "部分自研", "授权接入", "开源微调", "其它", "不适用"})
_B2_A_VALUES = _YES_NO_UNKNOWN | {"不适用"}
_B2_B_VALUES = frozenset({"有且下游可依赖", "无约定", "不确定", "不适用"})
# B4_2a 元素级封闭值域（2026-09-27 用户裁定：立即加白名单）。
# 允许值＝四类法定平台（§22757.1(i)(1)〔SB 1000〕/§22757.1(h)(1)〔现行法〕封闭列举）＋「其它」＋「不确定」。
# 四类法定平台与 `lookups.CA_LOP_CLOSED_CATEGORIES` 必须逐字一致——tests 以机械断言防两处漂移。
# 自造值、空字符串、标量、混合非法数组一律结构错误（退出码 2）；不得静默归一或降级。
_B4_2A_VALUES = frozenset({
    "社交媒体平台", "文件分享平台", "群发消息平台", "独立搜索引擎", "其它", "不确定",
})
# 数组字段的元素级值域（键须同时在 _LIST_FIELDS 内才生效）
_LIST_ENUMS: dict[str, frozenset] = {"B4_2a": _B4_2A_VALUES}
_TRI_STATE = frozenset({"yes", "no", "unknown"})
# agent2（2026-09-28）：交付偏好（A8）与 B13 总闸门封闭值域
_REPORT_LANGUAGE = frozenset({"纯中文", "中英双语", "不确定"})
_FOOTNOTE_PREF = frozenset({"是", "否", "不确定"})
_B13_GATE_VALUES = frozenset({"两类都有", "只自产广告", "只投放第三方", "都没有", "不确定"})
_B10_VALUES = frozenset({
    "界面文字或语音提示", "画面角标或可见标记", "隐式标识（元数据/水印）",
    "仅合同或条款约定", "AI交互身份提示", "未成年人适龄AI身份提示",
    "长时间互动周期提示", "合成表演者广告披露", "尚未实施",
})
_B12_USE_CASES = frozenset({
    "陪伴/虚拟角色", "客服", "企业运营", "基于源信息的生产力或分析",
    "内部研究", "技术支持", "游戏功能", "独立语音助手", "其它",
})
_B12_HUMAN_IDENTITY_SIGNALS = frozenset({
    "自称或暗示真人", "使用真人姓名或照片", "使用员工等真人身份",
    "叙述第一人称真人经历", "其它可能造成真人印象的线索", "以上皆无", "不确定",
})
_B12_CHILD_ACCESS_POLICY = frozenset({"allowed", "prohibited", "not_established", "unknown"})
_B12_CHILD_AFTER_AGE_CHECK = frozenset({"allow", "block", "undecided", "unknown"})
_B12_ACCESS_CONTEXT = frozenset({
    "general", "higher_education_only", "workplace_only", "mixed", "other", "unknown",
})
_B13_ROLES = frozenset({"creator", "advertising_medium", "both", "none", "unknown"})
_B13_PROMINENT_USE = frozenset({
    "foreground_demonstration", "narration_or_commercial_message",
    "explain_or_respond_to_commercial_message", "none", "unknown",
})
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
    # B-7（2026-09-23）：欧盟 Art. 50(4) 第 1-2 项（深度伪造）的独立落盘位。
    # 与 B6（第 3 项·公共利益文本）**同卡采集、各自落盘**：单一定义点仍归
    # B13 `identifiable_natural_person`（「可辨识自然人」不在第三处重复定义）。
    "B6_deepfake": _YES_NO_UNKNOWN,
    "B7": _YES_NO_UNKNOWN,
    "B8_1": _YES_NO_UNKNOWN,
    "B8_2": _YES_NO_UNKNOWN,
    "B8_4": frozenset({"是", "否", "部分完成", "不适用", "不确定"}),
    "B9": _YES_NO_UNKNOWN,
    "B5b_chat_status": _TRI_STATE,
    "chat_confirmed": _TRI_STATE,
    "A8_report_language": _REPORT_LANGUAGE,
    "A8_footnote_original_text": _FOOTNOTE_PREF,
    "B13_gate": _B13_GATE_VALUES,
    "B12_companion_status": frozenset({"yes", "no", "conditional"}),
    "B12_human_misidentification_status": frozenset({"yes", "no", "conditional"}),
    "AB1609_status": frozenset({
        "pending_governor", "signed_not_effective", "effective", "vetoed", "became_law_without_signature"
    }),
    "SB1000_status": frozenset({"待签署", "已签署", "否决", "超期自动生效"}),
}


def _normalise_scalar(value: object) -> object:
    if isinstance(value, str):
        text = value.strip()
        if text in {"不清楚", "不确定（按最严口径）", "不确定(按最严口径)"}:
            return "不确定"
        if text == "<=100万":
            return "≤100万"
        # 呈现层选项字面 → 落盘规范值（题面「其它（请补充）」，落盘统一「其它」）。
        # 仅映射选项字面本身；「其它:…」「其它：…」一类**混合了补充文本**的值不得在此归一，
        # 须由白名单判为结构错误、回原始问卷后手工归一（见 survey-audit-schema.md）。
        if text in {"其它（请补充）", "其它(请补充)"}:
            return "其它"
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


def _normalise_b2(value: object, *, schema_id: str | None, migrations: list[str]) -> dict:
    """校验 B2 主问题与两项上游追问；v1/v2 仅兼容旧形状。"""
    current = schema_id == CURRENT_SCHEMA_ID
    if isinstance(value, str):
        if current:
            raise AuditFormatError("answers.B2: survey_audit/3 须为结构化对象，不再接受字符串")
        text = str(_normalise_scalar(value))
        if not text:
            raise AuditFormatError("answers.B2: legacy string must be non-empty")
        migrations.append("B2 legacy scalar -> B2.legacy_text")
        return {"legacy_text": text}
    if not isinstance(value, dict):
        raise AuditFormatError(f"answers.B2: expected object, got {type(value).__name__}")

    allowed = {"relationship", "own_name", "relationship_details", "presentation_details", "a", "b"}
    if not current:
        allowed.add("legacy_text")
    bad = sorted(set(value) - allowed)
    if bad:
        raise AuditFormatError(f"answers.B2: unknown child key(s): {'、'.join(bad)}")

    normalised = {str(child): _normalise_scalar(item) for child, item in value.items()}
    canonical = {"relationship", "own_name", "a", "b"}
    missing = sorted(canonical - set(normalised))
    if missing:
        if current:
            raise AuditFormatError(
                "answers.B2: survey_audit/3 缺少规范子键 " + "、".join(missing)
            )
        if set(normalised) == {"legacy_text"}:
            return normalised
        if set(normalised) <= {"a", "b"} and {"a", "b"} <= set(normalised):
            migrations.append("B2 legacy a/b object retained; relationship/own_name unavailable")
        else:
            raise AuditFormatError(
                "answers.B2: legacy object须为a/b旧形状，或包含完整规范子键relationship/own_name/a/b"
            )

    if "a" in normalised and normalised["a"] not in _B2_A_VALUES:
        raise AuditFormatError(f"answers.B2.a: invalid value {normalised['a']!r}")
    if "b" in normalised and normalised["b"] not in _B2_B_VALUES:
        raise AuditFormatError(f"answers.B2.b: invalid value {normalised['b']!r}")
    if missing:
        return normalised

    relationship = normalised["relationship"]
    own_name = normalised["own_name"]
    if relationship not in _B2_RELATIONSHIPS:
        raise AuditFormatError(f"answers.B2.relationship: invalid value {relationship!r}")
    if own_name not in _YES_NO_UNKNOWN:
        raise AuditFormatError(f"answers.B2.own_name: invalid value {own_name!r}")
    for detail in ("relationship_details", "presentation_details"):
        if detail in normalised and (
            not isinstance(normalised[detail], str) or not normalised[detail].strip()
        ):
            raise AuditFormatError(f"answers.B2.{detail}: expected non-empty string")
    if relationship == "其它" and "relationship_details" not in normalised:
        raise AuditFormatError("answers.B2.relationship_details: relationship=其它时必填")
    if own_name == "否" and "presentation_details" not in normalised:
        raise AuditFormatError("answers.B2.presentation_details: own_name=否时须记录品牌/界面/合同归属")

    upstream = relationship in {"部分自研", "授权接入", "开源微调", "其它"}
    if upstream and (normalised["a"] == "不适用" or normalised["b"] == "不适用"):
        raise AuditFormatError("answers.B2: 存在第三方生成来源时a/b不得填不适用")
    if not upstream and (normalised["a"] != "不适用" or normalised["b"] != "不适用"):
        raise AuditFormatError("answers.B2: 自研/不适用路径未展开a/b时，两项均须填不适用")
    return normalised


def _normalise_answers(raw: dict, *, schema_id: str | None = None) -> tuple[dict, list[str]]:
    """归一化旧皮肤并严格校验答案键、类型和值域。

    本层只负责**结构与值域**（键集、类型、枚举/档位闭集）。跨题的分支条件约束
    （如「平台候选成立时门槛口径卡不得缺席」，见 F-4）属答案级语义校验，
    落在 ``resolve_triggers.cross_check_scale``，由两个入口统一调用，
    以保持与同族规则（`B4_2c_details.monthly_values`）**同一层级、同一退出码**。
    """
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
            items = [_normalise_scalar(item) for item in value]
            blank = [index for index, item in enumerate(items) if not item.strip()]
            if blank:
                raise AuditFormatError(
                    f"answers.{key}: array items must be non-empty "
                    f"(index {'、'.join(map(str, blank))})"
                )
            allowed = _LIST_ENUMS.get(key)
            if allowed is not None:
                invalid = sorted({item for item in items if item not in allowed})
                if invalid:
                    raise AuditFormatError(
                        f"answers.{key}: invalid value(s): " + "、".join(invalid)
                    )
            answers[key] = items
        elif key == "scale_facts":
            if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
                raise AuditFormatError("answers.scale_facts: expected object array")
            required = {"subject", "geography", "period", "dedup_method", "range", "source", "confirmed"}
            for index, item in enumerate(value):
                missing = sorted(required - set(item))
                if missing:
                    raise AuditFormatError(
                        f"answers.scale_facts[{index}]: missing {'、'.join(missing)}"
                    )
                bad = sorted(set(item) - required)
                if bad:
                    raise AuditFormatError(
                        f"answers.scale_facts[{index}]: unknown field(s): {'、'.join(bad)}"
                    )
                if not isinstance(item.get("confirmed"), bool):
                    raise AuditFormatError(f"answers.scale_facts[{index}].confirmed: expected boolean")
                for field in required - {"confirmed"}:
                    if not isinstance(item.get(field), str) or not item[field].strip():
                        raise AuditFormatError(f"answers.scale_facts[{index}].{field}: expected non-empty string")
            answers[key] = value
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
            if key == "B12":
                allowed = {
                    "natural_language_interface", "adaptive_humanlike_responses",
                    "social_or_emotional_function", "sustains_relationship", "use_cases",
                    "use_cases_other",
                    "game_scope_limited", "standalone_voice_device", "voice_emotional_output",
                    "human_identity_signals", "human_identity_signals_other",
                    "fictional_or_ai_framing", "child_access_policy",
                    "minor_access_in_fact", "known_minor_users", "minor_identification_capability",
                    "age_determination", "all_user_child_protections",
                    "child_access_after_age_check", "access_context",
                }
                bad = sorted(set(value) - allowed)
                if bad:
                    raise AuditFormatError(f"answers.B12: unknown field(s): {'、'.join(bad)}")
                for field in (
                    "natural_language_interface", "adaptive_humanlike_responses",
                    "social_or_emotional_function", "sustains_relationship", "game_scope_limited",
                    "standalone_voice_device", "voice_emotional_output", "minor_access_in_fact",
                    "known_minor_users", "minor_identification_capability", "age_determination",
                    "all_user_child_protections", "fictional_or_ai_framing",
                ):
                    if field in value and value[field] not in _TRI_STATE:
                        raise AuditFormatError(f"answers.B12.{field}: invalid tri-state {value[field]!r}")
                for field in ("use_cases", "human_identity_signals"):
                    if field in value:
                        if not isinstance(value[field], list) or not all(isinstance(item, str) for item in value[field]):
                            raise AuditFormatError(f"answers.B12.{field}: expected string array")
                invalid_uses = sorted(set(value.get("use_cases", [])) - _B12_USE_CASES)
                if invalid_uses:
                    raise AuditFormatError("answers.B12.use_cases: invalid value(s): " + "、".join(invalid_uses))
                use_cases_other = value.get("use_cases_other")
                if ("其它" in set(value.get("use_cases", []))) != bool(
                    isinstance(use_cases_other, str) and use_cases_other.strip()
                ):
                    raise AuditFormatError(
                        "answers.B12.use_cases_other: 仅选择其它时填写，且须为非空字符串"
                    )
                identity_signals = value.get("human_identity_signals", [])
                invalid_signals = sorted(set(identity_signals) - _B12_HUMAN_IDENTITY_SIGNALS)
                if invalid_signals:
                    raise AuditFormatError(
                        "answers.B12.human_identity_signals: invalid value(s): "
                        + "、".join(invalid_signals)
                    )
                if len(identity_signals) != len(set(identity_signals)):
                    raise AuditFormatError("answers.B12.human_identity_signals: duplicate value")
                if len(identity_signals) > 1 and ({"以上皆无", "不确定"} & set(identity_signals)):
                    raise AuditFormatError(
                        "answers.B12.human_identity_signals: 以上皆无/不确定不能与其它值并存"
                    )
                identity_other = value.get("human_identity_signals_other")
                if ("其它可能造成真人印象的线索" in set(identity_signals)) != bool(
                    isinstance(identity_other, str) and identity_other.strip()
                ):
                    raise AuditFormatError(
                        "answers.B12.human_identity_signals_other: 仅选择其它线索时填写，且须为非空字符串"
                    )
                if "child_access_policy" in value and value["child_access_policy"] not in _B12_CHILD_ACCESS_POLICY:
                    raise AuditFormatError(
                        f"answers.B12.child_access_policy: invalid value {value['child_access_policy']!r}"
                    )
                if "child_access_after_age_check" in value and value["child_access_after_age_check"] not in _B12_CHILD_AFTER_AGE_CHECK:
                    raise AuditFormatError(
                        "answers.B12.child_access_after_age_check: invalid value "
                        f"{value['child_access_after_age_check']!r}"
                    )
                if "access_context" in value and value["access_context"] not in _B12_ACCESS_CONTEXT:
                    raise AuditFormatError(f"answers.B12.access_context: invalid value {value['access_context']!r}")
                answers[key] = value
                continue
            if key == "B13":
                allowed = {
                    "role", "commercial_advertisement", "genai_human_performance",
                    "identifiable_natural_person", "prominent_use", "expressive_work_ad_present",
                    "expressive_work",
                    "use_consistent_within_work",
                    "translation_only", "accessibility_only", "court_order_status",
                }
                bad = sorted(set(value) - allowed)
                if bad:
                    raise AuditFormatError(f"answers.B13: unknown field(s): {'、'.join(bad)}")
                role = value.get("role")
                if role not in _B13_ROLES:
                    raise AuditFormatError(f"answers.B13.role: invalid or missing value {role!r}")
                creator_fields = {
                    "commercial_advertisement", "genai_human_performance",
                    "identifiable_natural_person", "prominent_use", "expressive_work_ad_present",
                    "expressive_work", "use_consistent_within_work",
                    "translation_only", "accessibility_only",
                }
                if role in {"none", "unknown"} and set(value) != {"role"}:
                    raise AuditFormatError(f"answers.B13: role={role}时不得包含卡内后续字段")
                if role == "advertising_medium" and (creator_fields & set(value)):
                    raise AuditFormatError("answers.B13: advertising_medium路径不得包含创作者字段")
                if role == "creator" and "court_order_status" in value:
                    raise AuditFormatError("answers.B13: creator路径不得包含广告媒介法院命令字段")
                # agent2（2026-09-28）：4a 前置分流一致性（结构层：仅字段级直接矛盾；
                # 跨键完整性与闸门三向一致性归 resolve_triggers 答案级校验，避免同缺陷双层级）。
                ew_present = value.get("expressive_work_ad_present")
                if ew_present is not None and ew_present not in _TRI_STATE:
                    raise AuditFormatError(
                        f"answers.B13.expressive_work_ad_present: invalid tri-state {ew_present!r}"
                    )
                if ew_present == "no" and (
                    "expressive_work" in value or "use_consistent_within_work" in value
                ):
                    raise AuditFormatError(
                        "answers.B13: expressive_work_ad_present=no 时不得落 expressive_work/"
                        "use_consistent_within_work（4a 前置分流：无作品广告则例外要件不采集）"
                    )
                for field in (
                    "commercial_advertisement", "genai_human_performance",
                    "identifiable_natural_person", "expressive_work_ad_present", "expressive_work", "use_consistent_within_work",
                    "translation_only", "accessibility_only", "court_order_status",
                ):
                    if field in value and value[field] not in _TRI_STATE:
                        raise AuditFormatError(f"answers.B13.{field}: invalid tri-state {value[field]!r}")
                if "prominent_use" in value:
                    prominent = value["prominent_use"]
                    if not isinstance(prominent, list) or not all(isinstance(item, str) for item in prominent):
                        raise AuditFormatError("answers.B13.prominent_use: expected string array")
                    invalid = sorted(set(prominent) - _B13_PROMINENT_USE)
                    if invalid:
                        raise AuditFormatError(
                            "answers.B13.prominent_use: invalid value(s): " + "、".join(invalid)
                        )
                    if len(prominent) != len(set(prominent)):
                        raise AuditFormatError("answers.B13.prominent_use: duplicate value")
                    if len(prominent) > 1 and ({"none", "unknown"} & set(prominent)):
                        raise AuditFormatError(
                            "answers.B13.prominent_use: none/unknown cannot be combined with another value"
                        )
                answers[key] = value
                continue
            if key == "AB1609_recheck":
                allowed = {"recheck_required", "recheck_reason", "recheck_by"}
                bad = sorted(set(value) - allowed)
                if bad:
                    raise AuditFormatError(f"answers.AB1609_recheck: unknown field(s): {'、'.join(bad)}")
                if not isinstance(value.get("recheck_required"), bool):
                    raise AuditFormatError("answers.AB1609_recheck.recheck_required: expected boolean")
                if value["recheck_required"]:
                    if value.get("recheck_reason") != "AB1609_revenue_near_threshold":
                        raise AuditFormatError("answers.AB1609_recheck.recheck_reason: invalid or missing value")
                    if not isinstance(value.get("recheck_by"), str) or not value["recheck_by"].strip():
                        raise AuditFormatError("answers.AB1609_recheck.recheck_by: expected non-empty string")
                answers[key] = value
                continue
            answers[key] = value
        elif key == "B2":
            answers[key] = _normalise_b2(value, schema_id=schema_id, migrations=migrations)
        elif key in _DICT_FIELDS:
            if not isinstance(value, dict):
                raise AuditFormatError(f"answers.{key}: expected object, got {type(value).__name__}")
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
    if "B10_current_practices" in answers:
        invalid = sorted(set(answers["B10_current_practices"]) - _B10_VALUES)
        if invalid:
            raise AuditFormatError("answers.B10_current_practices: invalid value(s): " + "、".join(invalid))
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

    # F-4（2026-09-23）：`B4_2c` 给出确定量级时门槛口径卡（含 large online platform 的
    # 「接收分发内容用户／创作者·协作者用户」法定区分）不得缺席——该要求的触发条件
    # 跨题（`B4_2` 是否为平台候选），非本层可判，故落在
    # `resolve_triggers.cross_check_scale`（答案级、退出码 1），此处不重复实现。
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
    answers, migrations = _normalise_answers(answers, schema_id=schema)
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
