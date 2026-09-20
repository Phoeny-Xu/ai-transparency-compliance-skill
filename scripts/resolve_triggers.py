#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""resolve_triggers.py —— B 组触发引擎 与 问卷答案级交叉校验

定位
----
`assets/modeA-questionnaire.md` 的「B组触发总览表（11 行）」是纯布尔式，过去靠 agent 每轮
复述条件。本脚本把它落成可执行函数：agent 只需喂答案（结构化 JSON），不再复述条件。

三条元规则也被代码锁死
----------------------
1. **触发条件不得锚 A4**（modeA-questionnaire 顶部「触发条件锚定规则（防漂移）」）：A4 对三法域
   逐一采集事实、不设勾选跳过，故「A4含X」恒为真、不能作触发条件。见 `TRIGGER_TABLE`
   的 `depends_on` 字段与 `assert_conditions_not_anchored_on_a4()`。
   注：该规则约束的是「是否问某道 B 题」，不限制答案级校验对 A4 详情的完整性检查；不同统计口径不得直接比较。
2. **规模字段只有在统计对象、地域、周期和去重方法明确且一致时才可比较**；旧版摘要字段缺少这些信息时，不得把全球与法域档位直接比较。
3. **内部不变量**：`TRIGGER_TABLE` 中标注 `always=True` 的行（B2）必须解析为触发。
   该断言的作用是防「答案根本没读到」被当成「答案无矛盾」：案例16-18 轮发现，若输入
   结构不符（如按文档样例落盘而脚本未解包 answers），全部触发行会静默塌成 1 行。
4. **B5a 勾选的高仿真能力必须与 A3 输出模态相容**（2026-09-19 新增，单向防过度勾选）：
   纯文本产品误勾「数字人／人脸生成／沉浸式拟真场景」等客观不可能的组合即报警。
   反方向（A3 含模态而 B5a 未勾）不代码化——「风景图／无人脸视频」可合法不勾，
   属人工按 modeA-questionnaire「B5a判定备注」五条映射追问的范畴。

用法
----
    python resolve_triggers.py survey_audit.json
    python resolve_triggers.py --demo

输入契约见 `references/survey-audit-schema.md`，读取统一走 `scripts/survey_io.py`
（嵌套与扁平两种结构都收，读取失败硬失败、不静默降级）。

退出码
------
    0 = 通过
    1 = 答案级问题（档位交叉矛盾、能力与模态矛盾，或答案值无法识别——须弹窗澄清后修订 answers）
    2 = 未执行（输入缺失、结构不符、JSON 解析失败、内部不变量违反）
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import survey_io  # noqa: E402  （统一读取，见 survey_io 模块头）

# ---------------------------------------------------------------------------
# 档位序数（仅用于各自摘要字段的范围检查；不同统计口径不得直接比较）
# ---------------------------------------------------------------------------

SCALE_ORDINAL = {
    "0": 0,
    "趋零": 0,
    "0/趋零": 0,
    "<1万": 1,
    "1-10万": 2,
    "10-100万": 3,
    "100万-1000万": 4,
    "1000万+": 5,
}

# B3a 档位覆盖的序数区间
B3A_RANGE = {
    "≤100万": (0, 3),
    "<=100万": (0, 3),
    ">100万": (4, 5),
    "不确定": None,
}

# B4_2c（内容传播平台过去 12 个月独立月用户）档位序数
B4_2C_ORDINAL = {
    "≤100万": 3,
    "<=100万": 3,
    "100万-200万": 4,
    ">200万": 5,
}

NATIONAL = {"中国", "中国大陆", "CN", "欧盟", "EU", "加州", "CA", "美国加州"}


# ---------------------------------------------------------------------------
# 触发表（声明式；depends_on 用于「不得锚 A4」断言）
# ---------------------------------------------------------------------------


def _a6_has(answers: dict, name: str) -> bool:
    values = answers.get("A6", [])
    if isinstance(values, str):
        values = [values]
    return any(name in str(v) for v in values)


def _a3_modalities(answers: dict) -> list[str]:
    """读取拆分后的输出模态；旧 v1 答案回退到 A3。"""
    values = answers.get("A3_modalities")
    if values is None:
        values = answers.get("A3") or []
    if isinstance(values, str):
        values = [values]
    return [str(value).strip() for value in values if str(value).strip()]


def _a3_generates(answers: dict) -> bool:
    """只有功能明确含生成时才视为生成式产品；v1 A3 非空仍按旧语义迁移。"""
    functions = answers.get("A3_functions")
    if functions is None:
        return bool(_a3_modalities(answers))
    if isinstance(functions, str):
        functions = [functions]
    return any(any(token in str(item) for token in ("生成", "生成式", "生成内容")) for item in functions)


def _a3_any(answers: dict, keys: tuple[str, ...]) -> bool:
    return any(any(k in value for k in keys) for value in _a3_modalities(answers))


# B5b 交互布尔的显式值域（N-6，2026-09-19）：缺省 True（最严口径，与
# modeA-questionnaire-business「`B5b_interactive` 派生规则」一致：仅「无自然人直接交互界面」
# 为 false，其余含「不确定」皆为 true）。若该键被落盘为字符串（如「否」），裸 `bool("否")`
# 恒为 True 会静默误触发；故显式判值域，只有真·假值才判 False。
_B5B_FALSE_STRINGS = frozenset({"否", "false", "no", "n", "0", "无", "不"})


def _b5b_interactive(answers: dict) -> bool:
    value = answers.get("B5b_interactive")
    if value is None:
        return True  # 未采集 → 最严口径（触发），不得因缺键静默漏采
    if isinstance(value, str):
        return value.strip().lower() not in _B5B_FALSE_STRINGS
    return bool(value)


TRIGGER_TABLE: list[dict] = [
    {
        "id": "B1",
        "depends_on": {"A2"},
        "cond": lambda a: a.get("A2") not in (None, "仅内部使用"),
        "desc": "A2≠仅内部使用",
    },
    {
        "id": "B2",
        "depends_on": set(),
        "cond": lambda a: True,
        "always": True,  # 内部不变量锚点：见 resolve_triggers() 的断言
        "desc": "恒触发（上游关系子问仅在 A1=否/部分时展开）",
    },
    {
        "id": "B3a",
        "depends_on": {"A6"},
        "cond": lambda a: _a6_has(a, "加州"),
        "desc": "A6含加州",
    },
    {
        "id": "B4",
        "depends_on": {"A2"},
        "cond": lambda a: a.get("A2") not in (None, "仅内部使用"),
        "desc": "A2≠仅内部使用",
    },
    {
        "id": "B5a",
        "depends_on": {"A6", "A3"},
        "cond": lambda a: _a6_has(a, "中国") and _a3_generates(a),
        "desc": "A6含中国 且 A3含任一生成模态",
    },
    {
        "id": "B5b",
        "depends_on": {"A6"},
        "cond": lambda a: _a6_has(a, "欧盟") and _b5b_interactive(a),
        "desc": "A6含欧盟 且产品与自然人交互",
    },
    {
        "id": "B6",
        "depends_on": {"A6", "A3"},
        "cond": lambda a: _a6_has(a, "欧盟") and _a3_any(a, ("文本",)),
        "desc": "A3含文本 且 A6含欧盟（①承担门控）",
    },
    {
        "id": "B7",
        "depends_on": {"B1_1"},
        "cond": lambda a: bool(a.get("B1_hardware")) or "硬件" in str(a.get("B1_1", [])),
        "desc": "B1①选硬件设备，或初始描述涉及硬件",
    },
    {
        "id": "B8-1~4",
        "depends_on": {"A6"},
        "cond": lambda a: _a6_has(a, "中国"),
        "desc": "A6含中国",
    },
    {
        "id": "B9",
        "depends_on": {"A6"},
        "cond": lambda a: _a6_has(a, "欧盟"),
        "desc": "A6含欧盟",
    },
    {
        "id": "B10",
        "depends_on": {"A3"},
        "cond": lambda a: _a3_generates(a),
        "desc": "A3功能含生成且有输出模态（纯分析/检测型不问）",
    },
]


class AnchorViolation(AssertionError):
    pass


class InvariantViolation(AssertionError):
    """触发表内部不变量被破坏（多与「答案没读到」同源）。"""


def assert_conditions_not_anchored_on_a4() -> None:
    """元规则锁死：任何 B 组触发条件都不得引用 A4（modeA-questionnaire 防漂移规则）。"""
    offenders = [row["id"] for row in TRIGGER_TABLE if "A4" in row["depends_on"]]
    if offenders:
        raise AnchorViolation(
            f"触发条件锚定了 A4（违反 modeA-questionnaire「触发条件锚定规则」）：{', '.join(offenders)}"
        )


def always_true_ids() -> list[str]:
    """声明为恒触发的行（数据驱动，避免用「恰好返回 True 的 lambda」当不变量）。"""
    return [row["id"] for row in TRIGGER_TABLE if row.get("always")]


def resolve_triggers(answers: dict) -> list[str]:
    assert_conditions_not_anchored_on_a4()
    triggered = [row["id"] for row in TRIGGER_TABLE if row["cond"](answers)]
    missing = [tid for tid in always_true_ids() if tid not in triggered]
    if missing:
        raise InvariantViolation(
            "触发表内部不变量被破坏：恒触发行未解析为触发（"
            + ", ".join(missing)
            + "）。通常意味着答案未被正确读取，请检查 survey_audit.json 结构"
        )
    return triggered


def china_connection_points(answers: dict) -> dict[str, str]:
    """按义务连接点返回 true/false/unknown，不把中国法域当作单一总开关。"""
    a4b = answers.get("A4b") or {}
    cn_access = a4b.get("中国") if isinstance(a4b, dict) else None
    if cn_access == "不确定":
        domestic_application = "unknown"
    else:
        domestic_application = "true" if cn_access in {"主动提供", "被动可达"} else "unknown"
    public_service = "unknown" if answers.get("A2") in {None, "不确定"} else (
        "false" if answers.get("A2") == "仅内部使用" else domestic_application
    )
    content_public = str(answers.get("B8_1", "")).strip()
    if content_public not in {"是", "否"}:
        content_public = "unknown"
    filing = "unknown"
    security = "unknown"
    if public_service == "false":
        filing = security = "false"
    elif public_service == "true":
        if content_public == "否":
            filing = security = "false"
        elif content_public == "是":
            filing = security = "unknown" if any(
                str(answers.get(key, "")).strip() in {"不确定", ""} for key in ("B8_2", "B8_3")
            ) else "true"
    return {
        "domestic_deep_synthesis_application": domestic_application,
        "domestic_public_genai_service": public_service,
        "content_public_distribution": content_public,
        "algorithm_filing": filing,
        "security_assessment": security,
    }


# ---------------------------------------------------------------------------
# 答案级交叉校验
# ---------------------------------------------------------------------------


def cross_check_scale(answers: dict) -> list[str]:
    """校验规模摘要和详情的内部完整性，不把不同法定口径强行比较。

    `covered provider` 的系统访问规模与 `large online platform` 的平台独立用户
    规模在法条中是两个不同指标。旧版答案只有档位时，保留值域检查和待核提示；
    只有详情字段明确同一统计对象、地域、周期和去重方法时，才允许作数值比较。
    """
    problems: list[str] = []
    b3a = str(answers.get("B3a", "")).strip()
    if b3a and b3a not in B3A_RANGE:
        if b3a == "不确定":
            return problems
        return [
            f"B3a 档位无法识别：「{b3a}」（允许值：≤100万 / >100万 / 不确定）",
            "提示：B3a 只保存门槛摘要；请补充 B3a_details 的统计对象、地域、周期和去重方法",
        ]
    if str(answers.get("B4_2", "")).strip() in {"是", "不确定"}:
        raw = str(answers.get("B4_2c", "")).strip()
        if raw and raw != "不确定" and raw not in B4_2C_ORDINAL:
            problems.append(
                f"B4_2c 档位无法识别：「{raw}」（允许值：≤100万 / 100万-200万 / >200万 / 不确定）"
            )

    # 新版平台详情要求逐月数据；旧版摘要没有详情时只列待核提示，不伪造历史数据。
    platform_details = answers.get("B4_2c_details")
    if isinstance(platform_details, dict):
        monthly = platform_details.get("monthly_values")
        if monthly is not None:
            if not isinstance(monthly, list) or len(monthly) != 12:
                problems.append("B4_2c_details.monthly_values 未提供完整的此前12个月逐月数据")
            elif any(not isinstance(item, (int, float, dict)) or isinstance(item, bool) for item in monthly):
                problems.append("B4_2c_details.monthly_values 含无法识别的月度数值")
        elif answers.get("B4_2c") not in (None, "", "不确定"):
            problems.append("B4_2c 只有门槛摘要，缺少 B4_2c_details.monthly_values；请核实此前12个月数据")

    return problems


# ---------------------------------------------------------------------------
# B5a 高仿真能力 × A3 输出模态 相容性（2026-09-19 用户裁定新增）
# ---------------------------------------------------------------------------
# 依据 `modeA-questionnaire.md` 「B5a判定备注（中国侧 A3 模态与高仿真能力核对，防止漏勾）」：
# A3 采集产品的**输出模态**，B5a 采集是否具备**深度合成规定第17条第1款所列高仿真能力**，
# 二者相关但不等同。该备注的落点是「防漏勾」（A3 含某模态而 B5a 未勾 → 不得直接采信
# 「以上皆无」），但「风景图／无人脸视频／音乐音效」等**可合法不勾**，机器无从裁断，
# 故漏勾方向**不代码化**、仍由人工按五条映射追问。
# 本函数只代码化**单向的「过度勾选」**：所勾能力依赖的输出模态在 A3 中**完全不存在**
# （如纯文本产品勾「人脸生成/替换/操控」「数字人」「沉浸式拟真场景」）——这是客观不可能，
# 可直接判为答案级矛盾。
# 新增能力选项时须同步本表（选项集见 modeA-questionnaire B5a；业务版皮肤继承母版同一选项集）。
B5A_REQUIRES: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("智能对话", "智能写作"), ("文本",)),
    (("合成人声", "仿声", "语音合成", "语音克隆"), ("音频", "视频")),
    (("人脸生成", "人脸替换", "人脸操控", "换脸"), ("图像", "视频")),
    (("姿态操控",), ("图像", "视频")),
    (("沉浸式拟真场景",), ("虚拟场景", "3D", "视频")),
    (("数字人", "虚拟人"), ("数字人", "虚拟人", "图像", "视频", "虚拟场景")),
)

# B5a 中「不作肯定主张」的选项：未勾选任何能力，不参与过度勾选校验。
B5A_NON_CLAIM = ("以上皆无", "不确定")


def cross_check_capability_modality(answers: dict) -> list[str]:
    """B5a 勾选能力 × A3 输出模态 相容性（单向：防过度勾选）。

    只报「勾了能力、但产品根本不产出该能力所需模态」这一类客观不可能；
    漏勾与「以上皆无」是否可信属人工追问（见 modeA-questionnaire B5a判定备注），不在此报。
    """
    problems: list[str] = []
    ticks = [str(x).strip() for x in (answers.get("B5a") or []) if str(x).strip()]
    modalities = _a3_modalities(answers)
    if not ticks or not modalities:
        return problems
    for caps, mods in B5A_REQUIRES:
        hit = [t for t in ticks if any(c in t for c in caps)]
        if not hit:
            continue
        if any(m in mod for mod in modalities for m in mods):
            continue
        problems.append(
            f"能力与模态矛盾：B5a 勾选了「{'／'.join(hit)}」，"
            f"但 A3 输出模态为「{'、'.join(modalities)}」——"
            f"该能力需可生成「{'／'.join(mods)}」，产品既不产出该模态即不可能具备该能力。"
            "须即时弹窗核对（A3 漏勾模态？或 B5a 误勾？），并按 modeA-questionnaire"
            "「矛盾处理规则」以产品实际功能描述为准回退"
        )
    return problems


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

DEMO = {
    "A1": "部分自研",
    "A2": "B2C",
    "A3": ["文本", "音频"],
    "A4a": {"中国": "1000万+", "欧盟": "100万-1000万", "加州": "10-100万"},
    "A6": ["中国大陆", "欧盟", "加州"],
    "B1_1": ["App"],
    "B3a": "≤100万",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="B 组触发引擎与答案级交叉校验")
    parser.add_argument("survey", nargs="?", help="survey_audit.json（结构化问卷答案）")
    parser.add_argument("--demo", action="store_true", help="用内置样例演示")
    args = parser.parse_args(argv)

    if args.demo:
        answers = DEMO
        print("（演示）B3a与A4(a)统计对象或地域未统一 → 仅提示补充详情，不报硬性规模矛盾")
    elif args.survey:
        try:
            answers = survey_io.load_audit(Path(args.survey))
        except survey_io.AuditFormatError as exc:
            print(f"resolve_triggers: 无法读取答案（未执行）：{exc}", file=sys.stderr)
            return 2
    else:
        parser.error("需要 survey_audit.json 或 --demo")

    try:
        triggered = resolve_triggers(answers)
    except (AnchorViolation, InvariantViolation) as exc:
        print(f"resolve_triggers: 内部不变量被破坏（未执行）：{exc}", file=sys.stderr)
        return 2

    problems = cross_check_scale(answers)
    problems += cross_check_capability_modality(answers)

    keys = survey_io.recognised_keys(answers)
    print(f"已识别答案键：{len(keys)} 个（{', '.join(keys) if keys else '无'}）")
    print("触发状态：")
    for row in TRIGGER_TABLE:
        mark = "触发" if row["id"] in triggered else "不触发"
        print(f"  [{mark}] {row['id']:<8} <- {row['desc']}")
    if problems:
        print("交叉校验：")
        for p in problems:
            print(f"  [!] {p}")
        return 1
    print("交叉校验：通过（无答案级问题）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
